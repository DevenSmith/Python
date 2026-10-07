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

tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    dtype=model_dtype,
).to(device)

model.eval()

prompts = [
    "The dog",
    "Machine learning can",
    "In the distant future, humanity",
]

model_inputs = tokenizer(
    prompts,
    return_tensors="pt",
    padding=True,
).to(device)

print("Input IDs:")
print(model_inputs["input_ids"])

print("\nInput shape:")
print(model_inputs["input_ids"].shape)

print("\nAttention masks:")
print(model_inputs["attention_mask"])

for index, token_ids in enumerate(
    model_inputs["input_ids"]
):
    print(f"\nPrompt {index}:")
    print(tokenizer.decode(token_ids))

torch.manual_seed(42)

with torch.no_grad():
    generated_token_ids = model.generate(
        **model_inputs,
        max_new_tokens=40,
        do_sample=True,
        temperature=0.8,
        top_k=50,
        pad_token_id=tokenizer.pad_token_id,
    )

generated_texts = tokenizer.batch_decode(
    generated_token_ids,
    skip_special_tokens=True,
)

print("\nGenerated text:")

for index, generated_text in enumerate(
    generated_texts
):
    print(f"\nResult {index}:")
    print(generated_text)
