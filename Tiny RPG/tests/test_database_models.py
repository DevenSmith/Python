import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tinyrpg.database import Base
from tinyrpg.database_models import CharacterRecord, InventoryItemRecord


def test_character_record_table_shape() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("characters")}

    assert set(columns) == {"id", "name", "character_class", "health", "level"}
    primary_key = inspector.get_pk_constraint("characters")
    assert primary_key["constrained_columns"] == ["id"]
    assert all(not column["nullable"] for column in columns.values())


def test_character_record_level_default() -> None:
    assert CharacterRecord.__table__.c.level.default.arg == 1


def test_character_has_inventory_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        character = CharacterRecord(name="Ada", character_class="Mage", health=80)
        character.inventory_items.extend(
            [
                InventoryItemRecord(
                    name="Health Potion", quantity=3, healing=25, damage=0
                ),
                InventoryItemRecord(name="Dagger", quantity=1, healing=0, damage=10),
            ]
        )
        session.add(character)
        session.commit()

        assert character.id == 1
        items_by_name = {item.name: item for item in character.inventory_items}
        assert set(items_by_name) == {"Health Potion", "Dagger"}
        assert all(item.character_id == character.id for item in character.inventory_items)
        assert all(item.character is character for item in character.inventory_items)


def test_character_cannot_have_duplicate_item_names() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        character = CharacterRecord(name="Ada", character_class="Mage", health=80)
        character.inventory_items.extend(
            [
                InventoryItemRecord(
                    name="Health Potion", quantity=1, healing=25, damage=0
                ),
                InventoryItemRecord(
                    name="Health Potion", quantity=2, healing=25, damage=0
                ),
            ]
        )
        session.add(character)

        with pytest.raises(IntegrityError):
            session.commit()
