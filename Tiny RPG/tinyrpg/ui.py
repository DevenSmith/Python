from rich.console import Console

from tinyrpg.models import CharacterClass

console = Console()


def greet_player(name: str) -> None:
    console.print(f"Welcome, {name}!", style="bold green")


def print_available_classes(collection: dict[CharacterClass, int]) -> None:
    print("Available Classes:")
    for available_character_class, starting_health in collection.items():
        print(f"- {available_character_class}: {starting_health} HP")


def print_visited_locations(collection: set[str]) -> None:
    print("Visited Locations:")
    for visited_location in collection:
        print(visited_location)


def print_durable_classes(collection: list[str]) -> None:
    print("Durable Classes:")
    for durable_class in collection:
        print(durable_class)
