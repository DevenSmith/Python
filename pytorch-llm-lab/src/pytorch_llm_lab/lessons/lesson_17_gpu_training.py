from pathlib import Path

import torch
from pytorch_llm_lab.lessons.lesson_11_tiny_gpt import TinyGPT


project_directory = Path(__file__).resolve().parents[3]
data_path = project_directory / "data" / "tiny_shakespeare.txt"

text = data_path.read_text(encoding="utf-8")

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

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print("Training device:")
print(device)

if device.type == "cuda":
    print("\nGPU:")
    print(torch.cuda.get_device_name(0))

batch_size = 64
sequence_length = 128

def get_batch(data):
    maximum_start = len(data) - sequence_length - 1

    start_positions = torch.randint(
        0,
        maximum_start + 1,
        (batch_size,),
    )

    inputs = torch.stack([
        data[start : start + sequence_length]
        for start in start_positions
    ])

    targets = torch.stack([
        data[start + 1 : start + sequence_length + 1]
        for start in start_positions
    ])

    return inputs.to(device), targets.to(device)

input_batch, target_batch = get_batch(training_data)

print("\nInput batch:")
print(input_batch.shape)
print(input_batch.device)

print("\nTarget batch:")
print(target_batch.shape)
print(target_batch.device)

model = TinyGPT(
    vocabulary_size=vocabulary_size,
    maximum_sequence_length=sequence_length,
    embedding_size=128,
    number_of_heads=4,
    number_of_layers=4,
).to(device)

loss_function = torch.nn.CrossEntropyLoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.0003,
)

number_of_parameters = sum(
    parameter.numel()
    for parameter in model.parameters()
)

print("\nModel device:")
print(next(model.parameters()).device)

print("\nTrainable parameters:")
print(f"{number_of_parameters:,}")

logits = model(input_batch)

loss = loss_function(
    logits.reshape(-1, vocabulary_size),
    target_batch.reshape(-1),
)

optimizer.zero_grad()
loss.backward()
optimizer.step()

print("\nLogit shape:")
print(logits.shape)

print("\nFirst GPU training loss:")
print(loss.item())

def estimate_loss(data, number_of_batches=10):
    model.eval()
    losses = []

    with torch.no_grad():
        for _ in range(number_of_batches):
            inputs, targets = get_batch(data)
            logits = model(inputs)

            loss = loss_function(
                logits.reshape(-1, vocabulary_size),
                targets.reshape(-1),
            )

            losses.append(loss.item())

    model.train()

    return sum(losses) / len(losses)

number_of_steps = 1000
evaluation_interval = 100

for step in range(number_of_steps + 1):
    if step % evaluation_interval == 0:
        training_loss = estimate_loss(training_data)
        validation_loss = estimate_loss(validation_data)

        print(
            f"step={step:4d} "
            f"training_loss={training_loss:.4f} "
            f"validation_loss={validation_loss:.4f}"
        )

    inputs, targets = get_batch(training_data)

    logits = model(inputs)

    loss = loss_function(
        logits.reshape(-1, vocabulary_size),
        targets.reshape(-1),
    )

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    checkpoint_directory = (
    project_directory / "checkpoints"
)
checkpoint_directory.mkdir(exist_ok=True)

checkpoint_path = (
    checkpoint_directory / "tiny_shakespeare_gpt.pt"
)

checkpoint = {
    "model_state": model.state_dict(),
    "optimizer_state": optimizer.state_dict(),
    "step": number_of_steps,
    "character_to_id": character_to_id,
    "id_to_character": id_to_character,
    "configuration": {
        "vocabulary_size": vocabulary_size,
        "maximum_sequence_length": sequence_length,
        "embedding_size": 128,
        "number_of_heads": 4,
        "number_of_layers": 4,
    },
    "training_loss": training_loss,
    "validation_loss": validation_loss,
}

torch.save(checkpoint, checkpoint_path)

print("\nSaved checkpoint:")
print(checkpoint_path)