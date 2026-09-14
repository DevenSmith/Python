from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tinyrpg.config import settings
from tinyrpg.database import create_tables, get_database_session
from tinyrpg.database_models import CharacterRecord, InventoryItemRecord, UserRecord
from tinyrpg.models import CLASS_HEALTH, CharacterClass
from tinyrpg.security import hash_password

app = FastAPI(title=settings.app_name)
create_tables()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
    expose_headers=["X-Next-Cursor"],
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


class CharacterUpdate(BaseModel):
    """Fields a client may change without replacing the whole character."""

    name: str | None = Field(default=None, min_length=1, max_length=30)
    health: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def require_a_change(self) -> "CharacterUpdate":
        if self.name is None and self.health is None:
            raise ValueError("Provide at least one field to update")
        return self


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=50)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, display_name: str) -> str:
        stripped_name = display_name.strip()
        if not stripped_name:
            raise ValueError("Display name cannot be blank")
        return stripped_name


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    created_at: datetime


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


class InventoryItemReplace(BaseModel):
    """Complete client-editable representation used by PUT."""

    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)
    healing: int = Field(ge=0)
    damage: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def validate_effect(self) -> "InventoryItemReplace":
        if self.healing == 0 and self.damage == 0:
            raise ValueError("An item must have healing or damage")
        return self


DatabaseSession = Annotated[Session, Depends(get_database_session)]


@app.get("/")
def welcome_to_tiny_rpg() -> dict[str, str]:
    return {"message": "Welcome to TinyRPG"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserCreate,
    session: DatabaseSession,
) -> UserResponse:
    normalized_email = str(user_data.email).lower()
    existing_user = session.scalar(
        select(UserRecord).where(UserRecord.email == normalized_email)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = UserRecord(
        email=normalized_email,
        display_name=user_data.display_name,
        password_hash=hash_password(user_data.password.get_secret_value()),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        # The database remains the final authority if concurrent requests race.
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from error

    session.refresh(user)
    return UserResponse.model_validate(user)


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
    response: Response,
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[CharacterResponse]:
    statement = select(CharacterRecord)
    if after_id is not None:
        statement = statement.where(CharacterRecord.id > after_id)

    # Fetch one extra record so the response can say whether another page exists.
    statement = statement.order_by(CharacterRecord.id).limit(limit + 1)
    characters = list(session.scalars(statement))
    has_more = len(characters) > limit
    page = characters[:limit]

    if has_more:
        response.headers["X-Next-Cursor"] = str(page[-1].id)

    return [
        CharacterResponse.model_validate(character)
        for character in page
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


@app.patch("/characters/{character_id}")
def update_character(
    character_id: int,
    changes: CharacterUpdate,
    session: DatabaseSession,
) -> CharacterResponse:
    character = session.get(CharacterRecord, character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    if changes.name is not None:
        character.name = changes.name
    if changes.health is not None:
        character.health = changes.health

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


@app.put("/characters/{character_id}/inventory/{item_id}")
def replace_inventory_item(
    character_id: int,
    item_id: int,
    replacement: InventoryItemReplace,
    session: DatabaseSession,
) -> InventoryItemResponse:
    if session.get(CharacterRecord, character_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    item_statement = select(InventoryItemRecord).where(
        InventoryItemRecord.id == item_id,
        InventoryItemRecord.character_id == character_id,
    )
    item = session.scalar(item_statement)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )

    duplicate_statement = select(InventoryItemRecord.id).where(
        InventoryItemRecord.character_id == character_id,
        InventoryItemRecord.name == replacement.name,
        InventoryItemRecord.id != item_id,
    )
    if session.scalar(duplicate_statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Character already has an item with this name",
        )

    item.name = replacement.name
    item.quantity = replacement.quantity
    item.healing = replacement.healing
    item.damage = replacement.damage
    session.commit()
    session.refresh(item)
    return InventoryItemResponse.model_validate(item)


@app.delete(
    "/characters/{character_id}/inventory/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_inventory_item(
    character_id: int,
    item_id: int,
    session: DatabaseSession,
) -> Response:
    if session.get(CharacterRecord, character_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    statement = select(InventoryItemRecord).where(
        InventoryItemRecord.id == item_id,
        InventoryItemRecord.character_id == character_id,
    )
    item = session.scalar(statement)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )

    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
