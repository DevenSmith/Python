from datetime import timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from tinyrpg.config import settings
from tinyrpg.database_models import (
    AuthTokenRecord,
    SecurityAuditEventRecord,
    UserRecord,
    UserSessionRecord,
)
from tinyrpg.dependencies import BearerCredentials, CurrentUser, DatabaseSession
from tinyrpg.email_service import send_verification_email
from tinyrpg.schemas.auth import MessageResponse
from tinyrpg.schemas.users import (
    PasswordChange,
    SecurityAuditEventResponse,
    SessionResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from tinyrpg.security import hash_password, verify_password
from tinyrpg.services.authentication import (
    delete_auth_cookies,
    issue_database_token,
    record_security_event,
    revoke_login_session,
    revoke_user_refresh_tokens,
    session_id_from_credentials,
    utc_now,
)

router = APIRouter(tags=["users"])


@router.post("/users", status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    response: Response,
    session: DatabaseSession,
) -> UserResponse:
    normalized_email = str(user_data.email).lower()
    if session.scalar(select(UserRecord).where(UserRecord.email == normalized_email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = UserRecord(
        email=normalized_email,
        display_name=user_data.display_name,
        password_hash=hash_password(user_data.password.get_secret_value()),
    )
    session.add(user)
    session.flush()
    token = issue_database_token(
        session,
        user.id,
        "email_verification",
        utc_now() + timedelta(hours=settings.verification_token_expire_hours),
    )
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from error
    session.refresh(user)
    background_tasks.add_task(send_verification_email, user.email, token)
    if settings.expose_development_tokens:
        response.headers["X-Verification-Token"] = token
    return UserResponse.from_record(user)


@router.get("/users/me")
def get_my_account(current_user: CurrentUser) -> UserResponse:
    return UserResponse.from_record(current_user)


@router.get("/users/me/security-events")
def list_my_security_events(
    session: DatabaseSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SecurityAuditEventResponse]:
    events = session.scalars(
        select(SecurityAuditEventRecord)
        .where(SecurityAuditEventRecord.user_id == current_user.id)
        .order_by(SecurityAuditEventRecord.id.desc())
        .limit(limit)
    )
    return [SecurityAuditEventResponse.model_validate(event) for event in events]


@router.patch("/users/me")
def update_my_account(
    changes: UserUpdate, session: DatabaseSession, current_user: CurrentUser
) -> UserResponse:
    current_user.display_name = changes.display_name
    session.commit()
    session.refresh(current_user)
    return UserResponse.from_record(current_user)


@router.post("/users/me/password")
def change_my_password(
    passwords: PasswordChange,
    request: Request,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> MessageResponse:
    if not verify_password(passwords.current_password.get_secret_value(), current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(passwords.new_password.get_secret_value())
    revoke_user_refresh_tokens(session, current_user.id, utc_now())
    record_security_event(session, current_user.id, "password_changed", request)
    session.commit()
    delete_auth_cookies(response)
    return MessageResponse(message="Password changed; sign in again on this device")


@router.post("/users/me/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all_devices(
    request: Request,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    revoke_user_refresh_tokens(session, current_user.id, utc_now())
    record_security_event(session, current_user.id, "all_sessions_revoked", request)
    session.commit()
    delete_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/users/me/sessions")
def list_my_sessions(
    session: DatabaseSession,
    current_user: CurrentUser,
    credentials: BearerCredentials,
) -> list[SessionResponse]:
    current_session_id = session_id_from_credentials(credentials)
    now = utc_now()
    sessions = session.scalars(
        select(UserSessionRecord).join(AuthTokenRecord).where(
            UserSessionRecord.user_id == current_user.id,
            UserSessionRecord.revoked_at.is_(None),
            AuthTokenRecord.purpose == "refresh",
            AuthTokenRecord.used_at.is_(None),
            AuthTokenRecord.revoked_at.is_(None),
            AuthTokenRecord.expires_at > now,
        ).order_by(UserSessionRecord.last_seen_at.desc())
    )
    return [SessionResponse(
        id=item.id,
        created_at=item.created_at,
        last_seen_at=item.last_seen_at,
        user_agent=item.user_agent,
        ip_address=item.ip_address,
        current=item.id == current_session_id,
    ) for item in sessions]


@router.delete("/users/me/sessions/{login_session_id}", status_code=204)
def revoke_my_session(
    login_session_id: str,
    request: Request,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
    credentials: BearerCredentials,
) -> Response:
    login_session = session.get(UserSessionRecord, login_session_id)
    if login_session is None or login_session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    current_session_id = session_id_from_credentials(credentials)
    revoke_login_session(session, login_session, utc_now())
    record_security_event(session, current_user.id, "session_revoked", request)
    session.commit()
    if login_session.id == current_session_id:
        delete_auth_cookies(response)
    response.status_code = 204
    return response


@router.delete("/users/me", status_code=204)
def disable_my_account(
    request: Request,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    now = utc_now()
    current_user.disabled_at = now
    revoke_user_refresh_tokens(session, current_user.id, now)
    record_security_event(session, current_user.id, "account_disabled", request)
    session.commit()
    delete_auth_cookies(response)
    response.status_code = 204
    return response
