"""Static game definitions that do not need database storage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Monster:
    slug: str
    name: str
    health: int
    damage: int
    xp_reward: int


MONSTERS: dict[str, Monster] = {
    "goblin": Monster(slug="goblin", name="Goblin", health=18, damage=5, xp_reward=50),
    "kobold": Monster(slug="kobold", name="Kobold", health=12, damage=4, xp_reward=35),
    "giant-rat": Monster(
        slug="giant-rat", name="Giant Rat", health=10, damage=3, xp_reward=25
    ),
    "giant-spider": Monster(
        slug="giant-spider", name="Giant Spider", health=24, damage=6, xp_reward=75
    ),
}


def experience_required_for_level(level: int) -> int:
    return level * 100
