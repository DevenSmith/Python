from ui import greet_player
from ui import print_available_classes
from ui import print_visited_locations
from ui import print_durable_classes
from models import Item, Character


def print_all_items(collection: list[Item]) -> None:
    print("Inventory:")
    for item in collection:
        print(f"- {item.name}: +{item.healing} HP")


def find_item(collection: list[Item], name: str) -> Item | None:
    for item in collection:
        if item.name == name:
            return item
    return None


def save_character_summary(summary: str, file_name: str) -> None:
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(summary)


def load_character_summary(file_name: str) -> str:
    with open(file_name, "r", encoding="utf-8") as file:
        text = file.read()
        return text


def main() -> None:
    acceptable_classes: dict[str, int] = {"Warrior": 120, "Mage": 80, "Rogue": 100}

    player_name = input("What is your name? ")

    greet_player(player_name)

    print_available_classes(acceptable_classes)

    while True:
        player_class = input("What is your class? ")
        if player_class in acceptable_classes:
            break
        print("Your character class is invalid")

    class_health = acceptable_classes[player_class]

    player_character: Character = Character(player_name, player_class, class_health)

    while True:
        try:
            trap_damage = int(input("How much trap damage should you take? "))
        except ValueError:
            print("That was not an integer. Try again")
            continue

        if trap_damage >= 0:
            break
        print("Pick a nonnegative number")

    player_character.health -= trap_damage

    summary = player_character.get_character_summary()
    print(summary)

    visited_locations: set[str] = {"Village"}
    visited_locations.add("Forest")
    visited_locations.add("Forest")

    print_visited_locations(visited_locations)

    durable_classes: list[str] = [
        durable_class
        for durable_class, starting_health in acceptable_classes.items()
        if starting_health >= 100
    ]

    print_durable_classes(durable_classes)

    items: list[Item] = []
    items.append(Item("Potion", 25))
    items.append(Item("Greater Potion", 50))
    print_all_items(items)

    used_item_name = input("Which item would you like to use? ")
    used_item = find_item(items, used_item_name)
    if used_item is None:
        print("Item not found!")
    else:
        print(f"Using {used_item.name}")
        player_character.health += used_item.healing
        print(f"Players current health is {player_character.health} HP")

    summary = player_character.get_character_summary()
    save_character_summary(summary, "character.txt")
    print("File written")

    load_summary = load_character_summary("character.txt")
    print("Loaded Character:")
    print(load_summary)


if __name__ == "__main__":
    main()