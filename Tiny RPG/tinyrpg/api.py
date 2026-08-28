from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from tinyrpg.config import settings
from tinyrpg.models import CLASS_HEALTH, Character, CharacterClass

app = FastAPI(title=settings.app_name)


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
    name: str
    character_class: CharacterClass
    health: int
    level: int
    id: int


characters: dict[int, Character] = {}


def get_character_store() -> dict[int, Character]:
    return characters


CharacterStore = Annotated[
    dict[int, Character],
    Depends(get_character_store),
]


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


@app.get("/characters/{character_id}")
def get_character_by_id(
    character_id: int, character_store: CharacterStore
) -> CharacterResponse:
    character = character_store.get(character_id)
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    response = CharacterResponse(
        name=character.name,
        character_class=character.character_class,
        health=character.health,
        level=character.level,
        id=character_id,
    )
    return response


@app.post("/characters", status_code=status.HTTP_201_CREATED)
def create_character(
    character_data: CharacterCreate, character_store: CharacterStore
) -> CharacterResponse:
    health = CLASS_HEALTH[character_data.character_class]
    character = Character(character_data.name, character_data.character_class, health)
    character_id = len(character_store) + 1
    response = CharacterResponse(
        name=character.name,
        character_class=character.character_class,
        health=character.health,
        level=character.level,
        id=character_id,
    )
    character_store[character_id] = character
    return response
