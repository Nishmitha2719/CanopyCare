"""Count supplied assets near cells without inferring impacts on people."""
from __future__ import annotations
import numpy as np
from scipy.spatial import cKDTree
from src.config import Config


def count_nearby(cell_xy_m: np.ndarray, asset_xy_m: np.ndarray, cfg: Config) -> np.ndarray:
    """Both arrays must use the configured metre CRS. Assets are not model features."""
    if len(asset_xy_m) == 0:
        return np.zeros(len(cell_xy_m), dtype=int)
    return np.asarray(cKDTree(asset_xy_m).query_ball_point(
        cell_xy_m, cfg["exposure"]["radius_m"], return_length=True))
