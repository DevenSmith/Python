import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

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

prompt = "The capital of France is"

model_inputs = tokenizer(
    prompt,
    return_tensors="pt",
).to(device)

with torch.no_grad():
    output = model(**model_inputs)

logits = output.logits

print("Input IDs shape:")
print(model_inputs["input_ids"].shape)

print("\nLogits shape:")
print(logits.shape)

next_token_logits = logits[0, -1, :]

probabilities = torch.softmax(
    next_token_logits.float(),
    dim=-1,
)

top_probabilities, top_token_ids = torch.topk(
    probabilities,
    k=10,
)

print("\nMost likely next tokens:")

for probability, token_id in zip(
    top_probabilities,
    top_token_ids,
):
    token_text = tokenizer.decode(
        [token_id.item()]
    )

    print(
        f"{repr(token_text):20s} "
        f"{probability.item():.4%}"
    )


with torch.no_grad():
    generated_token_ids = model.generate(
        **model_inputs,
        max_new_tokens=12,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )

generated_text = tokenizer.decode(
    generated_token_ids[0],
    skip_special_tokens=True,
)

print("\nGreedy continuation:")
print(generated_text)