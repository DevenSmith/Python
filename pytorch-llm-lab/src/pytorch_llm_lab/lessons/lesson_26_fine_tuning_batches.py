from pathlib import Path
import torch
from transformers import AutoTokenizer


project_directory = Path(__file__).resolve().parents[3]
data_path = (
    project_directory
    / "data"
    / "tiny_shakespeare.txt"
)

model_name = "openai-community/gpt2"

tokenizer = AutoTokenizer.from_pretrained(
    model_name
)

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
    ])

    labels = input_ids.clone()

    return input_ids, labels


torch.manual_seed(42)

input_ids, labels = get_batch(
    training_data
)

print("Input shape:")
print(input_ids.shape)

print("\nLabel shape:")
print(labels.shape)

print("\nFirst input:")
print(
    tokenizer.decode(input_ids[0])
)

print("\nInputs and labels identical:")
print(torch.equal(input_ids, labels))

print("\nFirst ten prediction tasks:")

for position in range(10):
    context_token_id = input_ids[
        0,
        position,
    ].item()

    target_token_id = labels[
        0,
        position + 1,
    ].item()

    context_token = tokenizer.decode(
        [context_token_id]
    )

    target_token = tokenizer.decode(
        [target_token_id]
    )

    print(
        f"{repr(context_token):15s} "
        f"predicts {repr(target_token)}"
    )