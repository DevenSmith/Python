from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tinyrpg.config import settings
from tinyrpg.database import create_tables, get_database_session
from tinyrpg.database_models import CharacterRecord
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
