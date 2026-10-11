"""Download the Tiny Shakespeare corpus used by the training lessons."""

from pathlib import Path
from urllib.request import urlopen

DATA_URL = (
    "https://raw.githubusercontent.com/karpathy/char-rnn/"
    "master/data/tinyshakespeare/input.txt"
)


def main() -> None:
    project_directory = Path(__file__).resolve().parents[1]
    data_directory = project_directory / "data"
    output_path = data_directory / "tiny_shakespeare.txt"

    if output_path.exists():
        print(f"Dataset already exists: {output_path}")
        return

    data_directory.mkdir(parents=True, exist_ok=True)

    with urlopen(DATA_URL, timeout=60) as response:
        text = response.read().decode("utf-8")

    output_path.write_text(text, encoding="utf-8")
    print(f"Downloaded {len(text):,} characters to {output_path}")


if __name__ == "__main__":
    main()
