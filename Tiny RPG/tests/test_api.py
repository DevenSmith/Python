from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tinyrpg import database_models  # noqa: F401
from tinyrpg.api import app, login_rate_limiter
from tinyrpg.config import settings
from tinyrpg.database import Base, get_database_session
from tinyrpg.database_models import (
    SecurityAuditEventRecord,
    UserRecord,
    UserSessionRecord,
)
from tinyrpg.security import create_access_token, verify_password

client = TestClient(app)
unauthenticated_client = TestClient(app)
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "email_delivery_enabled", False)
    client.cookies.clear()
    unauthenticated_client.cookies.clear()
    login_rate_limiter.clear()
    Base.metadata.create_all(test_engine)

    with TestSession() as session:
        owner = UserRecord(
            email="test-owner@example.com",
            display_name="Test Owner",
            password_hash="not-used-by-these-tests",
        )
        session.add(owner)
        session.commit()
        owner_id = owner.id

    client.headers["Authorization"] = f"Bearer {create_access_token(owner_id)}"

    def get_test_session() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_database_session] = get_test_session

    yield

    del client.headers["Authorization"]
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
    assert set(response.json()) == {
        "id", "email", "display_name", "created_at", "role", "email_verified"
    }
    assert response.json()["role"] == "player"
    assert response.json()["email_verified"] is False
    assert response.headers["x-verification-token"]

    with TestSession() as session:
        saved_user = session.scalar(
            select(UserRecord).where(UserRecord.email == "ada@example.com")
        )
        assert saved_user is not None
        assert saved_user.password_hash != "correct-horse-battery-staple"
        assert verify_password(
            "correct-horse-battery-staple", saved_user.password_hash
        )


def test_production_does_not_expose_verification_token_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "environment", "production")

    response = client.post(
        "/users",
        json={
            "email": "private-token@example.com",
            "display_name": "Private Token",
            "password": "secure-password",
        },
    )

    assert response.status_code == 201
    assert "x-verification-token" not in response.headers


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


def csrf_headers(test_client: TestClient = client) -> dict[str, str]:
    return {"X-CSRF-Token": test_client.cookies["csrf_token"]}


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

    response = unauthenticated_client.get("/users/me", headers=headers)

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


def test_account_profile_can_update_display_name() -> None:
    user, token = login_test_user()

    response = client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "  Ada Lovelace  "},
    )

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["display_name"] == "Ada Lovelace"


def test_change_password_requires_current_password_and_revokes_sessions() -> None:
    _, token = login_test_user()
    headers = {"Authorization": f"Bearer {token}"}
    wrong = client.post(
        "/users/me/password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "new-password"},
    )
    changed = client.post(
        "/users/me/password",
        headers=headers,
        json={
            "current_password": "correct-horse-battery-staple",
            "new_password": "new-password",
        },
    )

    assert wrong.status_code == 400
    assert changed.status_code == 200
    assert client.post("/auth/refresh").status_code == 401
    assert client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "new-password"},
    ).status_code == 200


