from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

project_directory = Path(__file__).resolve().parents[3]

original_model_name = "openai-community/gpt2"

fine_tuned_directory = (
    project_directory
    / "checkpoints"
    / "gpt2_shakespeare_finetuned"
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

original_model.eval()
fine_tuned_model.eval()

print("Device:")
print(device)

print("\nOriginal model:")
print(original_model_name)

print("\nFine-tuned model:")
print(fine_tuned_directory)

print("\nOriginal parameter count:")
print(
    f"{sum(parameter.numel() for parameter in original_model.parameters()):,}"
)

print("\nFine-tuned parameter count:")
print(
    f"{sum(parameter.numel() for parameter in fine_tuned_model.parameters()):,}"
)

data_path = (
    project_directory
    / "data"
    / "tiny_shakespeare.txt"
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

print("\nOriginal validation loss:")
print(original_loss)

print("\nFine-tuned validation loss:")
print(fine_tuned_loss)

print("\nOriginal perplexity:")
print(original_perplexity)

print("\nFine-tuned perplexity:")
print(fine_tuned_perplexity)

@torch.no_grad()
def generate_text(
    model,
    prompt,
    number_of_new_tokens=200,
):
    model.eval()

    model_inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to(device)

    generated_token_ids = model.generate(
        **model_inputs,
        max_new_tokens=number_of_new_tokens,
        do_sample=True,
        temperature=0.8,
        top_k=50,
        pad_token_id=tokenizer.eos_token_id,
    )

    return tokenizer.decode(
        generated_token_ids[0],
        skip_special_tokens=True,
    )

prompt = "ROMEO:\n"

torch.manual_seed(42)

original_text = generate_text(
    original_model,
    prompt,
)

torch.manual_seed(42)

fine_tuned_text = generate_text(
    fine_tuned_model,
    prompt,
)

print("\nOriginal GPT-2 generation:")
print(original_text)

print("\nFine-tuned GPT-2 generation:")
print(fine_tuned_text)