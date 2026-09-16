"""SQLAlchemy database foundation for Tiny RPG."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tinyrpg.config import settings


class Base(DeclarativeBase):
    """Parent class for every SQLAlchemy database model."""


# SQLite keeps this first ORM exercise local and requires no database server.
# PostgreSQL can later replace this URL without changing the model classes.
DATABASE_URL = settings.database_url
engine = create_engine(
    DATABASE_URL,
    # FastAPI may use a SQLite connection from a different worker thread.
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_database_session() -> Iterator[Session]:
    """Give one database session to a request and always close it afterward."""
    with SessionLocal() as session:
        yield session
