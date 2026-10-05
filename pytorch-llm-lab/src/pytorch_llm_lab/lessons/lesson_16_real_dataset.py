from pathlib import Path

import torch


project_directory = Path(__file__).resolve().parents[3]
data_path = project_directory / "data" / "tiny_shakespeare.txt"

text = data_path.read_text(encoding="utf-8")

characters = sorted(set(text))
vocabulary_size = len(characters)

print("Number of characters:")
print(len(text))

print("\nVocabulary size:")
print(vocabulary_size)

print("\nFirst 500 characters:")
print(repr(text[:500]))

character_to_id = {
    character: index
    for index, character in enumerate(characters)
}

id_to_character = {
    index: character
    for character, index in character_to_id.items()
}


def encode(text_to_encode):
    return [
        character_to_id[character]
        for character in text_to_encode
    ]


def decode(token_ids):
    return "".join(
        id_to_character[token_id]
        for token_id in token_ids
    )


encoded_text = torch.tensor(
    encode(text),
    dtype=torch.long,
)

split_position = int(0.9 * len(encoded_text))

training_data = encoded_text[:split_position]
validation_data = encoded_text[split_position:]

print("\nEncoded tensor shape:")
print(encoded_text.shape)

print("\nTraining tokens:")
print(len(training_data))

print("\nValidation tokens:")
print(len(validation_data))

print("\nRound-trip test:")
print(repr(decode(encoded_text[:100].tolist())))