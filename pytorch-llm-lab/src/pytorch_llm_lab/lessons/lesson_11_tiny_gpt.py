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


class TinyGPT(nn.Module):
    def __init__(
        self,
        vocabulary_size,
        maximum_sequence_length,
        embedding_size,
        number_of_heads,
        number_of_layers,
    ):
        super().__init__()

        self.maximum_sequence_length = maximum_sequence_length

        self.token_embedding = nn.Embedding(
            vocabulary_size,
            embedding_size,
        )

        self.position_embedding = nn.Embedding(
            maximum_sequence_length,
            embedding_size,
        )

        self.blocks = nn.ModuleList([
            TransformerBlock(
                embedding_size=embedding_size,
                number_of_heads=number_of_heads,
            )
            for _ in range(number_of_layers)
        ])

        self.final_layer_norm = nn.LayerNorm(embedding_size)

        self.output_layer = nn.Linear(
            embedding_size,
            vocabulary_size,
        )

    def forward(self, token_ids):
        sequence_length = token_ids.shape[-1]

        if sequence_length > self.maximum_sequence_length:
            raise ValueError(
                "Sequence is longer than the model's maximum sequence length"
            )

        position_ids = torch.arange(
            sequence_length,
            device=token_ids.device,
        )

        token_vectors = self.token_embedding(token_ids)
        position_vectors = self.position_embedding(position_ids)

        token_vectors = token_vectors + position_vectors

        for block in self.blocks:
            token_vectors = block(token_vectors)

        token_vectors = self.final_layer_norm(token_vectors)
        logits = self.output_layer(token_vectors)

        return logits


def main():
    torch.manual_seed(42)

    vocabulary_size = 8
    maximum_sequence_length = 16
    embedding_size = 8
    number_of_heads = 2
    number_of_layers = 2

    model = TinyGPT(
        vocabulary_size=vocabulary_size,
        maximum_sequence_length=maximum_sequence_length,
        embedding_size=embedding_size,
        number_of_heads=number_of_heads,
        number_of_layers=number_of_layers,
    )

    token_ids = torch.tensor([
        [3, 2, 4, 4, 5],
        [7, 5, 6, 4, 1],
    ])

    logits = model(token_ids)

    number_of_parameters = sum(
        parameter.numel()
        for parameter in model.parameters()
    )

    print("Token ID shape:")
    print(token_ids.shape)

    print("\nLogit shape:")
    print(logits.shape)

    print("\nNumber of trainable parameters:")
    print(number_of_parameters)


if __name__ == "__main__":
    main()