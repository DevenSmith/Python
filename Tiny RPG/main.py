from ui import greet_player
from ui import print_available_classes
from ui import print_visited_locations
from ui import print_durable_classes


def create_character(name: str, character_class: str, starting_hp: int) -> str:
    message = f"Character Created!\nName: {name}\nClass: {character_class}\nHealth: {starting_hp}"
    return message


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
    summary = create_character(player_name, player_class, class_health)
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


if __name__ == "__main__":
    main()