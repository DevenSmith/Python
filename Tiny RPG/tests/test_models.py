from tinyrpg.models import Character


def test_health_cannot_be_negative() -> None:
    test_character: Character = Character("testy", "Test Class", 100)
    test_character.health = -101
    assert test_character.health == 0


def test_character_initializes_attributes() -> None:
    test_character: Character = Character("testy", "Test Class", 100)
    assert test_character.name == "testy"
    assert test_character.character_class == "Test Class"
    assert test_character.health == 100
    assert test_character.level == 1
