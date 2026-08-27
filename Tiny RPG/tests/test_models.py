from tinyrpg.models import Character, CharacterClass


def test_health_cannot_be_negative() -> None:
    test_character: Character = Character("testy", CharacterClass.WARRIOR, 100)
    test_character.health = -101
    assert test_character.health == 0


def test_character_initializes_attributes() -> None:
    test_character: Character = Character("testy", CharacterClass.WARRIOR, 100)
    assert test_character.name == "testy"
    assert test_character.character_class == CharacterClass.WARRIOR
    assert test_character.health == 100
    assert test_character.level == 1


def test_character_class_enum() -> None:
    assert CharacterClass.WARRIOR.value == "Warrior"
    assert str(CharacterClass.MAGE) == "Mage"
