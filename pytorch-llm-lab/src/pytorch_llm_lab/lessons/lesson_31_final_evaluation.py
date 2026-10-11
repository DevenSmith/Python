from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

project_directory = Path(__file__).resolve().parents[3]

original_model_name = "openai-community/gpt2"

fine_tuned_directory = (
    project_directory
    / "checkpoints"
    / "gpt2_shakespeare_finetuned"
)

lora_adapter_directory = (
    project_directory
    / "checkpoints"
    / "gpt2_shakespeare_lora"
)

data_path = (
    project_directory
    / "data"
    / "tiny_shakespeare.txt"
)

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

model_dtype = (
    torch.float16
    if device.type == "cuda"
    else torch.float32
)

tokenizer = AutoTokenizer.from_pretrained(
    fine_tuned_directory
)

original_model = (
    AutoModelForCausalLM.from_pretrained(
        original_model_name,
        dtype=model_dtype,
    ).to(device)
)

fine_tuned_model = (
    AutoModelForCausalLM.from_pretrained(
        fine_tuned_directory,
        dtype=model_dtype,
    ).to(device)
)

lora_base_model = (
    AutoModelForCausalLM.from_pretrained(
        original_model_name,
        dtype=model_dtype,
    ).to(device)
)

lora_model = PeftModel.from_pretrained(
    lora_base_model,
    lora_adapter_directory,
)

original_model.eval()
fine_tuned_model.eval()
lora_model.eval()

print("Device:")
print(device)

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

validation_data = all_token_ids[
    split_position:
]

batch_size = 4
sequence_length = 128
number_of_batches = 20

random_generator = (
    torch.Generator()
    .manual_seed(42)
)

maximum_start = (
    len(validation_data) - sequence_length
)

validation_batches = []

for _ in range(number_of_batches):
    start_positions = torch.randint(
        0,
        maximum_start + 1,
        (batch_size,),
        generator=random_generator,
    )

    input_ids = torch.stack([
        validation_data[
            start : start + sequence_length
        ]
        for start in start_positions
    ])

    validation_batches.append(
        input_ids.to(device)
    )


@torch.no_grad()
def evaluate_model(model):
    model.eval()
    losses = []

    for input_ids in validation_batches:
        output = model(
            input_ids=input_ids,
            labels=input_ids,
        )

        losses.append(
            output.loss.float().item()
        )

    average_loss = (
        sum(losses) / len(losses)
    )

    perplexity = torch.exp(
        torch.tensor(average_loss)
    ).item()

    return average_loss, perplexity


original_loss, original_perplexity = (
    evaluate_model(original_model)
)

fine_tuned_loss, fine_tuned_perplexity = (
    evaluate_model(fine_tuned_model)
)

lora_loss, lora_perplexity = (
    evaluate_model(lora_model)
)

print("\nFinal model comparison:")
print(
    f"{'Model':20s} "
    f"{'Loss':>10s} "
    f"{'Perplexity':>12s}"
)

print(
    f"{'Original GPT-2':20s} "
    f"{original_loss:10.4f} "
    f"{original_perplexity:12.2f}"
)

print(
    f"{'Full fine-tune':20s} "
    f"{fine_tuned_loss:10.4f} "
    f"{fine_tuned_perplexity:12.2f}"
)

print(
    f"{'LoRA':20s} "
    f"{lora_loss:10.4f} "
    f"{lora_perplexity:12.2f}"
)
