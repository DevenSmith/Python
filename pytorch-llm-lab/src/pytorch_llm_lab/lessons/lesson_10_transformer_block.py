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


class MultiHeadCausalSelfAttention(nn.Module):
    def __init__(self, embedding_size, number_of_heads):
        super().__init__()

        if embedding_size % number_of_heads != 0:
            raise ValueError(
                "embedding_size must be divisible by number_of_heads"
            )

        head_size = embedding_size // number_of_heads

        self.heads = nn.ModuleList([
            CausalSelfAttention(
                embedding_size=embedding_size,
                head_size=head_size,
            )
            for _ in range(number_of_heads)
        ])

        self.output_projection = nn.Linear(
            embedding_size,
            embedding_size,
        )

    def forward(self, token_vectors):
        head_outputs = []

        for head in self.heads:
            context_vectors, _ = head(token_vectors)
            head_outputs.append(context_vectors)

        combined_output = torch.cat(head_outputs, dim=-1)
        output = self.output_projection(combined_output)

        return output


class FeedForward(nn.Module):
    def __init__(self, embedding_size):
        super().__init__()

        hidden_size = 4 * embedding_size

        self.network = nn.Sequential(
            nn.Linear(embedding_size, hidden_size),
            nn.GELU(),
            nn.Linear(hidden_size, embedding_size),
        )

    def forward(self, token_vectors):
        return self.network(token_vectors)
    

class TransformerBlock(nn.Module):
    def __init__(self, embedding_size, number_of_heads):
        super().__init__()

        self.layer_norm_1 = nn.LayerNorm(embedding_size)

        self.attention = MultiHeadCausalSelfAttention(
            embedding_size=embedding_size,
            number_of_heads=number_of_heads,
        )

        self.layer_norm_2 = nn.LayerNorm(embedding_size)
        self.feed_forward = FeedForward(embedding_size)

    def forward(self, token_vectors):
        normalized_vectors = self.layer_norm_1(token_vectors)
        attention_output = self.attention(normalized_vectors)
        token_vectors = token_vectors + attention_output

        normalized_vectors = self.layer_norm_2(token_vectors)
        feed_forward_output = self.feed_forward(normalized_vectors)
        token_vectors = token_vectors + feed_forward_output

        return token_vectors


torch.manual_seed(42)

batch_size = 2
sequence_length = 5
embedding_size = 8
number_of_heads = 2

token_vectors = torch.randn(
    batch_size,
    sequence_length,
    embedding_size,
)

transformer_block = TransformerBlock(
    embedding_size=embedding_size,
    number_of_heads=number_of_heads,
)

output = transformer_block(token_vectors)

print("Input shape:")
print(token_vectors.shape)

print("\nOutput shape:")
print(output.shape)

print("\nInput and output values identical:")
print(torch.allclose(token_vectors, output))