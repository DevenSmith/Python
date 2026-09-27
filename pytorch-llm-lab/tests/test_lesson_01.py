import pytest

from pytorch_llm_lab.lessons.lesson_01_gradient_descent import train


def test_gradient_descent_learns_the_line() -> None:
    result = train()

    assert result.weight == pytest.approx(2.0, abs=0.01)
    assert result.bias == pytest.approx(1.0, abs=0.03)
    assert result.final_loss < 0.001

