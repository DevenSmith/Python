import hmac
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    Cookie,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tinyrpg.config import settings
from tinyrpg.database import get_database_session
from tinyrpg.database_models import (
    AuthTokenRecord,
    CharacterRecord,
    InventoryItemRecord,
    UserRecord,
    UserSessionRecord,
)
from tinyrpg.email_service import send_password_reset_email, send_verification_email
from tinyrpg.models import CLASS_HEALTH, CharacterClass
from tinyrpg.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_opaque_token,
    decode_access_token_identity,
    hash_password,
    hash_token,
    verify_password,
)

app = FastAPI(title=settings.app_name)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=[
        "X-Next-Cursor",
        "X-Verification-Token",
        "X-Password-Reset-Token",
    ],
)


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    character_class: CharacterClass

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()

        if not stripped_name:
            raise ValueError("Name cannot be blank")

        return stripped_name


class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    character_class: CharacterClass
    health: int
    level: int
    id: int
    owner_id: int


class CharacterUpdate(BaseModel):
    """Fields a client may change without replacing the whole character."""

    name: str | None = Field(default=None, min_length=1, max_length=30)
    health: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def require_a_change(self) -> "CharacterUpdate":
        if self.name is None and self.health is None:
            raise ValueError("Provide at least one field to update")
        return self


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=50)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, display_name: str) -> str:
        stripped_name = display_name.strip()
        if not stripped_name:
            raise ValueError("Display name cannot be blank")
        return stripped_name


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    created_at: datetime
    role: str
    email_verified: bool

    @classmethod
    def from_record(cls, user: UserRecord) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
            role=user.role,
            email_verified=user.email_verified_at is not None,
        )


class UserUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, display_name: str) -> str:
        stripped_name = display_name.strip()
        if not stripped_name:
            raise ValueError("Display name cannot be blank")
        return stripped_name


class PasswordChange(BaseModel):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenRequest(BaseModel):
    token: SecretStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: SecretStr
    new_password: SecretStr = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    user_agent: str
    ip_address: str
    current: bool


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)
    healing: int = Field(default=0, ge=0)
    damage: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def validate_effect(self) -> "InventoryItemCreate":
        if self.healing == 0 and self.damage == 0:
            raise ValueError("An item must have healing or damage")
        return self


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    name: str
    quantity: int
    healing: int
    damage: int


class InventoryItemReplace(BaseModel):
    """Complete client-editable representation used by PUT."""

    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)
    healing: int = Field(ge=0)
    damage: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def validate_effect(self) -> "InventoryItemReplace":
        if self.healing == 0 and self.damage == 0:
            raise ValueError("An item must have healing or damage")
        return self


DatabaseSession = Annotated[Session, Depends(get_database_session)]
bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: BearerCredentials,
    session: DatabaseSession,
) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_error()

    try:
        user_id, login_session_id = decode_access_token_identity(credentials.credentials)
    except InvalidTokenError as error:
        raise authentication_error() from error

    user = session.get(UserRecord, user_id)
    if user is None or user.disabled_at is not None:
        raise authentication_error()
    if login_session_id is not None:
        login_session = session.get(UserSessionRecord, login_session_id)
        if (
            login_session is None
            or login_session.user_id != user_id
            or login_session.revoked_at is not None
            or login_session.compromised_at is not None
        ):
            raise authentication_error()
    return user


CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


class LoginRateLimiter:
    """Small in-process limiter for this teaching app.

    A multi-server deployment would use Redis so every process shares attempts.
    """

    def __init__(self) -> None:
        self.attempts: dict[str, deque[datetime]] = defaultdict(deque)
        self.lock = Lock()

    def check(self, key: str, now: datetime) -> None:
        cutoff = now - timedelta(minutes=settings.login_attempt_window_minutes)
        with self.lock:
            attempts = self.attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= settings.login_attempt_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again later.",
                    headers={"Retry-After": str(settings.login_attempt_window_minutes * 60)},
                )

    def failed(self, key: str, now: datetime) -> None:
        with self.lock:
            self.attempts[key].append(now)

    def succeeded(self, key: str) -> None:
        with self.lock:
            self.attempts.pop(key, None)

    def clear_email(self, email: str) -> None:
        """Unlock an account after its owner proves control through a reset token."""
        suffix = f":{email.lower()}"
        with self.lock:
            for key in [key for key in self.attempts if key.endswith(suffix)]:
                del self.attempts[key]

    def clear(self) -> None:
        with self.lock:
            self.attempts.clear()


