import hmac
from datetime import UTC, datetime

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from tinyrpg.config import settings
from tinyrpg.database_models import (
    AuthTokenRecord,
    SecurityAuditEventRecord,
    UserSessionRecord,
)
from tinyrpg.dependencies import authentication_error
from tinyrpg.security import (
    create_opaque_token,
    decode_access_token_identity,
    hash_token,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def comparable_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def record_security_event(
    session: Session, user_id: int, event_type: str, request: Request
) -> None:
    client_address = request.client.host if request.client is not None else "unknown"
    session.add(SecurityAuditEventRecord(
        user_id=user_id,
        event_type=event_type,
        ip_address=client_address[:64],
        user_agent=request.headers.get("user-agent", "Unknown device")[:255],
    ))


def issue_database_token(
    session: Session,
    user_id: int,
    purpose: str,
    expires_at: datetime,
    session_id: str | None = None,
) -> str:
    raw_token = create_opaque_token()
    session.add(AuthTokenRecord(
        user_id=user_id,
        session_id=session_id,
        token_hash=hash_token(raw_token),
        purpose=purpose,
        expires_at=expires_at,
    ))
    return raw_token


def consume_database_token(
    session: Session, raw_token: str, purpose: str, now: datetime
) -> AuthTokenRecord:
    token = session.scalar(select(AuthTokenRecord).where(
        AuthTokenRecord.token_hash == hash_token(raw_token),
        AuthTokenRecord.purpose == purpose,
    ))
    if (
        token is None
        or token.used_at is not None
        or token.revoked_at is not None
        or comparable_utc(token.expires_at) <= now
    ):
        raise authentication_error()
    token.used_at = now
    return token


def set_auth_cookies(response: Response, refresh_token: str) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token", value=refresh_token, max_age=max_age,
        httponly=True, secure=settings.use_secure_cookies, samesite="lax", path="/auth",
    )
    response.set_cookie(
        key="csrf_token", value=create_opaque_token(), max_age=max_age,
        httponly=False, secure=settings.use_secure_cookies, samesite="lax", path="/",
    )


def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/auth")
    response.delete_cookie("csrf_token", path="/")


def validate_csrf_token(cookie_token: str | None, header_token: str | None) -> None:
    if (
        cookie_token is None
        or header_token is None
        or not hmac.compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is missing or invalid",
        )


def revoke_user_refresh_tokens(session: Session, user_id: int, now: datetime) -> None:
    for login_session in session.scalars(select(UserSessionRecord).where(
        UserSessionRecord.user_id == user_id,
        UserSessionRecord.revoked_at.is_(None),
    )):
        login_session.revoked_at = now
    for token in session.scalars(select(AuthTokenRecord).where(
        AuthTokenRecord.user_id == user_id,
        AuthTokenRecord.purpose == "refresh",
        AuthTokenRecord.used_at.is_(None),
        AuthTokenRecord.revoked_at.is_(None),
    )):
        token.revoked_at = now


def revoke_login_session(
    session: Session, login_session: UserSessionRecord, now: datetime
) -> None:
    if login_session.revoked_at is None:
        login_session.revoked_at = now
    for token in session.scalars(select(AuthTokenRecord).where(
        AuthTokenRecord.session_id == login_session.id,
        AuthTokenRecord.purpose == "refresh",
        AuthTokenRecord.revoked_at.is_(None),
    )):
        token.revoked_at = now


def session_id_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is None:
        return None
    try:
        _, session_id = decode_access_token_identity(credentials.credentials)
    except InvalidTokenError:
        return None
    return session_id
