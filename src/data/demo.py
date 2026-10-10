"""Synthetic fixtures, never a source of empirical ecological claims."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import Config


def make_demo(cfg: Config) -> pd.DataFrame:
    """Generate reproducible spatially varying features and future binary labels."""
    d = cfg["demo"]
    rng = np.random.default_rng(cfg["seed"])
    row, col = np.indices((d["rows"], d["cols"]))
    row, col = row.ravel(), col.ravel()
    n = len(row)
    forest = rng.uniform(d["forest_min"], d["forest_max"], n)
    history = rng.beta(d["history_beta_a"], d["history_beta_b"], n)
    logit = (d["label_intercept"] + d["history_coefficient"] * history
             + d["forest_coefficient"] * forest
             + d["spatial_coefficient"] * np.sin(col / cfg["validation"]["block_size_m"] * 1000))
    positive = rng.random(n) < 1 / (1 + np.exp(-logit))
    loss = positive * rng.uniform(d["positive_loss_min"], d["positive_loss_max"], n)
    return pd.DataFrame({
        "cell_id": [f"N{i + 1:04d}" for i in range(n)],
        "x_m": d["origin_easting_m"] + (col + 0.5) * 1000,
        "y_m": d["origin_northing_m"] + (row + 0.5) * 1000,
        "area_ha": np.full(n, 100.0), "valid_fraction": np.ones(n),
        "forest_fraction": forest, "historical_loss_fraction": history,
        "elevation_m": d["elevation_base_m"] + rng.random(n) * d["elevation_range_m"],
        "slope_deg": rng.random(n) * d["slope_max_deg"],
        "future_loss_fraction": loss,
        "target": (loss >= cfg["forest"]["loss_threshold_fraction"]).astype(int),
    })
