from sqlalchemy import create_engine, inspect

from tinyrpg.database import Base
from tinyrpg.database_models import CharacterRecord


def test_character_record_table_shape() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("characters")}

    assert set(columns) == {"id", "name", "character_class", "health", "level"}
    assert columns["id"]["primary_key"] == 1
    assert all(not column["nullable"] for column in columns.values())


def test_character_record_level_default() -> None:
    assert CharacterRecord.__table__.c.level.default.arg == 1
