import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
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

number_of_parameters = sum(
    parameter.numel()
    for parameter in model.parameters()
)

print("Device:")
print(device)

print("\nModel data type:")
print(model.dtype)

print("\nNumber of parameters:")
print(f"{number_of_parameters:,}")


prompt = (
    "Artificial intelligence will change the world by"
)

model_inputs = tokenizer(
    prompt,
    return_tensors="pt",
).to(device)

print("\nModel inputs:")
print(model_inputs)

print("\nInput shape:")
print(model_inputs["input_ids"].shape)

torch.manual_seed(42)

with torch.no_grad():
    generated_token_ids = model.generate(
        **model_inputs,
        max_new_tokens=80,
        do_sample=True,
        temperature=0.8,
        top_k=50,
        pad_token_id=tokenizer.eos_token_id,
    )

generated_text = tokenizer.decode(
    generated_token_ids[0],
    skip_special_tokens=True,
)

print("\nGenerated text:")
print(generated_text)