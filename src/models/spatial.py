"""Buffered, group-disjoint spatial validation splits."""
from __future__ import annotations
from collections.abc import Iterator
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import StratifiedGroupKFold
from src.config import Config


def spatial_splits(frame: pd.DataFrame, cfg: Config) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Partition whole spatial blocks and exclude nearby training centroids."""
    settings = cfg["validation"]
    xy = frame[["x_m", "y_m"]].to_numpy()
    blocks = np.floor(xy / settings["block_size_m"]).astype(int)
    groups = np.array([f"{x}:{y}" for x, y in blocks])
    if len(np.unique(groups)) < settings["n_splits"]:
        raise ValueError("Fewer spatial blocks than folds")
    cv = StratifiedGroupKFold(settings["n_splits"], shuffle=True, random_state=cfg["seed"])
    for train, test in cv.split(xy, frame.target, groups):
        distance, _ = cKDTree(xy[test]).query(xy[train])
        train = train[distance > settings["buffer_m"]]
        if set(groups[train]) & set(groups[test]):
            raise AssertionError("Spatial blocks overlap")
        if len(train) == 0 or any(frame.iloc[idx].target.nunique() < 2 for idx in (train, test)):
            raise ValueError("A buffered fold lacks both classes; revise area/block/fold settings before evaluation")
        yield train, test