def test_logout_all_devices_revokes_refresh_tokens() -> None:
    _, token = login_test_user()

    response = client.post(
        "/users/me/logout-all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert client.post("/auth/refresh").status_code == 401


def test_disable_account_blocks_existing_access_token_and_login() -> None:
    _, token = login_test_user()
    headers = {"Authorization": f"Bearer {token}"}

    disabled = client.delete("/users/me", headers=headers)

    assert disabled.status_code == 204
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.post(
        "/auth/token",
        json={
            "email": "ada@example.com",
            "password": "correct-horse-battery-staple",
        },
    ).status_code == 401


def test_character_endpoints_require_authentication() -> None:
    response = unauthenticated_client.get("/characters")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_user_cannot_access_another_users_character() -> None:
    character_id = create_test_character()
    client.post(
        "/users",
        json={
            "email": "bob@example.com",
            "display_name": "Bob",
            "password": "bobs-secure-password",
        },
    )
    login = client.post(
        "/auth/token",
        json={"email": "bob@example.com", "password": "bobs-secure-password"},
    )
    bob_token = login.json()["access_token"]

    response = client.get(
        f"/characters/{character_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to access this character"
    }


def test_refresh_cookie_rotates_and_old_token_cannot_be_reused() -> None:
    register_test_user()
    login = client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
    )
    old_refresh_token = login.cookies["refresh_token"]
    old_csrf_token = login.cookies["csrf_token"]

    refreshed = client.post("/auth/refresh", headers=csrf_headers())

    assert refreshed.status_code == 200
    assert refreshed.json()["token_type"] == "bearer"
    assert refreshed.cookies["refresh_token"] != old_refresh_token

    replay_client = TestClient(app)
    replay_client.cookies.set("refresh_token", old_refresh_token, path="/auth")
    replay_client.cookies.set("csrf_token", old_csrf_token, path="/")
    replay = replay_client.post(
        "/auth/refresh", headers={"X-CSRF-Token": old_csrf_token}
    )
    assert replay.status_code == 401
    assert client.post("/auth/refresh", headers=csrf_headers()).status_code == 401

    with TestSession() as session:
        login_session = session.scalar(select(UserSessionRecord))
        assert login_session is not None
        assert login_session.compromised_at is not None


def test_user_can_list_and_revoke_an_individual_session() -> None:
    register_test_user()
    first_login = client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        headers={"User-Agent": "First browser"},
    )
    second_client = TestClient(app)
    second_login = second_client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        headers={"User-Agent": "Second browser"},
    )
    first_access_token = first_login.json()["access_token"]
    second_access_token = second_login.json()["access_token"]

    listed = client.get(
        "/users/me/sessions",
        headers={"Authorization": f"Bearer {first_access_token}"},
    )

    assert listed.status_code == 200
    assert len(listed.json()) == 2
    current = next(item for item in listed.json() if item["current"])
    other = next(item for item in listed.json() if not item["current"])
    assert current["user_agent"] == "First browser"
    assert other["user_agent"] == "Second browser"

    revoked = client.delete(
        f"/users/me/sessions/{other['id']}",
        headers={"Authorization": f"Bearer {first_access_token}"},
    )

    assert revoked.status_code == 204
    assert second_client.get(
        "/users/me", headers={"Authorization": f"Bearer {second_access_token}"}
    ).status_code == 401
    assert client.get(
        "/users/me", headers={"Authorization": f"Bearer {first_access_token}"}
    ).status_code == 200


def test_security_events_record_account_activity_and_are_user_scoped() -> None:
    register_test_user()
    login = client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
        headers={"User-Agent": "Audit test browser"},
    )
    token = login.json()["access_token"]

    failed_login = client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "wrong-password"},
    )
    events = client.get(
        "/users/me/security-events?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert failed_login.status_code == 401
    assert events.status_code == 200
    assert [event["event_type"] for event in events.json()] == [
        "login_failed",
        "login_succeeded",
    ]
    assert events.json()[1]["user_agent"] == "Audit test browser"
    assert set(events.json()[0]) == {
        "id", "event_type", "created_at", "ip_address", "user_agent"
    }
    with TestSession() as session:
        assert len(list(session.scalars(select(SecurityAuditEventRecord)))) == 2


def test_refresh_requires_matching_csrf_cookie_and_header() -> None:
    register_test_user()
    client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
    )

    missing = client.post("/auth/refresh")
    incorrect = client.post(
        "/auth/refresh", headers={"X-CSRF-Token": "incorrect-token"}
    )
    valid = client.post("/auth/refresh", headers=csrf_headers())

    assert missing.status_code == 403
    assert incorrect.status_code == 403
    assert valid.status_code == 200


def test_logout_revokes_refresh_token() -> None:
    register_test_user()
    client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
    )

    logged_out = client.post("/auth/logout", headers=csrf_headers())
    refresh_after_logout = client.post("/auth/refresh")

    assert logged_out.status_code == 204
    assert refresh_after_logout.status_code == 401


