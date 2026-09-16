import pytest
from pydantic import ValidationError

from tinyrpg.config import DEVELOPMENT_JWT_SECRET, Settings


def test_development_settings_use_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///./tiny_rpg.db"
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.use_secure_cookies is False


def test_frontend_origins_are_parsed_as_an_allowlist() -> None:
    settings = Settings(
        _env_file=None,
        frontend_origins="https://game.example/, https://admin.example",
    )

    assert settings.cors_origins == [
        "https://game.example",
        "https://admin.example",
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"jwt_secret_key": DEVELOPMENT_JWT_SECRET},
        {"cookie_secure": False},
        {"frontend_origins": "*"},
        {"frontend_origins": "http://tinyrpg.example"},
        {"frontend_origins": "https://localhost"},
    ],
)
def test_production_rejects_insecure_configuration(overrides: dict[str, object]) -> None:
    values: dict[str, object] = {
        "environment": "production",
        "jwt_secret_key": "a-unique-production-secret-that-is-long-enough",
        "frontend_origins": "https://tinyrpg.example",
        "cookie_secure": True,
        **overrides,
    }
    if overrides == {}:
        values["jwt_secret_key"] = DEVELOPMENT_JWT_SECRET

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_production_accepts_explicit_secure_configuration() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://app:secret@db/tinyrpg",
        frontend_origins="https://tinyrpg.example,https://admin.tinyrpg.example",
        jwt_secret_key="a-unique-production-secret-that-is-long-enough",
    )

    assert settings.use_secure_cookies is True
    assert settings.cors_origins == [
        "https://tinyrpg.example",
        "https://admin.tinyrpg.example",
    ]
