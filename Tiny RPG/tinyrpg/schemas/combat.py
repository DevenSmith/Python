from typing import Literal

from pydantic import BaseModel

CombatStyle = Literal["balanced", "aggressive", "defensive"]


class MonsterResponse(BaseModel):
    slug: str
    name: str
    health: int
    damage: int


class CombatRoundResponse(BaseModel):
    round_number: int
    character_roll: int
    outcome: Literal["miss", "hit", "critical"]
    character_damage: int
    monster_health: int
    monster_damage: int
    character_health: int


class FightResponse(BaseModel):
    character_id: int
    monster: MonsterResponse
    style: CombatStyle
    victory: bool
    character_health: int
    rounds: list[CombatRoundResponse]
