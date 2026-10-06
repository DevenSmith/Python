from pathlib import Path

import torch

from pytorch_llm_lab.lessons.lesson_11_tiny_gpt import TinyGPT

project_directory = Path(__file__).resolve().parents[3]
checkpoint_path = (
    project_directory
    / "checkpoints"
    / "tiny_shakespeare_gpt.pt"
)

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

checkpoint = torch.load(
    checkpoint_path,
    map_location=device,
    weights_only=True,
)

configuration = checkpoint["configuration"]
character_to_id = checkpoint["character_to_id"]
id_to_character = checkpoint["id_to_character"]

model = TinyGPT(**configuration).to(device)
model.load_state_dict(checkpoint["model_state"])

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.0003,
)
optimizer.load_state_dict(
    checkpoint["optimizer_state"]
)

completed_step = checkpoint["step"]

print("Loaded checkpoint:")
print(checkpoint_path)

print("\nDevice:")
print(device)

print("\nCompleted step:")
print(completed_step)

print("\nSaved training loss:")
print(checkpoint["training_loss"])

print("\nSaved validation loss:")
print(checkpoint["validation_loss"])

def encode(text):
    return [
        character_to_id[character]
        for character in text
    ]


def decode(token_ids):
    return "".join(
        id_to_character[token_id]
        for token_id in token_ids
    )


@torch.no_grad()
def generate(
    model,
    prompt,
    number_of_new_tokens,
    temperature=0.8,
    top_k=20,
):
    model.eval()

    token_ids = torch.tensor(
        [encode(prompt)],
        dtype=torch.long,
        device=device,
    )

    for _ in range(number_of_new_tokens):
        model_input = token_ids[
            :,
            -model.maximum_sequence_length :,
        ]

        logits = model(model_input)
        next_token_logits = logits[:, -1, :]
        adjusted_logits = next_token_logits / temperature

        if top_k is not None:
            allowed_count = min(
                top_k,
                adjusted_logits.shape[-1],
            )

            top_values, top_indices = torch.topk(
                adjusted_logits,
                k=allowed_count,
                dim=-1,
            )

            filtered_logits = torch.full_like(
                adjusted_logits,
                float("-inf"),
            )

            filtered_logits.scatter_(
                dim=-1,
                index=top_indices,
                src=top_values,
            )

            adjusted_logits = filtered_logits

        probabilities = torch.softmax(
            adjusted_logits,
            dim=-1,
        )

        next_token_id = torch.multinomial(
            probabilities,
            num_samples=1,
        )

        token_ids = torch.cat(
            [token_ids, next_token_id],
            dim=1,
        )

    return decode(
        token_ids[0].cpu().tolist()
    )


torch.manual_seed(42)

generated_text = generate(
    model=model,
    prompt="ROMEO:",
    number_of_new_tokens=500,
    temperature=0.8,
    top_k=20,
)

print("\nGenerated text:")
print(generated_text)


data_path = (
    project_directory
    / "data"
    / "tiny_shakespeare.txt"
)

text = data_path.read_text(encoding="utf-8")

encoded_text = torch.tensor(
    encode(text),
    dtype=torch.long,
)

split_position = int(0.9 * len(encoded_text))

training_data = encoded_text[:split_position]
validation_data = encoded_text[split_position:]

batch_size = 64
sequence_length = configuration[
    "maximum_sequence_length"
]


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


loss_function = torch.nn.CrossEntropyLoss()


def estimate_loss(data, number_of_batches=10):
    model.eval()
    losses = []

    with torch.no_grad():
        for _ in range(number_of_batches):
            inputs, targets = get_batch(data)
            logits = model(inputs)

            loss = loss_function(
                logits.reshape(
                    -1,
                    configuration["vocabulary_size"],
                ),
                targets.reshape(-1),
            )

            losses.append(loss.item())

    model.train()

    return sum(losses) / len(losses)


first_resumed_step = completed_step + 1
final_step = 3000
evaluation_interval = 200

model.train()

for step in range(
    first_resumed_step,
    final_step + 1,
):
    inputs, targets = get_batch(training_data)
    logits = model(inputs)

    loss = loss_function(
        logits.reshape(
            -1,
            configuration["vocabulary_size"],
        ),
        targets.reshape(-1),
    )

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if step % evaluation_interval == 0:
        training_loss = estimate_loss(training_data)
        validation_loss = estimate_loss(validation_data)

        print(
            f"step={step:4d} "
            f"training_loss={training_loss:.4f} "
            f"validation_loss={validation_loss:.4f}"
        )


torch.manual_seed(42)

improved_text = generate(
    model=model,
    prompt="ROMEO:",
    number_of_new_tokens=500,
    temperature=0.8,
    top_k=20,
)

print("\nGenerated text after resumed training:")
print(improved_text)


resumed_checkpoint_path = (
    project_directory
    / "checkpoints"
    / "tiny_shakespeare_gpt_step_3000.pt"
)

resumed_checkpoint = {
    "model_state": model.state_dict(),
    "optimizer_state": optimizer.state_dict(),
    "step": final_step,
    "character_to_id": character_to_id,
    "id_to_character": id_to_character,
    "configuration": configuration,
    "training_loss": training_loss,
    "validation_loss": validation_loss,
}

torch.save(
    resumed_checkpoint,
    resumed_checkpoint_path,
)

print("\nSaved resumed checkpoint:")
print(resumed_checkpoint_path)