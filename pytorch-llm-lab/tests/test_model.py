import pytest
import torch

from pytorch_llm_lab.model import CausalSelfAttention, TinyGPT


def test_tiny_gpt_preserves_batch_and_sequence_dimensions() -> None:
    model = TinyGPT(
        vocabulary_size=9,
        maximum_sequence_length=5,
        embedding_size=8,
        number_of_heads=2,
        number_of_layers=2,
    )
    token_ids = torch.randint(0, 9, (2, 5))

    logits = model(token_ids)

    assert logits.shape == (2, 5, 9)


def test_tiny_gpt_rejects_sequences_longer_than_its_context() -> None:
    model = TinyGPT(
        vocabulary_size=9,
        maximum_sequence_length=5,
        embedding_size=8,
        number_of_heads=2,
        number_of_layers=1,
    )

    with pytest.raises(ValueError, match="maximum sequence length"):
        model(torch.randint(0, 9, (1, 6)))


def test_causal_attention_hides_future_tokens() -> None:
    torch.manual_seed(42)
    attention = CausalSelfAttention(embedding_size=4, head_size=2)
    token_vectors = torch.randn(1, 3, 4)
    changed_future = token_vectors.clone()
    changed_future[:, 2] = 1000.0

    original_context, _ = attention(token_vectors)
    changed_context, _ = attention(changed_future)

    assert torch.allclose(
        original_context[:, :2],
        changed_context[:, :2],
        atol=1e-6,
    )
