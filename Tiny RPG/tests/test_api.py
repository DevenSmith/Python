from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tinyrpg.api import app
from tinyrpg.database import Base, get_database_session
from tinyrpg import database_models  # noqa: F401

client = TestClient(app)
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def isolated_database() -> Iterator[None]:
    Base.metadata.create_all(test_engine)

    def get_test_session() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_database_session] = get_test_session

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def test_welcome_to_tiny_rpg() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to TinyRPG"}


def test_classes_min_health() -> None:
    response = client.get("/classes?minimum_health=100")

    assert response.status_code == 200
    assert response.json() == {
        "Warrior": 120,
        "Rogue": 100,
    }


def test_create_character() -> None:
    response = client.post(
        "/characters",
        json={
            "name": "Deven",
            "character_class": "Warrior",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["name"] == "Deven"
    assert response_data["character_class"] == "Warrior"
    assert response_data["health"] == 120
    assert response_data["level"] == 1
    assert isinstance(response_data["id"], int)


def test_create_character_rejects_blank_name() -> None:
    response = client.post(
        "/characters",
        json={
            "name": "   ",
            "character_class": "Warrior",
        },
    )

    assert response.status_code == 422


def test_get_missing_character() -> None:
    response = client.get("/characters/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Character not found"}


def test_cors_allows_react_development_origin() -> None:
    response = client.options(
        "/characters",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_cors_allows_delete_from_react_development_origin() -> None:
    response = client.options(
        "/characters/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert "DELETE" in response.headers["access-control-allow-methods"]

def test_list_characters_when_empty() -> None:
    response = client.get("/characters")

    assert response.status_code == 200
    assert response.json() == []


def test_list_characters_includes_created_character() -> None:
    first_created = client.post(
        "/characters",
        json={
            "name": "Avery",
            "character_class": "Mage",
        },
    )

    second_created = client.post(
        "/characters",
        json={
            "name": "Deven",
            "character_class": "Warrior",
        },
    )
    assert second_created.status_code == 201
    assert first_created.status_code == 201

    response = client.get("/characters")

    assert response.status_code == 200
    assert response.json() == [
        first_created.json(),
        second_created.json(),
    ]


def test_get_character_count() -> None:
    first_created = client.post(
        "/characters",
        json={
            "name": "Avery",
            "character_class": "Mage",
        },
    )
    assert first_created.status_code == 201

    count = client.get("/characters/count")
    assert count.status_code == 200
    assert count.json() == {"count": 1}


def test_delete_existing_character() -> None:
    create_response = client.post(
        "/characters",
        json={
            "name": "Avery",
            "character_class": "Mage",
        },
    )
  
    assert create_response.status_code == 201
    character_id = create_response.json()["id"]
    delete_response = client.delete(f"/characters/{character_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Character deleted"}

    get_response = client.get(f"/characters/{character_id}")
    assert get_response.status_code == 404


def test_delete_missing_character_returns_404() -> None:
    delete_response = client.delete("/characters/999")
    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "Character not found"}


def test_create_character_does_not_overwrite_after_deletion() -> None:
    first_response = client.post(
        "/characters",
        json={
            "name": "Avery",
            "character_class": "Mage",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/characters",
        json={
            "name": "Deven",
            "character_class": "Warrior",
        },
    )
    assert second_response.status_code == 201

    first_id = first_response.json()["id"]
    second_id = second_response.json()["id"]

    delete_response = client.delete(f"/characters/{first_id}")
    assert delete_response.status_code == 200

    third_response = client.post(
        "/characters",
        json={
            "name": "Kylie",
            "character_class": "Rogue",
        },
    )
    assert third_response.status_code == 201

    third_id = third_response.json()["id"]

    assert third_id != second_id

    roster_response = client.get("/characters")
    assert roster_response.status_code == 200

    roster_names = [
        character["name"]
        for character in roster_response.json()
    ]

    assert roster_names == ["Deven", "Kylie"]
