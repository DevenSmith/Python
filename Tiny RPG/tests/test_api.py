from fastapi.testclient import TestClient

from tinyrpg.api import app


client = TestClient(app)


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