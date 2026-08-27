from fastapi import FastAPI, status
from pydantic import BaseModel

from tinyrpg.models import CLASS_HEALTH, Character, CharacterClass

app = FastAPI()


class CharacterCreate(BaseModel):
    name: str
    character_class: CharacterClass


class CharacterResponse(BaseModel):
    name: str
    character_class: CharacterClass
    health: int
    level: int


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


@app.post("/characters", status_code=status.HTTP_201_CREATED)
def create_character(character_data: CharacterCreate) -> CharacterResponse:
    health = CLASS_HEALTH[character_data.character_class]
    character = Character(character_data.name, character_data.character_class, health)
    response = CharacterResponse(
        name=character.name,
        character_class=character.character_class,
        health=character.health,
        level=character.level,
    )
    return response
