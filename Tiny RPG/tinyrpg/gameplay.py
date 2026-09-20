"""Static game definitions that do not need database storage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Monster:
    slug: str
    name: str
    health: int
    damage: int


MONSTERS: dict[str, Monster] = {
    "goblin": Monster(slug="goblin", name="Goblin", health=18, damage=5),
    "kobold": Monster(slug="kobold", name="Kobold", health=12, damage=4),
    "giant-rat": Monster(slug="giant-rat", name="Giant Rat", health=10, damage=3),
    "giant-spider": Monster(
        slug="giant-spider", name="Giant Spider", health=24, damage=6
    ),
}
