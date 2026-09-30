import torch
from torch import nn


class CausalSelfAttention(nn.Module):
    def __init__(self, embedding_size, head_size):
        super().__init__()

        self.query_layer = nn.Linear(
            embedding_size,
            head_size,
            bias=False,
        )
        self.key_layer = nn.Linear(
            embedding_size,
            head_size,
            bias=False,
        )
        self.value_layer = nn.Linear(
            embedding_size,
            head_size,
            bias=False,
        )

    def forward(self, token_vectors):
        queries = self.query_layer(token_vectors)
        keys = self.key_layer(token_vectors)
        values = self.value_layer(token_vectors)

        key_size = keys.shape[-1]
        attention_scores = (
            queries @ keys.transpose(-2, -1)
        ) / (key_size ** 0.5)

        sequence_length = token_vectors.shape[-2]
        future_mask = torch.triu(
            torch.ones(
                sequence_length,
                sequence_length,
                dtype=torch.bool,
                device=token_vectors.device,
            ),
            diagonal=1,
        )

        masked_scores = attention_scores.masked_fill(
            future_mask,
            float("-inf"),
        )

        attention_weights = torch.softmax(masked_scores, dim=-1)
        context_vectors = attention_weights @ values

        return context_vectors, attention_weights

torch.manual_seed(42)

token_vectors = torch.tensor([
    [1.0, 0.0],
    [0.8, 0.2],
    [0.0, 1.0],
])

attention = CausalSelfAttention(
    embedding_size=2,
    head_size=2,
)

batched_token_vectors = torch.stack([
    token_vectors,
    token_vectors,
])

context_vectors, attention_weights = attention(batched_token_vectors)

print("Input shape:")
print(batched_token_vectors.shape)

print("\nAttention weights shape:")
print(attention_weights.shape)

print("\nContext vectors shape:")
print(context_vectors.shape)