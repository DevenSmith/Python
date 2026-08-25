from dataclasses import dataclass


class Character:
    MAX_LEVEL: int = 10
    name: str
    character_class: str
    _health: int

    @property
    def health(self) -> int:
        return self._health

    @health.setter
    def health(self, new_value: int) -> None:
        if new_value > 0:
            self._health = new_value
        else:
            self._health = 0

    def __init__(self, name: str, character_class: str, health: int) -> None:
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