"""SQLAlchemy database foundation for Tiny RPG."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Parent class for every SQLAlchemy database model."""


# SQLite keeps this first ORM exercise local and requires no database server.
# PostgreSQL can later replace this URL without changing the model classes.
DATABASE_URL = "sqlite:///./tiny_rpg.db"
engine = create_engine(DATABASE_URL)


def create_tables() -> None:
    """Create any model tables that do not already exist."""
    # Importing registers CharacterRecord in Base.metadata before create_all runs.
    from tinyrpg import database_models  # noqa: F401

    Base.metadata.create_all(engine)
