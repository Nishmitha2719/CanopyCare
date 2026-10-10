"""Fold-local preprocessing and class-imbalance handling."""
from __future__ import annotations
from typing import Any
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from src.config import Config


def fit_model(x: np.ndarray, y: np.ndarray, xy: np.ndarray, cfg: Config) -> Any:
    """Fit exclusively on the supplied training subset."""
    settings = cfg["model"]
    kind = settings["kind"]
    if kind == "logistic":
        model = make_pipeline(StandardScaler(), LogisticRegression(
            C=settings["logistic_c"], max_iter=settings["logistic_max_iter"],
            class_weight="balanced", random_state=cfg["seed"]))
    elif kind == "xgboost":
        from xgboost import XGBClassifier
        model = XGBClassifier(n_estimators=settings["xgboost_estimators"],
            max_depth=settings["xgboost_max_depth"], learning_rate=settings["xgboost_learning_rate"],
            scale_pos_weight=float((y == 0).sum() / (y == 1).sum()),
            random_state=cfg["seed"], n_jobs=1, tree_method="hist", eval_metric="logloss")
    elif kind == "gnn":
        from src.models.graph import GraphClassifier
        return GraphClassifier(cfg).fit(x, y, xy)
    else:
        raise ValueError(f"Unknown model: {kind}")
    return model.fit(x, y)


def predict(model: Any, x: np.ndarray, xy: np.ndarray, cfg: Config) -> np.ndarray:
    if cfg["model"]["kind"] == "gnn":
        return model.predict_proba(x, xy)[:, 1]
    return model.predict_proba(x)[:, 1]
