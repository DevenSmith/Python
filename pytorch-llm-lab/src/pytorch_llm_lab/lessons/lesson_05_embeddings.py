import torch
from torch import nn


torch.manual_seed(42)

vocabulary_size = 8
embedding_size = 3

embedding = nn.Embedding(
    num_embeddings=vocabulary_size,
    embedding_dim=embedding_size,
)

print(embedding.weight)
print(embedding.weight.shape)

token_ids = torch.tensor([3, 2, 4, 4, 5])

embedded_tokens = embedding(token_ids)

print(embedded_tokens)
print(embedded_tokens.shape)

maximum_sequence_length = 5

position_embedding = nn.Embedding(
    num_embeddings=maximum_sequence_length,
    embedding_dim=embedding_size,
)

position_ids = torch.arange(len(token_ids))
position_vectors = position_embedding(position_ids)

model_inputs = embedded_tokens + position_vectors

print("position IDs:", position_ids)
print("position shape:", position_vectors.shape)
print("model input shape:", model_inputs.shape)
print(model_inputs)