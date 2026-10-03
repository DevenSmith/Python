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

split_position = int(0.9 * len(encoded_text))

training_data = encoded_text[:split_position]
validation_data = encoded_text[split_position:]

print("Complete dataset:")
print(len(encoded_text))

print("\nTraining tokens:")
print(len(training_data))

print("\nValidation tokens:")
print(len(validation_data))

def get_batch(data, batch_size, sequence_length):
    maximum_start = len(data) - sequence_length - 1

    start_positions = torch.randint(
        0,
        maximum_start + 1,
        (batch_size,),
    )

    input_batch = torch.stack([
        data[start : start + sequence_length]
        for start in start_positions
    ])

    target_batch = torch.stack([
        data[start + 1 : start + sequence_length + 1]
        for start in start_positions
    ])

    return input_batch, target_batch


batch_size = 4
sequence_length = 16

input_batch, target_batch = get_batch(
    training_data,
    batch_size,
    sequence_length,
)

print("\nInput batch shape:")
print(input_batch.shape)

print("\nTarget batch shape:")
print(target_batch.shape)

print("\nFirst input sequence:")
print(input_batch[0])

print("\nFirst target sequence:")
print(target_batch[0])

def decode(token_ids):
    return "".join(
        id_to_character[token_id]
        for token_id in token_ids
    )


print("\nDecoded input:")
print(repr(decode(input_batch[0].tolist())))

print("\nDecoded target:")
print(repr(decode(target_batch[0].tolist())))


model = TinyGPT(
    vocabulary_size=vocabulary_size,
    maximum_sequence_length=sequence_length,
    embedding_size=32,
    number_of_heads=4,
    number_of_layers=2,
)

loss_function = nn.CrossEntropyLoss()


def estimate_loss(model, data, number_of_batches=20):
    model.eval()
    losses = []

    with torch.no_grad():
        for _ in range(number_of_batches):
            inputs, targets = get_batch(
                data,
                batch_size,
                sequence_length,
            )

            logits = model(inputs)

            loss = loss_function(
                logits.reshape(-1, vocabulary_size),
                targets.reshape(-1),
            )

            losses.append(loss.item())

    model.train()

    return sum(losses) / len(losses)


initial_training_loss = estimate_loss(
    model,
    training_data,
)

initial_validation_loss = estimate_loss(
    model,
    validation_data,
)

print("\nInitial training loss:")
print(initial_training_loss)

print("\nInitial validation loss:")
print(initial_validation_loss)


optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.003,
)

number_of_steps = 1000
evaluation_interval = 100

for step in range(number_of_steps + 1):
    if step % evaluation_interval == 0:
        training_loss = estimate_loss(
            model,
            training_data,
        )
        validation_loss = estimate_loss(
            model,
            validation_data,
        )

        print(
            f"step={step:4d} "
            f"training_loss={training_loss:.4f} "
            f"validation_loss={validation_loss:.4f}"
        )

    inputs, targets = get_batch(
        training_data,
        batch_size,
        sequence_length,
    )

    logits = model(inputs)

    loss = loss_function(
        logits.reshape(-1, vocabulary_size),
        targets.reshape(-1),
    )

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()