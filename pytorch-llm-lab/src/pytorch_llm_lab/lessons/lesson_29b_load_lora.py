from pathlib import Path

import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

project_directory = Path(__file__).resolve().parents[3]

base_model_name = "openai-community/gpt2"

adapter_directory = (
    project_directory
    / "checkpoints"
    / "gpt2_shakespeare_lora"
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
    adapter_directory
)

base_model = (
    AutoModelForCausalLM.from_pretrained(
        base_model_name,
        dtype=model_dtype,
    ).to(device)
)

model = PeftModel.from_pretrained(
    base_model,
    adapter_directory,
)

model.eval()

print("Base model:")
print(base_model_name)

print("\nLoRA adapter:")
print(adapter_directory)


prompt = "ROMEO:\n"

model_inputs = tokenizer(
    prompt,
    return_tensors="pt",
).to(device)

torch.manual_seed(42)

with torch.no_grad():
    generated_token_ids = model.generate(
        **model_inputs,
        max_new_tokens=200,
        do_sample=True,
        temperature=0.8,
        top_k=50,
        pad_token_id=tokenizer.eos_token_id,
    )

generated_text = tokenizer.decode(
    generated_token_ids[0],
    skip_special_tokens=True,
)

print("\nLoRA generation:")
print(generated_text)