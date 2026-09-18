from datetime import timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select

from tinyrpg.config import settings
from tinyrpg.database_models import AuthTokenRecord, UserRecord, UserSessionRecord
from tinyrpg.dependencies import DatabaseSession, authentication_error
from tinyrpg.email_service import send_password_reset_email, send_verification_email
from tinyrpg.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenRequest,
    TokenResponse,
)
from tinyrpg.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from tinyrpg.services.authentication import (
    comparable_utc,
    consume_database_token,
    delete_auth_cookies,
    issue_database_token,
    record_security_event,
    revoke_login_session,
    revoke_user_refresh_tokens,
    set_auth_cookies,
    utc_now,
    validate_csrf_token,
)
from tinyrpg.services.rate_limiting import login_rate_limiter

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token")
def login_for_access_token(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    session: DatabaseSession,
) -> TokenResponse:
    email = str(credentials.email).lower()
    address = request.client.host if request.client is not None else "unknown"
    rate_key = f"{address}:{email}"
    now = utc_now()
    login_rate_limiter.check(rate_key, now)
    user = session.scalar(select(UserRecord).where(UserRecord.email == email))
    password = credentials.password.get_secret_value()
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        login_rate_limiter.failed(rate_key, now)
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.password_hash) or user.disabled_at is not None:
        login_rate_limiter.failed(rate_key, now)
        record_security_event(session, user.id, "login_failed", request)
        session.commit()
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_rate_limiter.succeeded(rate_key)
    login_session = UserSessionRecord(
        id=create_opaque_token(),
        user_id=user.id,
        last_seen_at=now,
        user_agent=request.headers.get("user-agent", "Unknown device")[:255],
        ip_address=address[:64],
    )
    session.add(login_session)
    record_security_event(session, user.id, "login_succeeded", request)
    refresh_token = issue_database_token(
        session,
        user.id,
        "refresh",
        now + timedelta(days=settings.refresh_token_expire_days),
        session_id=login_session.id,
    )
    session.commit()
    set_auth_cookies(response, refresh_token)
    return TokenResponse(
        access_token=create_access_token(user.id, now=now, session_id=login_session.id)
    )


@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_token: Annotated[str | None, Cookie()] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> TokenResponse:
    if refresh_token is None:
        raise authentication_error()
    validate_csrf_token(csrf_token, csrf_header)
    now = utc_now()
    old_token = session.scalar(select(AuthTokenRecord).where(
        AuthTokenRecord.token_hash == hash_token(refresh_token),
        AuthTokenRecord.purpose == "refresh",
    ))
    if old_token is None:
        raise authentication_error()
    login_session = session.get(UserSessionRecord, old_token.session_id) if old_token.session_id else None
    if old_token.used_at is not None:
        if login_session and login_session.revoked_at is None and login_session.compromised_at is None:
            login_session.compromised_at = now
            revoke_login_session(session, login_session, now)
            record_security_event(session, old_token.user_id, "refresh_token_reused", request)
            session.commit()
        raise authentication_error()
    if old_token.revoked_at is not None:
        raise authentication_error()
    if (
        comparable_utc(old_token.expires_at) <= now
        or login_session is None
        or login_session.revoked_at is not None
        or login_session.compromised_at is not None
    ):
        raise authentication_error()
    old_token.used_at = now
    user = session.get(UserRecord, old_token.user_id)
    if user is None or user.disabled_at is not None:
        raise authentication_error()
    rotated = issue_database_token(
        session, user.id, "refresh",
        now + timedelta(days=settings.refresh_token_expire_days),
        session_id=login_session.id,
    )
    login_session.last_seen_at = now
    login_session.user_agent = request.headers.get("user-agent", login_session.user_agent)[:255]
    if request.client is not None:
        login_session.ip_address = request.client.host[:64]
    session.commit()
    set_auth_cookies(response, rotated)
    return TokenResponse(
        access_token=create_access_token(user.id, now=now, session_id=login_session.id)
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_token: Annotated[str | None, Cookie()] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Response:
    if refresh_token is not None:
        validate_csrf_token(csrf_token, csrf_header)
        token = session.scalar(select(AuthTokenRecord).where(
            AuthTokenRecord.token_hash == hash_token(refresh_token),
            AuthTokenRecord.purpose == "refresh",
        ))
        if token is not None and token.revoked_at is None:
            login_session = session.get(UserSessionRecord, token.session_id) if token.session_id else None
            if login_session:
                revoke_login_session(session, login_session, utc_now())
            else:
                token.revoked_at = utc_now()
            record_security_event(session, token.user_id, "logout", request)
            session.commit()
    delete_auth_cookies(response)
    response.status_code = 204
    return response


@router.post("/verify-email")
def verify_email(token_data: TokenRequest, session: DatabaseSession) -> MessageResponse:
    token = consume_database_token(
        session, token_data.token.get_secret_value(), "email_verification", utc_now()
    )
    user = session.get(UserRecord, token.user_id)
    if user is None:
        raise authentication_error()
    user.email_verified_at = utc_now()
    session.commit()
    return MessageResponse(message="Email verified")


@router.post("/verify-email/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: DatabaseSession,
) -> MessageResponse:
    user = session.scalar(select(UserRecord).where(
        UserRecord.email == str(request_data.email).lower()
    ))
    if user is not None and user.disabled_at is None and user.email_verified_at is None:
        now = utc_now()
        for token in session.scalars(select(AuthTokenRecord).where(
            AuthTokenRecord.user_id == user.id,
            AuthTokenRecord.purpose == "email_verification",
            AuthTokenRecord.used_at.is_(None),
            AuthTokenRecord.revoked_at.is_(None),
        )):
            token.revoked_at = now
        raw_token = issue_database_token(
            session, user.id, "email_verification",
            now + timedelta(hours=settings.verification_token_expire_hours),
        )
        session.commit()
        background_tasks.add_task(send_verification_email, user.email, raw_token)
        if settings.expose_development_tokens:
            response.headers["X-Verification-Token"] = raw_token
    return MessageResponse(message="If that unverified account exists, verification instructions were created")


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: DatabaseSession,
) -> MessageResponse:
    user = session.scalar(select(UserRecord).where(
        UserRecord.email == str(request_data.email).lower()
    ))
    if user is not None and user.disabled_at is None:
        raw_token = issue_database_token(
            session, user.id, "password_reset",
            utc_now() + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
        session.commit()
        background_tasks.add_task(send_password_reset_email, user.email, raw_token)
        if settings.expose_development_tokens:
            response.headers["X-Password-Reset-Token"] = raw_token
    return MessageResponse(message="If that account exists, password reset instructions were created")


@router.post("/password-reset/confirm")
def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    request: Request,
    session: DatabaseSession,
) -> MessageResponse:
    now = utc_now()
    token = consume_database_token(
        session, reset_data.token.get_secret_value(), "password_reset", now
    )
    user = session.get(UserRecord, token.user_id)
    if user is None or user.disabled_at is not None:
        raise authentication_error()
    user.password_hash = hash_password(reset_data.new_password.get_secret_value())
    revoke_user_refresh_tokens(session, user.id, now)
    record_security_event(session, user.id, "password_reset", request)
    session.commit()
    login_rate_limiter.clear_email(user.email)
    return MessageResponse(message="Password updated")
