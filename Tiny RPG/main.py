def greet_player(name: str) -> None:
    print(f"Welcome, {name}!")


def create_character(name: str, character_class: str) -> str:
    message = f"Character Created!\nName: {name}\nClass: {character_class}"
    return message


def print_available_classes(collection: list[str]) -> None:
    print("Available Classes:")
    for available_character_class in collection:
        print("-", available_character_class)


acceptable_classes: list[str] = ["Warrior", "Mage", "Rogue"]

player_name = input("What is your name? ")
greet_player(player_name)

print_available_classes(acceptable_classes)

while True:
    player_class = input("What is your class? ")
    if player_class in acceptable_classes:
        break
    print("Your character class is invalid")

summary = create_character(player_name, player_class)
print(summary)