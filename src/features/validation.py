"""Fail-closed temporal, numeric, and target validation."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config import Config


def validate(frame: pd.DataFrame, metadata: dict[str, Any], cfg: Config) -> pd.DataFrame:
    """Validate all eligible cells. Missing predictors are errors, not silent drops."""
    cols = cfg["features"]["columns"]
    required = cols + ["cell_id", "x_m", "y_m", "area_ha", "valid_fraction", "target", "future_loss_fraction"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.cell_id.isna().any() or frame.cell_id.duplicated().any() or not frame.cell_id.str.fullmatch(r"N\d{4,}").all():
        raise ValueError("Cell IDs must be unique N0001-style identifiers")
    t = cfg["time"]["prediction_start_year"]
    if set(metadata["features"]) != set(cols):
        raise ValueError("Every predictor requires provenance")
    if any(not isinstance(item["observation_end_year"], int) or item["observation_end_year"] > t
           for item in metadata["features"].values()):
        raise ValueError("Feature observations extend past T")
    if (metadata["label_start_year"], metadata["label_end_year"]) != (t + 1, t + cfg["time"]["horizon_years"]):
        raise ValueError("Label horizon mismatch")
    if not np.isfinite(frame[["x_m", "y_m", "area_ha", "valid_fraction", "forest_fraction"]]).all().all():
        raise ValueError("Non-finite spatial/coverage fields")
    if frame[["x_m", "y_m"]].duplicated().any() or not np.allclose(frame.area_ha, 100):
        raise ValueError("Expected distinct full 1 km square cells (100 ha)")
    if not frame.valid_fraction.between(0, 1 + 1e-9).all():
        raise ValueError("Invalid coverage fraction")
    selected = frame.loc[(frame.forest_fraction >= cfg["forest"]["min_forest_fraction"])
                         & (frame.valid_fraction >= cfg["forest"]["min_valid_fraction"])].copy()
    numeric = cols + ["future_loss_fraction", "target"]
    if selected.empty or not np.isfinite(selected[numeric]).all().all():
        raise ValueError("Empty eligible dataset or non-finite predictors/labels")
    for col, (low, high) in cfg["features"]["ranges"].items():
        if not selected[col].between(low, high).all():
            raise ValueError(f"Feature {col} outside configured range")
    if not selected.future_loss_fraction.between(0, 1 + 1e-9).all():
        raise ValueError("Loss fraction outside [0,1]")
    expected = (selected.future_loss_fraction >= cfg["forest"]["loss_threshold_fraction"]).astype(int)
    if not np.array_equal(expected, selected.target):
        raise ValueError("Targets disagree with configured loss threshold")
    if selected.target.nunique() != 2:
        raise ValueError("Both target classes are needed for evaluation")
    return selected.reset_index(drop=True)
