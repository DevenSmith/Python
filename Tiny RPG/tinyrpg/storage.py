import json
from pathlib import Path

from tinyrpg.models import Character, CharacterClass


def save_character_summary(summary: str, file_path: Path) -> None:
    with file_path.open("w", encoding="utf-8") as file:
        file.write(summary)


def load_character_summary(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8") as file:
        text = file.read()
        return text


def save_character_json(character: Character, file_path: Path) -> None:
    character_data: dict[str, str | int] = {
        "name": character.name,
        "character_class": character.character_class.value,
        "health": character.health,
        "level": character.level,
    }

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(character_data, file, indent=4)


def load_character_json(file_path: Path) -> Character:
    with file_path.open("r", encoding="utf-8") as file:
        character_data = json.load(file)

    loaded_character = Character(
        character_data["name"],
        CharacterClass(character_data["character_class"]),
        character_data["health"],
    )
    loaded_character.level = character_data["level"]
    return loaded_character
