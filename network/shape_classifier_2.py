import torch
import torch.nn as nn


class ShapeClassifier_2(nn.Module):
    def __init__(self):
        super().__init__()
        self.relu = nn.ReLU()
        self.linear1 = nn.Linear(1024, 512, bias=False)
        self.bn1 = nn.BatchNorm1d(512)
        self.dp1 = nn.Dropout(p=0.5)
        self.linear2 = nn.Linear(512, 256)
        self.bn2 = nn.BatchNorm1d(256)
        self.dp2 = nn.Dropout(p=0.5)
        self.linear3 = nn.Linear(256, 40)

    def forward(self, x):
        x = x.reshape(x.shape[0], -1)  # bs, 1024
        x = self.relu(self.bn1(self.linear1(x)))
        x = self.dp1(x)
        x = self.relu(self.bn2(self.linear2(x)))
        x = self.dp2(x)
        x = self.linear3(x)
        return x
