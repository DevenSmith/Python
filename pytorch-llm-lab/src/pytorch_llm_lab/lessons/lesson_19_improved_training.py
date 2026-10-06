from pathlib import Path

import torch

from pytorch_llm_lab.model import TinyGPT

project_directory = Path(__file__).resolve().parents[3]
checkpoint_path = (
    project_directory
    / "checkpoints"
    / "tiny_shakespeare_gpt_step_3000.pt"
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

model = TinyGPT(
    **configuration,
    dropout_rate=0.1,
).to(device)

model.load_state_dict(
    checkpoint["model_state"]
)

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.0003,
)

optimizer.load_state_dict(
    checkpoint["optimizer_state"]
)

completed_step = checkpoint["step"]

print("Device:")
print(device)

print("\nLoaded step:")
print(completed_step)

print("\nDropout rate:")
print(model.blocks[0].dropout.p)


def encode(text):
    return [
        character_to_id[character]
        for character in text
    ]


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
vocabulary_size = configuration[
    "vocabulary_size"
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

additional_steps = 2000

scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer,
    T_max=additional_steps,
    eta_min=0.00003,
)

use_mixed_precision = device.type == "cuda"

scaler = torch.amp.GradScaler(
    device.type,
    enabled=use_mixed_precision,
)


def train_step():
    model.train()
    inputs, targets = get_batch(training_data)
    optimizer.zero_grad(set_to_none=True)

    with torch.autocast(
        device_type=device.type,
        dtype=torch.float16,
        enabled=use_mixed_precision,
    ):
        logits = model(inputs)

        loss = loss_function(
            logits.reshape(-1, vocabulary_size),
            targets.reshape(-1),
        )

    scaler.scale(loss).backward()

    scaler.unscale_(optimizer)

    gradient_norm = torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        max_norm=1.0,
    )

    scaler.step(optimizer)
    scaler.update()

    scheduler.step()

    current_learning_rate = optimizer.param_groups[0]["lr"]

    return (
        loss.item(),
        gradient_norm.item(),
        current_learning_rate,
    )


@torch.no_grad()
def estimate_loss(data, number_of_batches=20):
    model.eval()
    losses = []

    for _ in range(number_of_batches):
        inputs, targets = get_batch(data)

        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=use_mixed_precision,
        ):
            logits = model(inputs)

            loss = loss_function(
                logits.reshape(-1, vocabulary_size),
                targets.reshape(-1),
            )

        losses.append(loss.item())

    return sum(losses) / len(losses)


first_step = completed_step + 1
final_step = completed_step + additional_steps
evaluation_interval = 200

for step in range(first_step, final_step + 1):
    batch_loss, gradient_norm, learning_rate = train_step()

    if step % evaluation_interval == 0:
        training_loss = estimate_loss(training_data)
        validation_loss = estimate_loss(validation_data)

        print(
            f"step={step:4d} "
            f"training_loss={training_loss:.4f} "
            f"validation_loss={validation_loss:.4f} "
            f"gradient_norm={gradient_norm:.4f} "
            f"learning_rate={learning_rate:.8f}"
        )

output_checkpoint_path = (
    project_directory
    / "checkpoints"
    / "tiny_shakespeare_gpt_step_5000.pt"
)

improved_configuration = {
    **configuration,
    "dropout_rate": 0.1,
}

torch.save(
    {
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "scheduler_state": scheduler.state_dict(),
        "scaler_state": scaler.state_dict(),
        "step": final_step,
        "configuration": improved_configuration,
        "character_to_id": character_to_id,
        "id_to_character": id_to_character,
        "training_loss": training_loss,
        "validation_loss": validation_loss,
    },
    output_checkpoint_path,
)

print("\nSaved improved checkpoint:")
print(output_checkpoint_path)