from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tinyrpg import database_models  # noqa: F401
from tinyrpg.api import app
from tinyrpg.config import settings
from tinyrpg.database import Base, get_database_session
from tinyrpg.database_models import UserRecord
from tinyrpg.security import create_access_token, verify_password

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


def test_register_user_hashes_password_and_returns_safe_fields() -> None:
    response = client.post(
        "/users",
        json={
            "email": "  Ada@Example.COM ",
            "display_name": "  Ada  ",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"
    assert response.json()["display_name"] == "Ada"
    assert set(response.json()) == {"id", "email", "display_name", "created_at"}

    with TestSession() as session:
        saved_user = session.scalar(
            select(UserRecord).where(UserRecord.email == "ada@example.com")
        )
        assert saved_user is not None
        assert saved_user.password_hash != "correct-horse-battery-staple"
        assert verify_password(
            "correct-horse-battery-staple", saved_user.password_hash
        )


def test_register_user_rejects_duplicate_normalized_email() -> None:
    first = client.post(
        "/users",
        json={
            "email": "ada@example.com",
            "display_name": "Ada",
            "password": "first-password",
        },
    )
    duplicate = client.post(
        "/users",
        json={
            "email": "ADA@EXAMPLE.COM",
            "display_name": "Other Ada",
            "password": "second-password",
        },
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_register_user_validates_all_public_fields() -> None:
    response = client.post(
        "/users",
        json={"email": "not-an-email", "display_name": " ", "password": "short"},
    )

    assert response.status_code == 422
    error_locations = {tuple(error["loc"]) for error in response.json()["detail"]}
    assert ("body", "email") in error_locations
    assert ("body", "display_name") in error_locations
    assert ("body", "password") in error_locations


def register_test_user() -> dict[str, object]:
    response = client.post(
        "/users",
        json={
            "email": "ada@example.com",
            "display_name": "Ada",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_login_returns_signed_expiring_bearer_token() -> None:
    user = register_test_user()

    response = client.post(
        "/auth/token",
        json={
            "email": "ADA@EXAMPLE.COM",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    payload = jwt.decode(
        response.json()["access_token"],
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )
    assert payload["sub"] == str(user["id"])
    assert payload["exp"] - payload["iat"] == 30 * 60


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ada@example.com", "wrong-password"),
        ("missing@example.com", "wrong-password"),
    ],
)
def test_login_rejects_invalid_credentials_with_same_response(
    email: str, password: str
) -> None:
    register_test_user()

    response = client.post(
        "/auth/token",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_disabled_user() -> None:
    register_test_user()
    with TestSession() as session:
        user = session.scalar(
            select(UserRecord).where(UserRecord.email == "ada@example.com")
        )
        assert user is not None
        user.disabled_at = datetime.now(UTC)
        session.commit()

    response = client.post(
        "/auth/token",
        json={
            "email": "ada@example.com",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 401


def login_test_user() -> tuple[dict[str, object], str]:
    user = register_test_user()
    response = client.post(
        "/auth/token",
        json={
            "email": "ada@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 200
    return user, response.json()["access_token"]


def test_users_me_authenticates_bearer_token() -> None:
    user, token = login_test_user()

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == user


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic abc123", "Bearer not-a-jwt"],
)
def test_users_me_rejects_missing_or_invalid_credentials(
    authorization: str | None,
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}

    response = client.get("/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_users_me_rejects_expired_token() -> None:
    user = register_test_user()
    user_id = user["id"]
    assert isinstance(user_id, int)
    expired_token = create_access_token(
        user_id,
        now=datetime.now(UTC) - timedelta(minutes=31),
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_users_me_rejects_token_after_account_is_disabled() -> None:
    user, token = login_test_user()
    user_id = user["id"]
    assert isinstance(user_id, int)
    with TestSession() as session:
        saved_user = session.get(UserRecord, user_id)
        assert saved_user is not None
        saved_user.disabled_at = datetime.now(UTC)
        session.commit()

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


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


def test_list_characters_uses_cursor_pagination() -> None:
    for name in ["Ada", "Bob", "Cora"]:
        created = client.post(
            "/characters",
            json={"name": name, "character_class": "Mage"},
        )
        assert created.status_code == 201

    first_page = client.get("/characters?limit=2")

    assert first_page.status_code == 200
    assert [character["name"] for character in first_page.json()] == ["Ada", "Bob"]
    cursor = first_page.headers["x-next-cursor"]

    second_page = client.get(f"/characters?after_id={cursor}&limit=2")

    assert second_page.status_code == 200
    assert [character["name"] for character in second_page.json()] == ["Cora"]
    assert "x-next-cursor" not in second_page.headers


def test_list_characters_validates_pagination_query() -> None:
    assert client.get("/characters?limit=0").status_code == 422
    assert client.get("/characters?limit=101").status_code == 422
    assert client.get("/characters?after_id=-1").status_code == 422


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


def create_test_character() -> int:
    response = client.post(
        "/characters",
        json={"name": "Ada", "character_class": "Mage"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_level_up_character() -> None:
    character_id = create_test_character()

    response = client.post(f"/characters/{character_id}/level-up")

    assert response.status_code == 200
    assert response.json()["id"] == character_id
    assert response.json()["level"] == 2

    saved_character = client.get(f"/characters/{character_id}")

    assert saved_character.status_code == 200
    assert saved_character.json()["level"] == 2


def test_patch_character_updates_only_supplied_fields() -> None:
    character_id = create_test_character()

    response = client.patch(
        f"/characters/{character_id}",
        json={"name": "  Ada the Wise  "},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Ada the Wise"
    assert response.json()["health"] == 80
    assert response.json()["character_class"] == "Mage"


def test_patch_character_validates_request_and_missing_resource() -> None:
    character_id = create_test_character()

    empty = client.patch(f"/characters/{character_id}", json={})
    invalid_health = client.patch(
        f"/characters/{character_id}",
        json={"health": -1},
    )
    missing = client.patch("/characters/999", json={"health": 10})

    assert empty.status_code == 422
    assert invalid_health.status_code == 422
    assert missing.status_code == 404


def test_cors_allows_patch_from_react_development_origin() -> None:
    response = client.options(
        "/characters/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )

    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_add_and_list_inventory_item() -> None:
    character_id = create_test_character()
    item_data = {
        "name": "Health Potion",
        "quantity": 3,
        "healing": 25,
        "damage": 0,
    }

    created = client.post(f"/characters/{character_id}/inventory", json=item_data)
    assert created.status_code == 201
    assert created.json() == {
        "id": created.json()["id"],
        "character_id": character_id,
        **item_data,
    }

    inventory = client.get(f"/characters/{character_id}/inventory")
    assert inventory.status_code == 200
    assert inventory.json() == [created.json()]


def test_existing_inventory_item_increases_quantity() -> None:
    character_id = create_test_character()
    item_data = {
        "name": "Dagger",
        "quantity": 1,
        "healing": 0,
        "damage": 10,
    }
    first = client.post(f"/characters/{character_id}/inventory", json=item_data)
    second = client.post(f"/characters/{character_id}/inventory", json=item_data)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["quantity"] == 2


def test_inventory_rejects_missing_character_and_invalid_item() -> None:
    missing = client.post(
        "/characters/999/inventory",
        json={"name": "Dagger", "quantity": 1, "damage": 10},
    )
    assert missing.status_code == 404

    character_id = create_test_character()
    invalid = client.post(
        f"/characters/{character_id}/inventory",
        json={"name": " ", "quantity": 0, "healing": -1, "damage": 0},
    )
    assert invalid.status_code == 422
    error_locations = {tuple(error["loc"]) for error in invalid.json()["detail"]}
    assert ("body", "name") in error_locations
    assert ("body", "quantity") in error_locations
    assert ("body", "healing") in error_locations


def test_existing_item_rejects_different_effects() -> None:
    character_id = create_test_character()
    url = f"/characters/{character_id}/inventory"
    created = client.post(
        url,
        json={"name": "Health Potion", "quantity": 1, "healing": 25},
    )
    conflict = client.post(
        url,
        json={"name": "Health Potion", "quantity": 2, "healing": 50},
    )

    assert created.status_code == 201
    assert conflict.status_code == 409
    inventory = client.get(url).json()
    assert inventory[0]["quantity"] == 1
    assert inventory[0]["healing"] == 25


def test_delete_inventory_item_returns_no_content() -> None:
    character_id = create_test_character()
    inventory_url = f"/characters/{character_id}/inventory"
    created = client.post(
        inventory_url,
        json={"name": "Dagger", "quantity": 1, "damage": 10},
    )
    item_id = created.json()["id"]

    deleted = client.delete(f"{inventory_url}/{item_id}")

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(inventory_url).json() == []


def test_delete_inventory_item_checks_its_character() -> None:
    first_character_id = create_test_character()
    second_character_id = create_test_character()
    created = client.post(
        f"/characters/{first_character_id}/inventory",
        json={"name": "Dagger", "quantity": 1, "damage": 10},
    )
    item_id = created.json()["id"]

    wrong_owner = client.delete(
        f"/characters/{second_character_id}/inventory/{item_id}"
    )
    missing_character = client.delete(f"/characters/999/inventory/{item_id}")

    assert wrong_owner.status_code == 404
    assert missing_character.status_code == 404
    assert client.get(f"/characters/{first_character_id}/inventory").json() == [
        created.json()
    ]


def test_put_replaces_complete_inventory_item_and_is_idempotent() -> None:
    character_id = create_test_character()
    inventory_url = f"/characters/{character_id}/inventory"
    created = client.post(
        inventory_url,
        json={"name": "Dagger", "quantity": 1, "healing": 0, "damage": 10},
    )
    item_url = f"{inventory_url}/{created.json()['id']}"
    replacement = {
        "name": "Enchanted Dagger",
        "quantity": 2,
        "healing": 0,
        "damage": 25,
    }

    first = client.put(item_url, json=replacement)
    second = client.put(item_url, json=replacement)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert second.json() == {
        "id": created.json()["id"],
        "character_id": character_id,
        **replacement,
    }


def test_put_requires_complete_valid_representation() -> None:
    character_id = create_test_character()
    created = client.post(
        f"/characters/{character_id}/inventory",
        json={"name": "Dagger", "quantity": 1, "damage": 10},
    )
    item_url = f"/characters/{character_id}/inventory/{created.json()['id']}"

    missing_damage = client.put(
        item_url,
        json={"name": "Sword", "quantity": 1, "healing": 0},
    )
    wrong_character = client.put(
        f"/characters/999/inventory/{created.json()['id']}",
        json={"name": "Sword", "quantity": 1, "healing": 0, "damage": 20},
    )

    assert missing_damage.status_code == 422
    assert wrong_character.status_code == 404
    assert client.get(f"/characters/{character_id}/inventory").json() == [
        created.json()
    ]


def test_put_rejects_duplicate_item_name() -> None:
    character_id = create_test_character()
    inventory_url = f"/characters/{character_id}/inventory"
    dagger = client.post(
        inventory_url,
        json={"name": "Dagger", "quantity": 1, "damage": 10},
    ).json()
    client.post(
        inventory_url,
        json={"name": "Potion", "quantity": 1, "healing": 10},
    )

    conflict = client.put(
        f"{inventory_url}/{dagger['id']}",
        json={"name": "Potion", "quantity": 5, "healing": 20, "damage": 0},
    )

    assert conflict.status_code == 409
    assert client.get(inventory_url).json()[0] == dagger
