"""Fold-fitted model preprocessing; exported feature tables preserve missing values."""
from __future__ import annotations
from typing import Any
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from src.features.temporal import audit_features


def model_columns(manifest: dict[str,Any]) -> list[str]:
    """Use the explicit predictor allowlist; never select numeric columns wholesale."""
    audit_features(manifest["features"],manifest["cutoff_year"],manifest.get("sources"))
    columns = manifest["model_features"]
    if set(columns) & set(manifest["label_columns"]): raise ValueError("Label leaked into model columns")
    if any(c not in manifest["features"] for c in columns): raise ValueError("Unregistered model feature")
    return columns.copy()


def make_preprocessor() -> Pipeline:
    """Call fit only on spatial TRAIN data, then transform held-out cells.

    A column empty in a training fold receives the fixed zero fallback and a missing
    indicator. That fallback contains no held-out information. Globally unavailable
    source columns should already be excluded by model_columns().
    """
    return Pipeline([("impute",SimpleImputer(strategy="median",add_indicator=True,keep_empty_features=True)),
                     ("scale",StandardScaler())])
