"""SQLAlchemy database foundation for Tiny RPG."""

from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Parent class for every SQLAlchemy database model."""


# SQLite keeps this first ORM exercise local and requires no database server.
# PostgreSQL can later replace this URL without changing the model classes.
DATABASE_URL = "sqlite:///./tiny_rpg.db"
engine = create_engine(
    DATABASE_URL,
    # FastAPI may use a SQLite connection from a different worker thread.
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_tables() -> None:
    """Create any model tables that do not already exist."""
    # Importing registers CharacterRecord in Base.metadata before create_all runs.
    from tinyrpg import database_models  # noqa: F401

    Base.metadata.create_all(engine)
    # create_all does not add columns to an existing learning database. These
    # small SQLite migrations preserve accounts created by earlier lessons.
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        if "role" not in user_columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'player'")
            )
        if "email_verified_at" not in user_columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN email_verified_at DATETIME")
            )


def get_database_session() -> Iterator[Session]:
    """Give one database session to a request and always close it afterward."""
    with SessionLocal() as session:
        yield session
