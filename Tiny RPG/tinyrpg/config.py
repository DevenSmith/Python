from functools import cached_property
from typing import Literal
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = (
    "development-only-change-this-key-before-any-real-deployment-123456"
)


class Settings(BaseSettings):
    """Environment-driven application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "testing", "production"] = "development"
    app_name: str = "TinyRPG API"
    database_url: str = "sqlite:///./tiny_rpg.db"
    frontend_origins: str = "http://localhost:5173"
    jwt_secret_key: str = DEVELOPMENT_JWT_SECRET
    cookie_secure: bool | None = None
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    verification_token_expire_hours: int = 24
    password_reset_token_expire_minutes: int = 30
    login_attempt_limit: int = 5
    login_attempt_window_minutes: int = 5

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def use_secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment == "production"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment != "production":
            return self
        if self.jwt_secret_key == DEVELOPMENT_JWT_SECRET or len(self.jwt_secret_key) < 32:
            raise ValueError("Production requires a unique JWT_SECRET_KEY of at least 32 characters")
        if not self.use_secure_cookies:
            raise ValueError("Production requires COOKIE_SECURE=true")
        if not self.cors_origins:
            raise ValueError("Production requires at least one FRONTEND_ORIGINS entry")
        for origin in self.cors_origins:
            parsed = urlparse(origin)
            if origin == "*" or parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1"}:
                raise ValueError("Production frontend origins must be explicit HTTPS URLs")
        return self


settings = Settings()
