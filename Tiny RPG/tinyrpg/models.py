from dataclasses import dataclass
from enum import StrEnum


class CharacterClass(StrEnum):
    WARRIOR = "Warrior"
    MAGE = "Mage"
    ROGUE = "Rogue"


class Character:
    MAX_LEVEL: int = 10
    name: str
    character_class: CharacterClass
    _health: int

    @property
    def health(self) -> int:
        return self._health

    @health.setter
    def health(self, new_value: int) -> None:
        self._health = max(0, new_value)

    def __init__(self, name: str, character_class: CharacterClass, health: int) -> None:
        self.level: int = 1
        self.name = name
        self.character_class = character_class
        self.health = health

    def get_character_summary(self) -> str:
        message = f"Character Created!\nName: {self.name}\nClass: {self.character_class}\nHealth: {self.health}\nLevel: {self.level}/{Character.MAX_LEVEL}"
        return message


@dataclass
class Item:
    name: str
    healing: int
