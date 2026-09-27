import torch
from torch import nn


class LineModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(in_features=1, out_features=1)

    def forward(self, x):
        return self.linear(x)


torch.manual_seed(42)

x = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
targets = torch.tensor([[3.0], [5.0], [7.0], [9.0]])

model = LineModel()

loss_function = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=0.05)

for step in range(500):
    predictions = model(x)
    loss = loss_function(predictions, targets)

    if step % 50 == 0:
        print(
            f"step={step:3d} "
            f"loss={loss.item():.6f} "
            f"weight={model.linear.weight.item():.4f} "
            f"bias={model.linear.bias.item():.4f}"
        )

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()