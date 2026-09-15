"""Password security helpers shared by registration and login."""

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


def create_access_token(user_id: int, now: datetime | None = None) -> str:
    """Create a signed JWT identifying one user for a limited time."""
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
