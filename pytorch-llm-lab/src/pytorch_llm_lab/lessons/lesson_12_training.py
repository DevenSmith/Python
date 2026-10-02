import torch
from torch import nn

from pytorch_llm_lab.lessons.lesson_11_tiny_gpt import TinyGPT


torch.manual_seed(42)

text = "hello world\n" * 100

characters = sorted(set(text))
vocabulary_size = len(characters)

character_to_id = {
    character: index
    for index, character in enumerate(characters)
}

id_to_character = {
    index: character
    for character, index in character_to_id.items()
}

encoded_text = torch.tensor(
    [
        character_to_id[character]
        for character in text
    ],
    dtype=torch.long,
)

print("Vocabulary:")
print(character_to_id)

print("\nNumber of characters:")
print(len(encoded_text))

sequence_length = 16

input_ids = encoded_text[:sequence_length].unsqueeze(0)
target_ids = encoded_text[1 : sequence_length + 1].unsqueeze(0)


def decode(token_ids):
    return "".join(
        id_to_character[token_id]
        for token_id in token_ids
    )


print("\nInput shape:")
print(input_ids.shape)

print("\nTarget shape:")
print(target_ids.shape)

print("\nInput text:")
print(repr(decode(input_ids[0].tolist())))

print("\nTarget text:")
print(repr(decode(target_ids[0].tolist())))

model = TinyGPT(
    vocabulary_size=vocabulary_size,
    maximum_sequence_length=sequence_length,
    embedding_size=32,
    number_of_heads=4,
    number_of_layers=2,
)

logits = model(input_ids)

loss_function = nn.CrossEntropyLoss()

flattened_logits = logits.reshape(
    -1,
    vocabulary_size,
)
flattened_targets = target_ids.reshape(-1)

loss = loss_function(
    flattened_logits,
    flattened_targets,
)

print("\nOriginal logits shape:")
print(logits.shape)

print("\nFlattened logits shape:")
print(flattened_logits.shape)

print("\nFlattened target shape:")
print(flattened_targets.shape)

print("\nInitial loss:")
print(loss.item())

predicted_ids = logits.argmax(dim=-1)

predicted_text = decode(
    predicted_ids[0].tolist()
)

print("\nPredicted next characters:")
print(repr(predicted_text))

print("\nCorrect next characters:")
print(repr(decode(target_ids[0].tolist())))

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.003,
)

for step in range(500):
    logits = model(input_ids)

    loss = loss_function(
        logits.reshape(-1, vocabulary_size),
        target_ids.reshape(-1),
    )

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if step % 50 == 0:
        print(
            f"step={step:3d} "
            f"loss={loss.item():.6f}"
        )

with torch.no_grad():
    final_logits = model(input_ids)
    final_predictions = final_logits.argmax(dim=-1)

print("\nPrediction after training:")
print(repr(decode(final_predictions[0].tolist())))

print("\nTarget:")
print(repr(decode(target_ids[0].tolist())))