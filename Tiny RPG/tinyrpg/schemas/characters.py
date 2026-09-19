from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tinyrpg.models import CharacterClass


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    character_class: CharacterClass

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        stripped = name.strip()
        if not stripped:
            raise ValueError("Name cannot be blank")
        return stripped


class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    character_class: CharacterClass
    health: int
    level: int
    id: int
    owner_id: int


class DamageRequest(BaseModel):
    amount: int = Field(gt=0, le=10_000)


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    health: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        stripped = name.strip()
        if not stripped:
            raise ValueError("Name cannot be blank")
        return stripped

    @model_validator(mode="after")
    def require_a_change(self) -> "CharacterUpdate":
        if self.name is None and self.health is None:
            raise ValueError("Provide at least one field to update")
        return self
