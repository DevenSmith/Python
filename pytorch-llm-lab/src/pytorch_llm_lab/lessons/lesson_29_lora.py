from pathlib import Path

import torch
from peft import (
    LoraConfig,
    TaskType,
    get_peft_model,
)
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

model_name = "openai-community/gpt2"

project_directory = Path(__file__).resolve().parents[3]

data_path = (
    project_directory
    / "data"
    / "tiny_shakespeare.txt"
)

tokenizer = AutoTokenizer.from_pretrained(
    model_name
)

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

base_model = (
    AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float32,
    ).to(device)
)

lora_configuration = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    target_modules=["c_attn"],
    bias="none",
    fan_in_fan_out=True,
)

model = get_peft_model(
    base_model,
    lora_configuration,
)

model.config.use_cache = False

model.print_trainable_parameters()


trainable_parameters = [
    parameter
    for parameter in model.parameters()
    if parameter.requires_grad
]

optimizer = torch.optim.AdamW(
    trainable_parameters,
    lr=0.0002,
    weight_decay=0.01,
)

optimizer_parameter_count = sum(
    parameter.numel()
    for parameter in trainable_parameters
)

print("\nParameters given to optimizer:")
print(f"{optimizer_parameter_count:,}")

text = data_path.read_text(
    encoding="utf-8"
)

all_token_ids = torch.tensor(
    tokenizer.encode(
        text,
        add_special_tokens=False,
        verbose=False,
    ),
    dtype=torch.long,
)

split_position = int(
    0.9 * len(all_token_ids)
)

training_data = all_token_ids[
    :split_position
]

validation_data = all_token_ids[
    split_position:
]

batch_size = 4
sequence_length = 128


def get_batch(data):
    maximum_start = (
        len(data) - sequence_length
    )

    start_positions = torch.randint(
        0,
        maximum_start + 1,
        (batch_size,),
    )

    input_ids = torch.stack([
        data[start : start + sequence_length]
        for start in start_positions
    ]).to(device)

    labels = input_ids.clone()

    return input_ids, labels


use_mixed_precision = device.type == "cuda"

scaler = torch.amp.GradScaler(
    device.type,
    init_scale=256.0,
    enabled=use_mixed_precision,
)


def train_step():
    model.train()

    input_ids, labels = get_batch(
        training_data
    )

    optimizer.zero_grad(
        set_to_none=True
    )

    with torch.autocast(
        device_type=device.type,
        dtype=torch.float16,
        enabled=use_mixed_precision,
    ):
        output = model(
            input_ids=input_ids,
            labels=labels,
        )

        loss = output.loss

    scaler.scale(loss).backward()
    scaler.unscale_(optimizer)

    gradient_norm = (
        torch.nn.utils.clip_grad_norm_(
            trainable_parameters,
            max_norm=1.0,
        )
    )

    scaler.step(optimizer)
    scaler.update()

    return (
        loss.item(),
        gradient_norm.item(),
    )


@torch.no_grad()
def estimate_loss(
    data,
    number_of_batches=10,
):
    model.eval()
    losses = []

    for _ in range(number_of_batches):
        input_ids, labels = get_batch(data)

        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=use_mixed_precision,
        ):
            output = model(
                input_ids=input_ids,
                labels=labels,
            )

        losses.append(
            output.loss.item()
        )

    return sum(losses) / len(losses)


total_steps = 200
evaluation_interval = 50

torch.manual_seed(42)

initial_validation_loss = estimate_loss(
    validation_data
)

print(
    f"\nstep={0:3d} "
    f"validation_loss="
    f"{initial_validation_loss:.4f}"
)

for step in range(1, total_steps + 1):
    training_loss, gradient_norm = train_step()

    if step % evaluation_interval == 0:
        validation_loss = estimate_loss(
            validation_data
        )

        print(
            f"step={step:3d} "
            f"training_loss={training_loss:.4f} "
            f"validation_loss={validation_loss:.4f} "
            f"gradient_norm={gradient_norm:.4f}"
        )

adapter_directory = (
    project_directory
    / "checkpoints"
    / "gpt2_shakespeare_lora"
)

model.config.use_cache = True

model.save_pretrained(
    adapter_directory
)

tokenizer.save_pretrained(
    adapter_directory
)

torch.save(
    {
        "completed_steps": total_steps,
        "optimizer_state": optimizer.state_dict(),
        "scaler_state": scaler.state_dict(),
        "initial_validation_loss": (
            initial_validation_loss
        ),
        "final_validation_loss": validation_loss,
    },
    adapter_directory / "training_state.pt",
)

print("\nSaved LoRA adapter:")
print(adapter_directory)
