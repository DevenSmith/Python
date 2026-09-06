"""SQLAlchemy models that describe Tiny RPG's database tables."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tinyrpg.database import Base


class CharacterRecord(Base):
    __tablename__ = "characters"
    __table_args__ = (
        CheckConstraint("health >= 0", name="ck_characters_health_nonnegative"),
        CheckConstraint("level >= 1 AND level <= 10", name="ck_characters_level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    character_class: Mapped[str] = mapped_column(String(20))
    health: Mapped[int]
    level: Mapped[int] = mapped_column(default=1)
    inventory_items: Mapped[list[InventoryItemRecord]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
    )


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
