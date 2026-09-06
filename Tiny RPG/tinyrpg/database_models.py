"""SQLAlchemy models that describe Tiny RPG's database tables."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

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
