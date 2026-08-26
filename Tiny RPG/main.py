from pathlib import Path

from tinyrpg.models import Character, Item
from tinyrpg.storage import (
    load_character_json,
    load_character_summary,
    save_character_json,
    save_character_summary,
)
from tinyrpg.ui import (
    greet_player,
    print_available_classes,
    print_durable_classes,
    print_visited_locations,
)


def print_all_items(collection: list[Item]) -> None:
    print("Inventory:")
    for item in collection:
        print(f"- {item.name}: +{item.healing} HP")


def find_item(collection: list[Item], name: str) -> Item | None:
    for item in collection:
        if item.name == name:
            return item
    return None


def main() -> None:
    acceptable_classes: dict[str, int] = {"Warrior": 120, "Mage": 80, "Rogue": 100}
    project_directory = Path(__file__).parent
    text_save_path = project_directory / "character.txt"
    json_save_path = project_directory / "character.json"

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

    items: list[Item] = [Item("Potion", 25), Item("Greater Potion", 50)]
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
    save_character_summary(summary, text_save_path)
    print("File written")

    load_summary = load_character_summary(text_save_path)
    print("Loaded Character:")
    print(load_summary)

    save_character_json(player_character, json_save_path)
    loaded_character = load_character_json(json_save_path)
    print("Json Loaded Character:")
    json_summary = loaded_character.get_character_summary()
    print(json_summary)


if __name__ == "__main__":
    main()
