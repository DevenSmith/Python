from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from tinyrpg.database_models import UserRecord


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=50)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Display name cannot be blank")
        return stripped


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    created_at: datetime
    role: str
    email_verified: bool

    @classmethod
    def from_record(cls, user: UserRecord) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
            role=user.role,
            email_verified=user.email_verified_at is not None,
        )


class UserUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Display name cannot be blank")
        return stripped


class PasswordChange(BaseModel):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)


class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    user_agent: str
    ip_address: str
    current: bool


class SecurityAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    created_at: datetime
    ip_address: str
    user_agent: str
