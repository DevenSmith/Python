from ui import greet_player
from ui import print_available_classes
from ui import print_visited_locations
from ui import print_durable_classes


class Character:
    name: str
    character_class: str
    health: int
    def __init__(self, name: str, character_class: str, health: int) -> None:
        self.name = name
        self.character_class = character_class
        self.health = health

    def get_character_summary(self) -> str:
        message = f"Character Created!\nName: {self.name}\nClass: {self.character_class}\nHealth: {self.health}"
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

    player_character: Character = Character(player_name, player_class, class_health)

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


if __name__ == "__main__":
    main()