from transformers import AutoTokenizer


model_name = "Qwen/Qwen2.5-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(
    model_name
)

messages = [
    {
        "role": "system",
        "content": (
            "You are a concise programming tutor."
        ),
    },
    {
        "role": "user",
        "content": (
            "What does optimizer.step() do?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "It updates the model's parameters "
            "using their gradients and the "
            "optimizer's update rule."
        ),
    },
]

formatted_text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=False,
)

print("Formatted conversation:")
print(formatted_text)

encoded_conversation = (
    tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        return_dict=True,
        return_tensors="pt",
    )
)

token_ids = encoded_conversation[
    "input_ids"
][0]

print("\nInput shape:")
print(
    encoded_conversation[
        "input_ids"
    ].shape
)

print("\nNumber of tokens:")
print(len(token_ids))

print("\nFirst 30 token IDs:")
print(token_ids[:30].tolist())

prompt_messages = messages[:-1]

encoded_prompt = tokenizer.apply_chat_template(
    prompt_messages,
    tokenize=True,
    add_generation_prompt=True,
    return_dict=True,
    return_tensors="pt",
)

prompt_length = encoded_prompt[
    "input_ids"
].shape[-1]

input_ids = encoded_conversation[
    "input_ids"
]

labels = input_ids.clone()

labels[
    :,
    :prompt_length,
] = -100

number_of_ignored_tokens = (
    labels == -100
).sum().item()

number_of_trained_tokens = (
    labels != -100
).sum().item()

assistant_token_ids = labels[0][
    labels[0] != -100
]

print("\nPrompt tokens ignored:")
print(number_of_ignored_tokens)

print("\nAssistant tokens trained:")
print(number_of_trained_tokens)

print("\nText represented by trained labels:")
print(
    tokenizer.decode(
        assistant_token_ids,
        skip_special_tokens=True,
    )
)