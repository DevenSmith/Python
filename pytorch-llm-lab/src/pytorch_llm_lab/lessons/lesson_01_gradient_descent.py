"""Lesson 1: learn a straight line with tensors and automatic differentiation."""

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class TrainingResult:
    weight: float
    bias: float
    final_loss: float


def train(steps: int = 500, learning_rate: float = 0.05) -> TrainingResult:
    """Fit y = weight * x + bias to four examples using gradient descent."""
    torch.manual_seed(42)

    x = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
    targets = torch.tensor([[3.0], [5.0], [7.0], [9.0]])

    weight = torch.randn(1, requires_grad=True)
    bias = torch.zeros(1, requires_grad=True)

    for step in range(steps):
        predictions = x * weight + bias
        loss = ((predictions - targets) ** 2).mean()
        loss.backward()

        if step % 50 == 0:
            print(
                f"step={step:3d} "
                f"loss={loss.item():.6f} "
                f"weight={weight.item():.4f} "
                f"bias={bias.item():.4f}"
            )                    

        # Parameter updates are bookkeeping, not part of the model calculation.
        with torch.no_grad():
            weight -= learning_rate * weight.grad
            bias -= learning_rate * bias.grad
            weight.grad.zero_()
            bias.grad.zero_()

    final_predictions = x * weight + bias
    final_loss = ((final_predictions - targets) ** 2).mean()
    return TrainingResult(weight.item(), bias.item(), final_loss.item())


def main() -> None:
    result = train()
    prediction = 10 * result.weight + result.bias

    print(f"Learned weight: {result.weight:.4f}")
    print(f"Learned bias: {result.bias:.4f}")
    print(f"Final loss: {result.final_loss:.8f}")
    print(f"Prediction for x=10: {prediction:.4f}")


if __name__ == "__main__":
    main()

