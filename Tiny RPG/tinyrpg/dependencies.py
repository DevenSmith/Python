"""Reusable FastAPI dependencies shared by endpoint routers."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from tinyrpg.database import get_database_session
from tinyrpg.database_models import CharacterRecord, UserRecord, UserSessionRecord
from tinyrpg.security import decode_access_token_identity

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


def require_admin(current_user: CurrentUser) -> UserRecord:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return current_user


AdminUser = Annotated[UserRecord, Depends(require_admin)]


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
