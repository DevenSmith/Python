"""SQLAlchemy models that describe Tiny RPG's database tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tinyrpg.database import Base


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="player")
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    characters: Mapped[list[CharacterRecord]] = relationship(back_populates="owner")
    auth_tokens: Mapped[list[AuthTokenRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSessionRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSessionRecord(Base):
    """One signed-in browser or device, across refresh-token rotations."""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compromised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[UserRecord] = relationship(back_populates="sessions")
    auth_tokens: Mapped[list[AuthTokenRecord]] = relationship(back_populates="login_session")


class AuthTokenRecord(Base):
    """Hashed, revocable tokens used for refresh and one-time account actions."""

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_sessions.id", ondelete="CASCADE"), index=True, nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[UserRecord] = relationship(back_populates="auth_tokens")
    login_session: Mapped[UserSessionRecord | None] = relationship(back_populates="auth_tokens")


class CharacterRecord(Base):
    __tablename__ = "characters"
    __table_args__ = (
        CheckConstraint("health >= 0", name="ck_characters_health_nonnegative"),
        CheckConstraint("level >= 1 AND level <= 10", name="ck_characters_level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(30))
    character_class: Mapped[str] = mapped_column(String(20))
    health: Mapped[int]
    level: Mapped[int] = mapped_column(default=1)
    inventory_items: Mapped[list[InventoryItemRecord]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
    )
    owner: Mapped[UserRecord] = relationship(back_populates="characters")


class InventoryItemRecord(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("character_id", "name", name="uq_inventory_character_item"),
        CheckConstraint("quantity > 0", name="ck_inventory_quantity_positive"),
        CheckConstraint("healing >= 0", name="ck_inventory_healing_nonnegative"),
        CheckConstraint("damage >= 0", name="ck_inventory_damage_nonnegative"),
        CheckConstraint(
            "healing > 0 OR damage > 0",
            name="ck_inventory_item_has_effect",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int]
    healing: Mapped[int] = mapped_column(default=0)
    damage: Mapped[int] = mapped_column(default=0)
    character: Mapped[CharacterRecord] = relationship(back_populates="inventory_items")
