"""Validation and response models for character inventory endpoints."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)
    healing: int = Field(default=0, ge=0)
    damage: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def validate_effect(self) -> "InventoryItemCreate":
        if self.healing == 0 and self.damage == 0:
            raise ValueError("An item must have healing or damage")
        return self


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    name: str
    quantity: int
    healing: int
    damage: int


class InventoryItemReplace(BaseModel):
    """Complete client-editable representation used by PUT."""

    name: str = Field(min_length=1, max_length=50)
    quantity: int = Field(gt=0)
    healing: int = Field(ge=0)
    damage: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped_name = name.strip()
        if not stripped_name:
            raise ValueError("Name cannot be blank")
        return stripped_name

    @model_validator(mode="after")
    def validate_effect(self) -> "InventoryItemReplace":
        if self.healing == 0 and self.damage == 0:
            raise ValueError("An item must have healing or damage")
        return self
