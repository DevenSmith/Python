from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

project_directory = Path(__file__).resolve().parents[3]
data_path = (
    project_directory
    / "data"
    / "tiny_shakespeare.txt"
)

model_name = "openai-community/gpt2"

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
    model_name
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype=model_dtype,
).to(device)

model.eval()

text = data_path.read_text(
    encoding="utf-8"
)

sample_text = text[:1000]

model_inputs = tokenizer(
    sample_text,
    return_tensors="pt",
    truncation=True,
    max_length=128,
).to(device)

with torch.no_grad():
    output = model(
        **model_inputs,
        labels=model_inputs["input_ids"],
    )

print("Input shape:")
print(model_inputs["input_ids"].shape)

print("\nLogits shape:")
print(output.logits.shape)

print("\nLoss:")
print(output.loss.item())

perplexity = torch.exp(
    output.loss.float()
)

print("\nPerplexity:")
print(perplexity.item())

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

print("\nComplete dataset tokens:")
print(len(all_token_ids))

print("\nTraining tokens:")
print(len(training_data))

print("\nValidation tokens:")
print(len(validation_data))

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
    ])

    return input_ids.to(device)


@torch.no_grad()
def estimate_loss(
    data,
    number_of_batches=20,
):
    model.eval()
    losses = []

    for _ in range(number_of_batches):
        input_ids = get_batch(data)

        output = model(
            input_ids=input_ids,
            labels=input_ids,
        )

        losses.append(
            output.loss.item()
        )

    return sum(losses) / len(losses)


torch.manual_seed(42)

validation_loss = estimate_loss(
    validation_data
)

validation_perplexity = torch.exp(
    torch.tensor(validation_loss)
).item()

print("\nAverage validation loss:")
print(validation_loss)

print("\nAverage validation perplexity:")
print(validation_perplexity)