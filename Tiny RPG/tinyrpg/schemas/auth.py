from pydantic import BaseModel, EmailStr, Field, SecretStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenRequest(BaseModel):
    token: SecretStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: SecretStr
    new_password: SecretStr = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str
