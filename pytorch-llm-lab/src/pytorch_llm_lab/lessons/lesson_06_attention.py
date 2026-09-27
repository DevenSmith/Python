import torch


token_vectors = torch.tensor([
    [1.0, 0.0],
    [0.8, 0.2],
    [0.0, 1.0],
])

attention_scores = token_vectors @ token_vectors.T

print("Token vectors:")
print(token_vectors)

print("\nAttention scores:")
print(attention_scores)

future_mask = torch.triu(
    torch.ones_like(attention_scores, dtype=torch.bool),
    diagonal=1,
)

masked_scores = attention_scores.masked_fill(
    future_mask,
    float("-inf"),
)

print("\nFuture mask:")
print(future_mask)

print("\nMasked scores:")
print(masked_scores)

attention_weights = torch.softmax(masked_scores, dim=-1)

print("\nAttention weights:")
print(attention_weights)

print("\nRow totals:")
print(attention_weights.sum(dim=-1))

context_vectors = attention_weights @ token_vectors

print("\nContext vectors:")
print(context_vectors)