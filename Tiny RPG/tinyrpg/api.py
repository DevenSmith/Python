from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tinyrpg.config import settings
from tinyrpg.database import create_tables, get_database_session
from tinyrpg.database_models import CharacterRecord, InventoryItemRecord
from tinyrpg.models import CLASS_HEALTH, CharacterClass

app = FastAPI(title=settings.app_name)
create_tables()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    character_class: CharacterClass

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()

        if not stripped_name:
            raise ValueError("Name cannot be blank")

        return stripped_name


class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    character_class: CharacterClass
    health: int
    level: int
    id: int


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)
    healing: int = Field(default=0, ge=0)
    damage: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def validate_effect(self) -> "InventoryItemCreate":
        if self.healing == 0 and self.damage == 0:
            raise ValueError("An item must have healing or damage")
        return self


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    name: str
    quantity: int
    healing: int
    damage: int


DatabaseSession = Annotated[Session, Depends(get_database_session)]


@app.get("/")
def welcome_to_tiny_rpg() -> dict[str, str]:
    return {"message": "Welcome to TinyRPG"}


@app.get("/classes")
def get_classes(minimum_health: int | None = None) -> dict[str, int]:
    return {
        character_class.value: health
        for character_class, health in CLASS_HEALTH.items()
        if minimum_health is None or health >= minimum_health
    }


@app.get("/classes/{character_class}")
def get_specific_class(character_class: CharacterClass) -> dict[str, int]:
    return {character_class.value: CLASS_HEALTH[character_class]}


@app.get("/characters")
def list_characters(
    session: DatabaseSession,
) -> list[CharacterResponse]:
    statement = select(CharacterRecord).order_by(CharacterRecord.id)
    return [
        CharacterResponse.model_validate(character)
        for character in session.scalars(statement)
    ]


@app.get("/characters/count")
def get_character_count(session: DatabaseSession) -> dict[str, int]:
    count = session.scalar(select(func.count()).select_from(CharacterRecord))
    return {"count": count or 0}


@app.get("/characters/{character_id}")
def get_character_by_id(
    character_id: int,
    session: DatabaseSession,
) -> CharacterResponse:
    character = session.get(CharacterRecord, character_id)

    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    return CharacterResponse.model_validate(character)


@app.post("/characters", status_code=status.HTTP_201_CREATED)
def create_character(
    character_data: CharacterCreate,
    session: DatabaseSession,
) -> CharacterResponse:
    health = CLASS_HEALTH[character_data.character_class]
    character = CharacterRecord(
        name=character_data.name,
        character_class=character_data.character_class.value,
        health=health,
        level=1,
    )
    session.add(character)
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@app.post("/characters/{character_id}/level-up")
def level_up_character(
    character_id: int,
    session: DatabaseSession,
) -> CharacterResponse:
    character = session.get(CharacterRecord, character_id)

    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    character.level += 1
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@app.get("/characters/{character_id}/inventory")
def list_inventory_items(
    character_id: int,
    session: DatabaseSession,
) -> list[InventoryItemResponse]:
    if session.get(CharacterRecord, character_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    statement = (
        select(InventoryItemRecord)
        .where(InventoryItemRecord.character_id == character_id)
        .order_by(InventoryItemRecord.id)
    )
    return [
        InventoryItemResponse.model_validate(item)
        for item in session.scalars(statement)
    ]


@app.post("/characters/{character_id}/inventory")
def add_inventory_item(
    character_id: int,
    item_data: InventoryItemCreate,
    response: Response,
    session: DatabaseSession,
) -> InventoryItemResponse:
    if session.get(CharacterRecord, character_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    statement = select(InventoryItemRecord).where(
        InventoryItemRecord.character_id == character_id,
        InventoryItemRecord.name == item_data.name,
    )
    item = session.scalar(statement)

    if item is None:
        item = InventoryItemRecord(
            character_id=character_id,
            name=item_data.name,
            quantity=item_data.quantity,
            healing=item_data.healing,
            damage=item_data.damage,
        )
        session.add(item)
        response.status_code = status.HTTP_201_CREATED
    else:
        if item.healing != item_data.healing or item.damage != item_data.damage:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An item with this name already has different effects",
            )
        item.quantity += item_data.quantity

    session.commit()
    session.refresh(item)
    return InventoryItemResponse.model_validate(item)


@app.delete("/characters/{character_id}")
def delete_character_by_id(
    character_id: int,
    session: DatabaseSession,
) -> dict[str, str]:
    character = session.get(CharacterRecord, character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    session.delete(character)
    session.commit()
    return {"message": "Character deleted"}
