"""Held-out permutation importance plus optional SHAP and Captum adapters."""
from __future__ import annotations
from typing import Any
import numpy as np
from sklearn.metrics import average_precision_score
from src.config import Config
from src.models.estimators import predict


def permutation_importance(model: Any, x: np.ndarray, y: np.ndarray,
                           xy: np.ndarray, cfg: Config) -> dict[str, float]:
    """AP degradation on held-out data; negative values are retained."""
    rng = np.random.default_rng(cfg["seed"])
    baseline = average_precision_score(y, predict(model, x, xy, cfg))
    result = {}
    for j, name in enumerate(cfg["features"]["columns"]):
        scores = []
        for _ in range(cfg["explanations"]["permutation_repeats"]):
            changed = x.copy()
            changed[:, j] = rng.permutation(changed[:, j])
            scores.append(baseline - average_precision_score(y, predict(model, changed, xy, cfg)))
        result[name] = float(np.mean(scores))
    return result


def tree_shap(model: Any, x: np.ndarray, cfg: Config) -> Any:
    """Raw-margin SHAP values for a fitted tree model; x must have training feature order."""
    import shap
    return shap.TreeExplainer(model)(x[:cfg["explanations"]["shap_max_cells"]])


def graph_integrated_gradients(model: Any, x: np.ndarray, xy: np.ndarray,
                               node_index: int) -> tuple[np.ndarray, float]:
    """Attribute one node's logit to all graph-node features relative to training means.

    Attribution shape is [nodes, features], including neighbor contributions.
    The convergence delta checks numerical integration, not causal validity.
    """
    import torch
    from captum.attr import IntegratedGradients
    from src.models.graph import edges
    values = torch.tensor(model.scaler.transform(x), dtype=torch.float32).unsqueeze(0)
    edge = edges(xy, model.cfg["model"]["graph_radius_m"])
    def forward(batch: torch.Tensor) -> torch.Tensor:
        return torch.stack([model.net(item, edge)[node_index] for item in batch])
    attribution, delta = IntegratedGradients(forward).attribute(
        values, baselines=torch.zeros_like(values),
        n_steps=model.cfg["explanations"]["integrated_gradients_steps"], return_convergence_delta=True)
    return attribution.squeeze(0).detach().numpy(), float(delta.item())
