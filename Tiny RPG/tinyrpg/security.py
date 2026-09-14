"""Password security helpers shared by registration and login."""

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Create a salted, one-way password hash using recommended settings."""
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a submitted password against its stored hash."""
    return password_hash.verify(password, stored_hash)
