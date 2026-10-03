from pathlib import Path

import torch

from pytorch_llm_lab.lessons.lesson_11_tiny_gpt import TinyGPT


project_directory = Path(__file__).resolve().parents[3]
checkpoint_path = project_directory / "checkpoints" / "tiny_gpt.pt"

checkpoint = torch.load(
    checkpoint_path,
    map_location="cpu",
    weights_only=True,
)

configuration = checkpoint["configuration"]
character_to_id = checkpoint["character_to_id"]
id_to_character = checkpoint["id_to_character"]

model = TinyGPT(**configuration)
model.load_state_dict(checkpoint["model_state"])
model.eval()

print("Loaded checkpoint:")
print(checkpoint_path)

print("\nModel configuration:")
print(configuration)


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
    temperature=1.0,
    top_k=None,
):
    token_ids = torch.tensor(
        [encode(prompt)],
        dtype=torch.long,
    )

    if temperature <= 0:
        raise ValueError("temperature must be greater than zero")

    for _ in range(number_of_new_tokens):
        model_input = token_ids[
            :,
            -model.maximum_sequence_length :,
        ]

        logits = model(model_input)

        next_token_logits = logits[:, -1, :]

        adjusted_logits = next_token_logits / temperature

        if top_k is not None:
            top_k = min(
                top_k,
                adjusted_logits.shape[-1],
            )

            top_values, top_indices = torch.topk(
                adjusted_logits,
                k=top_k,
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

    return decode(token_ids[0].tolist())


for temperature in [1.0, 2.0, 5.0]:
    generated_text = generate(
        model=model,
        prompt="hell",
        number_of_new_tokens=50,
        temperature=temperature,
        top_k=3,
    )

    print(
        f"\nTemperature {temperature}, top-k 3:"
    )
    print(repr(generated_text))