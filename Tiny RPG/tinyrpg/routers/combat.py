from random import randint
from typing import Literal

from fastapi import APIRouter, HTTPException, status

from tinyrpg.dependencies import CurrentUser, DatabaseSession, get_owned_character
from tinyrpg.gameplay import MONSTERS
from tinyrpg.models import CLASS_BASE_DAMAGE, CharacterClass
from tinyrpg.schemas.combat import (
    CombatRoundResponse,
    CombatStyle,
    FightResponse,
    MonsterResponse,
)

router = APIRouter(tags=["combat"])


@router.get("/monsters")
def list_monsters() -> list[MonsterResponse]:
    return [MonsterResponse.model_validate(monster, from_attributes=True) for monster in MONSTERS.values()]


@router.post("/characters/{character_id}/fight/{monster_slug}")
def fight_monster(
    character_id: int,
    monster_slug: str,
    session: DatabaseSession,
    current_user: CurrentUser,
    style: CombatStyle = "balanced",
    power_strike: bool = False,
) -> FightResponse:
    character = get_owned_character(character_id, current_user, session)
    if character.health == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A defeated character cannot fight",
        )
    monster = MONSTERS.get(monster_slug)
    if monster is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monster not found",
        )

    monster_health = monster.health
    character_class = CharacterClass(character.character_class)
    normal_damage = CLASS_BASE_DAMAGE[character_class] + character.level
    monster_damage = monster.damage
    if style == "aggressive":
        normal_damage += 3
        monster_damage += 2
    elif style == "defensive":
        normal_damage = max(1, normal_damage - 3)
        monster_damage = max(1, monster_damage - 2)
    if power_strike:
        normal_damage += 5
    rounds: list[CombatRoundResponse] = []

    while character.health > 0 and monster_health > 0:
        roll = randint(1, 20)
        outcome: Literal["miss", "hit", "critical"]
        if roll == 1 or (power_strike and roll <= 5):
            outcome = "miss"
            character_damage = 0
        elif roll == 20:
            outcome = "critical"
            character_damage = normal_damage * 2
        else:
            outcome = "hit"
            character_damage = normal_damage

        monster_health = max(0, monster_health - character_damage)
        damage_received = 0 if monster_health == 0 else monster_damage
        character.health = max(0, character.health - damage_received)
        rounds.append(
            CombatRoundResponse(
                round_number=len(rounds) + 1,
                character_roll=roll,
                outcome=outcome,
                character_damage=character_damage,
                monster_health=monster_health,
                monster_damage=damage_received,
                character_health=character.health,
            )
        )

    victory = monster_health == 0
    xp_awarded = monster.xp_reward if victory else 0
    character.experience += xp_awarded
    session.commit()
    return FightResponse(
        character_id=character.id,
        monster=MonsterResponse.model_validate(monster, from_attributes=True),
        style=style,
        power_strike=power_strike,
        xp_awarded=xp_awarded,
        character_experience=character.experience,
        victory=victory,
        character_health=character.health,
        rounds=rounds,
    )