def test_logout_requires_csrf_token_when_refresh_cookie_exists() -> None:
    register_test_user()
    client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
    )

    rejected = client.post("/auth/logout")

    assert rejected.status_code == 403
    assert client.post("/auth/refresh", headers=csrf_headers()).status_code == 200


def test_email_verification_token_is_single_use() -> None:
    registered = client.post(
        "/users",
        json={
            "email": "verify@example.com",
            "display_name": "Verify Me",
            "password": "secure-password",
        },
    )
    token = registered.headers["x-verification-token"]

    verified = client.post("/auth/verify-email", json={"token": token})
    reused = client.post("/auth/verify-email", json={"token": token})

    assert verified.status_code == 200
    assert reused.status_code == 401
    with TestSession() as session:
        user = session.scalar(select(UserRecord).where(UserRecord.email == "verify@example.com"))
        assert user is not None
        assert user.email_verified_at is not None


def test_requesting_another_verification_token_revokes_the_old_one() -> None:
    registered = client.post(
        "/users",
        json={
            "email": "verify@example.com",
            "display_name": "Verify Me",
            "password": "secure-password",
        },
    )
    old_token = registered.headers["x-verification-token"]

    requested = client.post(
        "/auth/verify-email/request", json={"email": "verify@example.com"}
    )
    new_token = requested.headers["x-verification-token"]

    assert requested.status_code == 202
    assert new_token != old_token
    assert client.post("/auth/verify-email", json={"token": old_token}).status_code == 401
    assert client.post("/auth/verify-email", json={"token": new_token}).status_code == 200


def test_password_reset_changes_password_and_hides_unknown_accounts() -> None:
    register_test_user()
    requested = client.post(
        "/auth/password-reset/request", json={"email": "ada@example.com"}
    )
    token = requested.headers["x-password-reset-token"]
    unknown = client.post(
        "/auth/password-reset/request", json={"email": "missing@example.com"}
    )

    reset = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "a-brand-new-password"},
    )
    old_login = client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "correct-horse-battery-staple"},
    )
    new_login = client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "a-brand-new-password"},
    )

    assert requested.status_code == 202
    assert unknown.status_code == 202
    assert unknown.json() == requested.json()
    assert "x-password-reset-token" not in unknown.headers
    assert reset.status_code == 200
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_password_reset_unlocks_login_after_rate_limit() -> None:
    register_test_user()
    requested = client.post(
        "/auth/password-reset/request", json={"email": "ada@example.com"}
    )
    reset_token = requested.headers["x-password-reset-token"]
    for _ in range(settings.login_attempt_limit):
        response = unauthenticated_client.post(
            "/auth/token",
            json={"email": "ada@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
    assert unauthenticated_client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "wrong-password"},
    ).status_code == 429

    reset = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "new-password"},
    )
    login = unauthenticated_client.post(
        "/auth/token",
        json={"email": "ada@example.com", "password": "new-password"},
    )

    assert reset.status_code == 200
    assert login.status_code == 200


def test_admin_endpoint_distinguishes_authentication_from_authorization() -> None:
    user, token = login_test_user()
    headers = {"Authorization": f"Bearer {token}"}

    forbidden = client.get("/admin/users", headers=headers)
    with TestSession() as session:
        saved_user = session.get(UserRecord, user["id"])
        assert saved_user is not None
        saved_user.role = "admin"
        session.commit()
    allowed = client.get("/admin/users", headers=headers)

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert any(account["email"] == "ada@example.com" for account in allowed.json())


def test_login_rate_limit_returns_429_after_repeated_failures() -> None:
    register_test_user()

    responses = [
        unauthenticated_client.post(
            "/auth/token",
            json={"email": "ada@example.com", "password": "wrong-password"},
        )
        for _ in range(settings.login_attempt_limit + 1)
    ]

    assert all(response.status_code == 401 for response in responses[:-1])
    assert responses[-1].status_code == 429
    assert responses[-1].headers["retry-after"] == str(
        settings.login_attempt_window_minutes * 60
    )


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
