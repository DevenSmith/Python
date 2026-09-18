"""HTTP endpoints for inventory items owned through a character."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from tinyrpg.database_models import InventoryItemRecord
from tinyrpg.dependencies import CurrentUser, DatabaseSession, get_owned_character
from tinyrpg.models import CLASS_HEALTH, CharacterClass
from tinyrpg.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemReplace,
    InventoryItemResponse,
    UseItemResponse,
)

router = APIRouter(prefix="/characters/{character_id}/inventory", tags=["inventory"])


@router.get("")
def list_inventory_items(
    character_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> list[InventoryItemResponse]:
    get_owned_character(character_id, current_user, session)
    statement = (
        select(InventoryItemRecord)
        .where(InventoryItemRecord.character_id == character_id)
        .order_by(InventoryItemRecord.id)
    )
    return [
        InventoryItemResponse.model_validate(item)
        for item in session.scalars(statement)
    ]


@router.post("")
def add_inventory_item(
    character_id: int,
    item_data: InventoryItemCreate,
    response: Response,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> InventoryItemResponse:
    get_owned_character(character_id, current_user, session)
    item = session.scalar(
        select(InventoryItemRecord).where(
            InventoryItemRecord.character_id == character_id,
            InventoryItemRecord.name == item_data.name,
        )
    )
    if item is None:
        item = InventoryItemRecord(
            character_id=character_id,
            name=item_data.name,
            quantity=item_data.quantity,
            healing=item_data.healing,
            damage=item_data.damage,
        )
        session.add(item)
        response.status_code = status.HTTP_201_CREATED
    else:
        if item.healing != item_data.healing or item.damage != item_data.damage:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An item with this name already has different effects",
            )
        item.quantity += item_data.quantity
    session.commit()
    session.refresh(item)
    return InventoryItemResponse.model_validate(item)


@router.put("/{item_id}")
def replace_inventory_item(
    character_id: int,
    item_id: int,
    replacement: InventoryItemReplace,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> InventoryItemResponse:
    get_owned_character(character_id, current_user, session)
    item = session.scalar(
        select(InventoryItemRecord).where(
            InventoryItemRecord.id == item_id,
            InventoryItemRecord.character_id == character_id,
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )
    duplicate_id = session.scalar(
        select(InventoryItemRecord.id).where(
            InventoryItemRecord.character_id == character_id,
            InventoryItemRecord.name == replacement.name,
            InventoryItemRecord.id != item_id,
        )
    )
    if duplicate_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Character already has an item with this name",
        )
    item.name = replacement.name
    item.quantity = replacement.quantity
    item.healing = replacement.healing
    item.damage = replacement.damage
    session.commit()
    session.refresh(item)
    return InventoryItemResponse.model_validate(item)


@router.post("/{item_id}/use")
def use_inventory_item(
    character_id: int,
    item_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> UseItemResponse:
    character = get_owned_character(
        character_id,
        current_user,
        session,
    )

    item = session.scalar(
        select(InventoryItemRecord).where(
            InventoryItemRecord.id == item_id,
            InventoryItemRecord.character_id == character_id,
        )
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )

    if item.healing <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This item cannot heal the character",
        )

    character_class = CharacterClass(character.character_class)
    maximum_health = CLASS_HEALTH[character_class]

    if character.health >= maximum_health:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Character is already at maximum health",
        )

    missing_health = maximum_health - character.health
    healing_applied = min(item.healing, missing_health)
    item_name = item.name
    character.health += healing_applied
    item.quantity -= 1
    remaining_quantity = item.quantity
    if item.quantity == 0:
        session.delete(item)

    session.commit()

    return UseItemResponse(
        character_id=character.id,
        item_name=item_name,
        healing_applied=healing_applied,
        new_health=character.health,
        remaining_quantity=remaining_quantity,
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    character_id: int,
    item_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    get_owned_character(character_id, current_user, session)
    item = session.scalar(
        select(InventoryItemRecord).where(
            InventoryItemRecord.id == item_id,
            InventoryItemRecord.character_id == character_id,
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found for this character",
        )
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
