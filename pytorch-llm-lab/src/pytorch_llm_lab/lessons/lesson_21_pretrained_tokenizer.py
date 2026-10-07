from transformers import AutoTokenizer


model_name = "openai-community/gpt2"

tokenizer = AutoTokenizer.from_pretrained(
    model_name
)

text = "PyTorch makes learning transformers interesting."

token_ids = tokenizer.encode(text)

print("Original text:")
print(text)

print("\nToken IDs:")
print(token_ids)

print("\nTokens:")
print(
    tokenizer.convert_ids_to_tokens(token_ids)
)

print("\nDecoded text:")
print(tokenizer.decode(token_ids))

print("\nVocabulary size:")
print(tokenizer.vocab_size)