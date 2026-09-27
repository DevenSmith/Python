import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class LineModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(in_features=1, out_features=1)

    def forward(self, x):
        return self.linear(x)


torch.manual_seed(42)

x = torch.tensor([[1.0], [2.0], [3.0], [4.0]])
targets = torch.tensor([[3.0], [5.0], [7.0], [9.0]])

dataset = TensorDataset(x, targets)
data_loader = DataLoader(dataset, batch_size=2, shuffle=True)

model = LineModel()

loss_function = nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=0.05)

for epoch in range(250):
    epoch_loss = 0.0

    for batch_x, batch_targets in data_loader:
        predictions = model(batch_x)
        loss = loss_function(predictions, batch_targets)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()

    average_loss = epoch_loss / len(data_loader)

    if epoch % 25 == 0:
        print(
            f"epoch={epoch:3d} "
            f"loss={average_loss:.6f} "
            f"weight={model.linear.weight.item():.4f} "
            f"bias={model.linear.bias.item():.4f}"
        )