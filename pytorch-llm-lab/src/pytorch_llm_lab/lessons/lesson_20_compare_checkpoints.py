from pathlib import Path

import torch

from pytorch_llm_lab.model import TinyGPT

project_directory = Path(__file__).resolve().parents[3]
checkpoint_directory = project_directory / "checkpoints"

step_3000_path = (
    checkpoint_directory
    / "tiny_shakespeare_gpt_step_3000.pt"
)

step_5000_path = (
    checkpoint_directory
    / "tiny_shakespeare_gpt_step_5000.pt"
)

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print("Device:")
print(device)

print("\nFirst checkpoint:")
print(step_3000_path)

print("\nSecond checkpoint:")
print(step_5000_path)


def load_model(checkpoint_path):
    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=True,
    )

    model = TinyGPT(
        **checkpoint["configuration"]
    ).to(device)

    model.load_state_dict(
        checkpoint["model_state"]
    )

    model.eval()

    return model, checkpoint


model_3000, checkpoint_3000 = load_model(
    step_3000_path
)

model_5000, checkpoint_5000 = load_model(
    step_5000_path
)

print("\nLoaded steps:")
print(checkpoint_3000["step"])
print(checkpoint_5000["step"])

character_to_id = checkpoint_5000[
    "character_to_id"
]
id_to_character = checkpoint_5000[
    "id_to_character"
]


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

        adjusted_logits = (
            next_token_logits / temperature
        )

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


prompt = "ROMEO:"
number_of_new_tokens = 500
temperature = 0.8
top_k = 20

torch.manual_seed(42)

text_from_step_3000 = generate(
    model=model_3000,
    prompt=prompt,
    number_of_new_tokens=number_of_new_tokens,
    temperature=temperature,
    top_k=top_k,
)

torch.manual_seed(42)

text_from_step_5000 = generate(
    model=model_5000,
    prompt=prompt,
    number_of_new_tokens=number_of_new_tokens,
    temperature=temperature,
    top_k=top_k,
)

print("\nStep 3000 generation:")
print(text_from_step_3000)

print("\nStep 5000 generation:")
print(text_from_step_5000)
