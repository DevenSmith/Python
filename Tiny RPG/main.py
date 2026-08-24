def greet_player(name: str) -> None:
    print(f"Welcome, {name}!")


def create_character(name: str, character_class: str) -> str:
    message = f"Character Created!\nName: {name}\nClass: {character_class}"
    return message


acceptable_classes: list[str] = ["Warrior", "Mage", "Rogue"]

player_name = input("What is your name? ")
greet_player(player_name)
player_class = input("What is your class? ")
if player_class in acceptable_classes:
    summary = create_character(player_name, player_class)
    print(summary)
else:
    print("Your character class is invalid")

