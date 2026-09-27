import torch


text = "hello world"

characters = sorted(set(text))

print(characters)
print(len(characters))

character_to_id = {
    character: index
    for index, character in enumerate(characters)
}

print(character_to_id)

def encode(text_to_encode):
    return [
        character_to_id[character]
        for character in text_to_encode
    ]


encoded_text = encode(text)
print(encoded_text)

token_ids = torch.tensor(encoded_text, dtype=torch.long)

print(token_ids)
print(token_ids.shape)

id_to_character = {
    index: character
    for character, index in character_to_id.items()
}


def decode(token_ids):
    return "".join(
        id_to_character[token_id]
        for token_id in token_ids
    )


decoded_text = decode(encoded_text)
print(decoded_text)

input_tokens = token_ids[:-1]
target_tokens = token_ids[1:]

print("inputs: ", input_tokens)
print("targets:", target_tokens)

for position, target_id in enumerate(target_tokens):
    context_ids = input_tokens[: position + 1]
    context = decode(context_ids.tolist())
    target = decode([target_id.item()])

    print(f"When the context is {context!r}, predict {target!r}")