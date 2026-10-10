"""Inductive CPU GCN: training and validation graphs never share nodes or edges."""
from __future__ import annotations
import numpy as np
import torch
from scipy.spatial import cKDTree
from sklearn.preprocessing import StandardScaler
from torch_geometric.nn import GCNConv
from src.config import Config


def edges(xy: np.ndarray, radius: float) -> torch.Tensor:
    pairs = cKDTree(xy).query_pairs(radius, output_type="ndarray")
    both = np.concatenate([pairs, pairs[:, ::-1]], axis=0)
    return torch.tensor(both.T, dtype=torch.long)


class GCN(torch.nn.Module):
    """Two graph convolutions with a per-node binary logit."""
    def __init__(self, inputs: int, hidden: int):
        super().__init__()
        self.first = GCNConv(inputs, hidden)
        self.last = GCNConv(hidden, 1)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        return self.last(self.first(x, edge_index).relu(), edge_index).squeeze(-1)


class GraphClassifier:
    """A fixed-epoch inductive estimator; no early stopping on outer test labels."""
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.scaler = StandardScaler()

    def fit(self, x: np.ndarray, y: np.ndarray, xy: np.ndarray) -> GraphClassifier:
        torch.manual_seed(self.cfg["seed"])
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        m = self.cfg["model"]
        self.net = GCN(x.shape[1], m["graph_hidden_channels"])
        values = torch.tensor(self.scaler.fit_transform(x), dtype=torch.float32)
        edge = edges(xy, m["graph_radius_m"])
        target = torch.tensor(y, dtype=torch.float32)
        weight = torch.tensor(float((y == 0).sum() / (y == 1).sum()))
        criterion = torch.nn.BCEWithLogitsLoss(pos_weight=weight)
        optimizer = torch.optim.Adam(self.net.parameters(), lr=m["graph_learning_rate"],
                                     weight_decay=m["graph_weight_decay"])
        self.net.train()
        for _ in range(m["graph_epochs"]):
            optimizer.zero_grad()
            loss = criterion(self.net(values, edge), target)
            loss.backward()
            optimizer.step()
        self.net.eval()
        return self

    def predict_proba(self, x: np.ndarray, xy: np.ndarray) -> np.ndarray:
        values = torch.tensor(self.scaler.transform(x), dtype=torch.float32)
        with torch.no_grad():
            p = self.net(values, edges(xy, self.cfg["model"]["graph_radius_m"])).sigmoid().numpy()
        return np.column_stack([1 - p, p])
