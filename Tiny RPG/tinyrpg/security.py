"""Password security helpers shared by registration and login."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from tinyrpg.config import settings

password_hash = PasswordHash.recommended()
# Verifying this when an email is unknown makes login timing more similar to a
# wrong-password attempt and reveals less information about registered emails.
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password-used-only-for-timing")


def hash_password(password: str) -> str:
    """Create a salted, one-way password hash using recommended settings."""
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a submitted password against its stored hash."""
    return password_hash.verify(password, stored_hash)


def create_opaque_token() -> str:
    """Create a high-entropy secret suitable for a one-time or refresh token."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Store only a deterministic digest so a database leak reveals no tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: int,
    now: datetime | None = None,
    session_id: str | None = None,
) -> str:
    """Create a signed JWT identifying one user for a limited time."""
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": expires_at,
    }
    if session_id is not None:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> int:
    """Verify a JWT and return its positive integer user ID.

    PyJWT raises InvalidTokenError for invalid signatures, expired tokens, or
    missing and malformed required claims. The API converts that to HTTP 401.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        options={"require": ["sub", "iat", "exp"]},
    )
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject.isdecimal():
        raise jwt.InvalidTokenError("Token subject must be a user ID")
    user_id = int(subject)
    if user_id <= 0:
        raise jwt.InvalidTokenError("Token subject must be a positive user ID")
    return user_id


def decode_access_token_identity(token: str) -> tuple[int, str | None]:
    """Verify a JWT and return its user ID and optional login-session ID."""
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        options={"require": ["sub", "iat", "exp"]},
    )
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject.isdecimal() or int(subject) <= 0:
        raise jwt.InvalidTokenError("Token subject must be a positive user ID")
    session_id = payload.get("sid")
    if session_id is not None and (not isinstance(session_id, str) or not session_id):
        raise jwt.InvalidTokenError("Token session ID must be a non-empty string")
    return int(subject), session_id
