from random import randint
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from tinyrpg.database_models import CharacterRecord
from tinyrpg.dependencies import CurrentUser, DatabaseSession, get_owned_character
from tinyrpg.models import CLASS_BASE_DAMAGE, CLASS_HEALTH, CharacterClass
from tinyrpg.schemas.characters import (
    AttackRollResponse,
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
    DamageRequest,
)

router = APIRouter(tags=["characters"])


@router.get("/classes")
def get_classes(minimum_health: int | None = None) -> dict[str, int]:
    return {
        character_class.value: health
        for character_class, health in CLASS_HEALTH.items()
        if minimum_health is None or health >= minimum_health
    }


@router.get("/classes/{character_class}")
def get_specific_class(character_class: CharacterClass) -> dict[str, int]:
    return {character_class.value: CLASS_HEALTH[character_class]}


@router.get("/characters")
def list_characters(
    session: DatabaseSession,
    current_user: CurrentUser,
    response: Response,
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[CharacterResponse]:
    statement = select(CharacterRecord).where(CharacterRecord.owner_id == current_user.id)
    if after_id is not None:
        statement = statement.where(CharacterRecord.id > after_id)
    characters = list(session.scalars(statement.order_by(CharacterRecord.id).limit(limit + 1)))
    page = characters[:limit]
    if len(characters) > limit:
        response.headers["X-Next-Cursor"] = str(page[-1].id)
    return [CharacterResponse.model_validate(character) for character in page]


@router.get("/characters/count")
def get_character_count(
    session: DatabaseSession, current_user: CurrentUser
) -> dict[str, int]:
    count = session.scalar(
        select(func.count()).select_from(CharacterRecord).where(
            CharacterRecord.owner_id == current_user.id
        )
    )
    return {"count": count or 0}


@router.get("/characters/{character_id}")
def get_character_by_id(
    character_id: int, session: DatabaseSession, current_user: CurrentUser
) -> CharacterResponse:
    return CharacterResponse.model_validate(
        get_owned_character(character_id, current_user, session)
    )


@router.post("/characters", status_code=status.HTTP_201_CREATED)
def create_character(
    character_data: CharacterCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = CharacterRecord(
        owner_id=current_user.id,
        name=character_data.name,
        character_class=character_data.character_class.value,
        health=CLASS_HEALTH[character_data.character_class],
        level=1,
    )
    session.add(character)
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@router.patch("/characters/{character_id}")
def update_character(
    character_id: int,
    changes: CharacterUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)
    if changes.name is not None:
        character.name = changes.name
    if changes.health is not None:
        character.health = changes.health
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@router.post("/characters/{character_id}/level-up")
def level_up_character(
    character_id: int, session: DatabaseSession, current_user: CurrentUser
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)
    character.level += 1
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@router.post("/characters/{character_id}/take-damage")
def take_character_damage(
    character_id: int,
    damage: DamageRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)
    character.health = max(0, character.health - damage.amount)
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@router.post("/characters/{character_id}/revive")
def revive_character(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(character_id, current_user, session)
    if character.health > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a defeated character can be revived",
        )
    character_class = CharacterClass(character.character_class)
    character.health = max(1, CLASS_HEALTH[character_class] // 2)
    session.commit()
    session.refresh(character)
    return CharacterResponse.model_validate(character)


@router.post("/characters/{character_id}/attack-roll")
def roll_character_attack(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> AttackRollResponse:
    character = get_owned_character(character_id, current_user, session)
    if character.health == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A defeated character cannot attack",
        )

    roll = randint(1, 20)
    character_class = CharacterClass(character.character_class)
    normal_damage = CLASS_BASE_DAMAGE[character_class] + character.level
    outcome: Literal["miss", "hit", "critical"]

    if roll == 1:
        outcome = "miss"
        damage = 0
    elif roll == 20:
        outcome = "critical"
        damage = normal_damage * 2
    else:
        outcome = "hit"
        damage = normal_damage

    return AttackRollResponse(
        character_id=character.id,
        character_name=character.name,
        roll=roll,
        outcome=outcome,
        damage=damage,
    )


@router.delete("/characters/{character_id}")
def delete_character_by_id(
    character_id: int, session: DatabaseSession, current_user: CurrentUser
) -> dict[str, str]:
    character = get_owned_character(character_id, current_user, session)
    session.delete(character)
    session.commit()
    return {"message": "Character deleted"}


@router.post("/characters/{character_id}/rest")
def rest_character(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CharacterResponse:
    character = get_owned_character(
        character_id,
        current_user,
        session,
    )

    character_class = CharacterClass(character.character_class)
    maximum_health = CLASS_HEALTH[character_class]

    if character.health == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A defeated character cannot rest",
        )

    if character.health >= maximum_health:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Character is already at maximum health",
        )

    rest_healing = max(1, maximum_health // 5)

    character.health = min(
        maximum_health,
        character.health + rest_healing,
    )

    session.commit()
    session.refresh(character)

    return CharacterResponse.model_validate(character)