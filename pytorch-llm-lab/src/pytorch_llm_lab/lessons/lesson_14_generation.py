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
def generate(model, prompt, number_of_new_tokens):
    token_ids = torch.tensor(
        [encode(prompt)],
        dtype=torch.long,
    )

    for _ in range(number_of_new_tokens):
        model_input = token_ids[
            :,
            -model.maximum_sequence_length :,
        ]

        logits = model(model_input)

        next_token_logits = logits[:, -1, :]

        next_token_id = next_token_logits.argmax(
            dim=-1,
            keepdim=True,
        )

        token_ids = torch.cat(
            [token_ids, next_token_id],
            dim=1,
        )

    return decode(token_ids[0].tolist())


generated_text = generate(
    model=model,
    prompt="hell",
    number_of_new_tokens=50,
)

print("\nGenerated text:")
print(repr(generated_text))