login_rate_limiter = LoginRateLimiter()


def require_admin(current_user: CurrentUser) -> UserRecord:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return current_user


AdminUser = Annotated[UserRecord, Depends(require_admin)]


def utc_now() -> datetime:
    return datetime.now(UTC)


def comparable_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def issue_database_token(
    session: Session,
    user_id: int,
    purpose: str,
    expires_at: datetime,
    session_id: str | None = None,
) -> str:
    raw_token = create_opaque_token()
    session.add(
        AuthTokenRecord(
            user_id=user_id,
            session_id=session_id,
            token_hash=hash_token(raw_token),
            purpose=purpose,
            expires_at=expires_at,
        )
    )
    return raw_token


def consume_database_token(
    session: Session,
    raw_token: str,
    purpose: str,
    now: datetime,
) -> AuthTokenRecord:
    token = session.scalar(
        select(AuthTokenRecord).where(
            AuthTokenRecord.token_hash == hash_token(raw_token),
            AuthTokenRecord.purpose == purpose,
        )
    )
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
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite="lax",
        path="/auth",
    )
    response.set_cookie(
        key="csrf_token",
        value=create_opaque_token(),
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.use_secure_cookies,
        samesite="lax",
        path="/",
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
    for login_session in session.scalars(
        select(UserSessionRecord).where(
            UserSessionRecord.user_id == user_id,
            UserSessionRecord.revoked_at.is_(None),
        )
    ):
        login_session.revoked_at = now
    for token in session.scalars(
        select(AuthTokenRecord).where(
            AuthTokenRecord.user_id == user_id,
            AuthTokenRecord.purpose == "refresh",
            AuthTokenRecord.used_at.is_(None),
            AuthTokenRecord.revoked_at.is_(None),
        )
    ):
        token.revoked_at = now


def revoke_login_session(
    session: Session, login_session: UserSessionRecord, now: datetime
) -> None:
    if login_session.revoked_at is None:
        login_session.revoked_at = now
    for token in session.scalars(
        select(AuthTokenRecord).where(
            AuthTokenRecord.session_id == login_session.id,
            AuthTokenRecord.purpose == "refresh",
            AuthTokenRecord.revoked_at.is_(None),
        )
    ):
        token.revoked_at = now


def session_id_from_credentials(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials is None:
        return None
    try:
        _, login_session_id = decode_access_token_identity(credentials.credentials)
    except InvalidTokenError:
        return None
    return login_session_id


def get_owned_character(
    character_id: int,
    current_user: UserRecord,
    session: Session,
) -> CharacterRecord:
    character = session.get(CharacterRecord, character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    if character.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this character",
        )
    return character


@app.get("/")
def welcome_to_tiny_rpg() -> dict[str, str]:
    return {"message": "Welcome to TinyRPG"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    response: Response,
    session: DatabaseSession,
) -> UserResponse:
    normalized_email = str(user_data.email).lower()
    existing_user = session.scalar(
        select(UserRecord).where(UserRecord.email == normalized_email)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = UserRecord(
        email=normalized_email,
        display_name=user_data.display_name,
        password_hash=hash_password(user_data.password.get_secret_value()),
    )
    session.add(user)
    session.flush()
    verification_token = issue_database_token(
        session,
        user.id,
        "email_verification",
        utc_now() + timedelta(hours=settings.verification_token_expire_hours),
    )
    try:
        session.commit()
    except IntegrityError as error:
        # The database remains the final authority if concurrent requests race.
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from error

    session.refresh(user)
    background_tasks.add_task(send_verification_email, user.email, verification_token)
    if settings.expose_development_tokens:
        response.headers["X-Verification-Token"] = verification_token
    return UserResponse.from_record(user)


@app.post("/auth/token")
def login_for_access_token(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    session: DatabaseSession,
) -> TokenResponse:
    normalized_email = str(credentials.email).lower()
    client_address = request.client.host if request.client is not None else "unknown"
    rate_limit_key = f"{client_address}:{normalized_email}"
    now = utc_now()
    login_rate_limiter.check(rate_limit_key, now)
    user = session.scalar(
        select(UserRecord).where(UserRecord.email == normalized_email)
    )
    submitted_password = credentials.password.get_secret_value()

    if user is None:
        verify_password(submitted_password, DUMMY_PASSWORD_HASH)
        login_rate_limiter.failed(rate_limit_key, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        not verify_password(submitted_password, user.password_hash)
        or user.disabled_at is not None
    ):
        login_rate_limiter.failed(rate_limit_key, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_rate_limiter.succeeded(rate_limit_key)
    login_session = UserSessionRecord(
        id=create_opaque_token(),
        user_id=user.id,
        last_seen_at=now,
        user_agent=request.headers.get("user-agent", "Unknown device")[:255],
        ip_address=client_address[:64],
    )
    session.add(login_session)
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


@app.get("/users/me")
def get_my_account(current_user: CurrentUser) -> UserResponse:
    return UserResponse.from_record(current_user)


@app.patch("/users/me")
def update_my_account(
    changes: UserUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> UserResponse:
    current_user.display_name = changes.display_name
    session.commit()
    session.refresh(current_user)
    return UserResponse.from_record(current_user)


@app.post("/users/me/password")
def change_my_password(
    passwords: PasswordChange,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> MessageResponse:
    if not verify_password(
        passwords.current_password.get_secret_value(), current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = hash_password(passwords.new_password.get_secret_value())
    revoke_user_refresh_tokens(session, current_user.id, utc_now())
    session.commit()
    delete_auth_cookies(response)
    return MessageResponse(message="Password changed; sign in again on this device")


@app.post("/users/me/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all_devices(
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    revoke_user_refresh_tokens(session, current_user.id, utc_now())
    session.commit()
    delete_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.get("/users/me/sessions")
def list_my_sessions(
    session: DatabaseSession,
    current_user: CurrentUser,
    credentials: BearerCredentials,
) -> list[SessionResponse]:
    current_session_id = session_id_from_credentials(credentials)
    now = utc_now()
    sessions = session.scalars(
        select(UserSessionRecord)
        .join(AuthTokenRecord)
        .where(
            UserSessionRecord.user_id == current_user.id,
            UserSessionRecord.revoked_at.is_(None),
            AuthTokenRecord.purpose == "refresh",
            AuthTokenRecord.used_at.is_(None),
            AuthTokenRecord.revoked_at.is_(None),
            AuthTokenRecord.expires_at > now,
        )
        .order_by(UserSessionRecord.last_seen_at.desc())
    )
    return [
        SessionResponse(
            id=login_session.id,
            created_at=login_session.created_at,
            last_seen_at=login_session.last_seen_at,
            user_agent=login_session.user_agent,
            ip_address=login_session.ip_address,
            current=login_session.id == current_session_id,
        )
        for login_session in sessions
    ]


@app.delete("/users/me/sessions/{login_session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_my_session(
    login_session_id: str,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
    credentials: BearerCredentials,
) -> Response:
    login_session = session.get(UserSessionRecord, login_session_id)
    if login_session is None or login_session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    current_session_id = session_id_from_credentials(credentials)
    revoke_login_session(session, login_session, utc_now())
    session.commit()
    if login_session.id == current_session_id:
        delete_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def disable_my_account(
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    now = utc_now()
    current_user.disabled_at = now
    revoke_user_refresh_tokens(session, current_user.id, now)
    session.commit()
    delete_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.post("/auth/refresh")
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
    old_token = session.scalar(
        select(AuthTokenRecord).where(
            AuthTokenRecord.token_hash == hash_token(refresh_token),
            AuthTokenRecord.purpose == "refresh",
        )
    )
    if old_token is None:
        raise authentication_error()
    login_session = (
        session.get(UserSessionRecord, old_token.session_id)
        if old_token.session_id is not None
        else None
    )
    if old_token.used_at is not None:
        if (
            login_session is not None
            and login_session.revoked_at is None
            and login_session.compromised_at is None
        ):
            login_session.compromised_at = now
            revoke_login_session(session, login_session, now)
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
    rotated_token = issue_database_token(
        session,
        user.id,
        "refresh",
        now + timedelta(days=settings.refresh_token_expire_days),
        session_id=login_session.id,
    )
    login_session.last_seen_at = now
    login_session.user_agent = request.headers.get("user-agent", login_session.user_agent)[:255]
    if request.client is not None:
        login_session.ip_address = request.client.host[:64]
    session.commit()
    set_auth_cookies(response, rotated_token)
    return TokenResponse(
        access_token=create_access_token(user.id, now=now, session_id=login_session.id)
    )


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_token: Annotated[str | None, Cookie()] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Response:
    if refresh_token is not None:
        validate_csrf_token(csrf_token, csrf_header)
        token = session.scalar(
            select(AuthTokenRecord).where(
                AuthTokenRecord.token_hash == hash_token(refresh_token),
                AuthTokenRecord.purpose == "refresh",
            )
        )
        if token is not None and token.revoked_at is None:
            login_session = (
                session.get(UserSessionRecord, token.session_id)
                if token.session_id is not None
                else None
            )
            if login_session is not None:
                revoke_login_session(session, login_session, utc_now())
            else:
                token.revoked_at = utc_now()
            session.commit()
    delete_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.post("/auth/verify-email")
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


@app.post("/auth/verify-email/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: DatabaseSession,
) -> MessageResponse:
    user = session.scalar(
        select(UserRecord).where(UserRecord.email == str(request_data.email).lower())
    )
    if (
        user is not None
        and user.disabled_at is None
        and user.email_verified_at is None
    ):
        now = utc_now()
        for old_token in session.scalars(
            select(AuthTokenRecord).where(
                AuthTokenRecord.user_id == user.id,
                AuthTokenRecord.purpose == "email_verification",
                AuthTokenRecord.used_at.is_(None),
                AuthTokenRecord.revoked_at.is_(None),
            )
        ):
            old_token.revoked_at = now
        raw_token = issue_database_token(
            session,
            user.id,
            "email_verification",
            now + timedelta(hours=settings.verification_token_expire_hours),
        )
        session.commit()
        background_tasks.add_task(send_verification_email, user.email, raw_token)
        if settings.expose_development_tokens:
            response.headers["X-Verification-Token"] = raw_token
    return MessageResponse(
        message="If that unverified account exists, verification instructions were created"
    )


@app.post("/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: DatabaseSession,
) -> MessageResponse:
    user = session.scalar(
        select(UserRecord).where(UserRecord.email == str(request_data.email).lower())
    )
    if user is not None and user.disabled_at is None:
        raw_token = issue_database_token(
            session,
            user.id,
            "password_reset",
            utc_now() + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
        session.commit()
        background_tasks.add_task(send_password_reset_email, user.email, raw_token)
        if settings.expose_development_tokens:
            response.headers["X-Password-Reset-Token"] = raw_token
    return MessageResponse(
        message="If that account exists, password reset instructions were created"
    )


@app.post("/auth/password-reset/confirm")
def confirm_password_reset(
    reset_data: PasswordResetConfirm,
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
    session.commit()
    login_rate_limiter.clear_email(user.email)
    return MessageResponse(message="Password updated")


@app.get("/admin/users")
def list_users_for_admin(
    session: DatabaseSession,
    _admin: AdminUser,
) -> list[UserResponse]:
    return [UserResponse.from_record(user) for user in session.scalars(select(UserRecord).order_by(UserRecord.id))]


@app.get("/classes")
def get_classes(minimum_health: int | None = None) -> dict[str, int]:
    return {
        character_class.value: health
        for character_class, health in CLASS_HEALTH.items()
        if minimum_health is None or health >= minimum_health
    }


@app.get("/classes/{character_class}")
def get_specific_class(character_class: CharacterClass) -> dict[str, int]:
    return {character_class.value: CLASS_HEALTH[character_class]}


@app.get("/characters")
def list_characters(
    session: DatabaseSession,
    current_user: CurrentUser,
    response: Response,
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[CharacterResponse]:
    statement = select(CharacterRecord).where(
        CharacterRecord.owner_id == current_user.id
    )
    if after_id is not None:
        statement = statement.where(CharacterRecord.id > after_id)

    # Fetch one extra record so the response can say whether another page exists.
    statement = statement.order_by(CharacterRecord.id).limit(limit + 1)
    characters = list(session.scalars(statement))
    has_more = len(characters) > limit
    page = characters[:limit]

    if has_more:
        response.headers["X-Next-Cursor"] = str(page[-1].id)

    return [
        CharacterResponse.model_validate(character)
        for character in page
    ]


@app.get("/characters/count")
def get_character_count(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> dict[str, int]:
    count = session.scalar(
        select(func.count())
        .select_from(CharacterRecord)
        .where(CharacterRecord.owner_id == current_user.id)
    )
    return {"count": count or 0}


@app.get("/characters/{character_id}")
def get_character_by_id(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)
    return CharacterResponse.model_validate(character)


@app.post("/characters", status_code=status.HTTP_201_CREATED)
def create_character(
    character_data: CharacterCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    health = CLASS_HEALTH[character_data.character_class]
    character = CharacterRecord(
        owner_id=current_user.id,
        name=character_data.name,
        character_class=character_data.character_class.value,
        health=health,
        level=1,
    )
    session.add(character)
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@app.patch("/characters/{character_id}")
def update_character(
    character_id: int,
    changes: CharacterUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)

    if changes.name is not None:
        character.name = changes.name
    if changes.health is not None:
        character.health = changes.health

    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@app.post("/characters/{character_id}/level-up")
def level_up_character(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)

    character.level += 1
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@app.get("/characters/{character_id}/inventory")
def list_inventory_items(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> list[InventoryItemResponse]:
    get_owned_character(character_id, current_user, session)

    statement = (
        select(InventoryItemRecord)
        .where(InventoryItemRecord.character_id == character_id)
        .order_by(InventoryItemRecord.id)
    )
    return [
        InventoryItemResponse.model_validate(item)
        for item in session.scalars(statement)
    ]


@app.post("/characters/{character_id}/inventory")
def add_inventory_item(
    character_id: int,
    item_data: InventoryItemCreate,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> InventoryItemResponse:
    get_owned_character(character_id, current_user, session)

    statement = select(InventoryItemRecord).where(
        InventoryItemRecord.character_id == character_id,
        InventoryItemRecord.name == item_data.name,
    )
    item = session.scalar(statement)

    if item is None:
        item = InventoryItemRecord(
            character_id=character_id,
            name=item_data.name,
            quantity=item_data.quantity,
            healing=item_data.healing,
            damage=item_data.damage,
        )
        session.add(item)
        response.status_code = status.HTTP_201_CREATED
    else:
        if item.healing != item_data.healing or item.damage != item_data.damage:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An item with this name already has different effects",
            )
        item.quantity += item_data.quantity

    session.commit()
    session.refresh(item)
    return InventoryItemResponse.model_validate(item)


@app.put("/characters/{character_id}/inventory/{item_id}")
def replace_inventory_item(
    character_id: int,
    item_id: int,
    replacement: InventoryItemReplace,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> InventoryItemResponse:
    get_owned_character(character_id, current_user, session)

    item_statement = select(InventoryItemRecord).where(
        InventoryItemRecord.id == item_id,
        InventoryItemRecord.character_id == character_id,
    )
    item = session.scalar(item_statement)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )

    duplicate_statement = select(InventoryItemRecord.id).where(
        InventoryItemRecord.character_id == character_id,
        InventoryItemRecord.name == replacement.name,
        InventoryItemRecord.id != item_id,
    )
    if session.scalar(duplicate_statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Character already has an item with this name",
        )

    item.name = replacement.name
    item.quantity = replacement.quantity
    item.healing = replacement.healing
    item.damage = replacement.damage
    session.commit()
    session.refresh(item)
    return InventoryItemResponse.model_validate(item)


@app.delete(
    "/characters/{character_id}/inventory/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_inventory_item(
    character_id: int,
    item_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    get_owned_character(character_id, current_user, session)

    statement = select(InventoryItemRecord).where(
        InventoryItemRecord.id == item_id,
        InventoryItemRecord.character_id == character_id,
    )
    item = session.scalar(statement)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )

    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/characters/{character_id}")
def delete_character_by_id(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> dict[str, str]:
    character = get_owned_character(character_id, current_user, session)

    session.delete(character)
    session.commit()
    return {"message": "Character deleted"}
