"""End-to-end buffered CV, fold-only preprocessing, and reproducible artifacts."""
from __future__ import annotations
import importlib.metadata
import platform
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, auc, confusion_matrix, f1_score,
                             precision_recall_curve, recall_score, roc_auc_score)
from src.carbon.scenario import carbon_scenario
from src.config import Config, fingerprint, public_config, resolve, write_json
from src.data.provenance import load_dataset, sha256
from src.features.validation import validate
from src.models.estimators import fit_model, predict
from src.models.spatial import spatial_splits
from src.xai.explain import permutation_importance


def metrics(y: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, Any]:
    precision, recall, _ = precision_recall_curve(y, p)
    predicted = p >= threshold
    return {"pr_auc": float(auc(recall, precision)),
            "average_precision": float(average_precision_score(y, p)),
            "recall": float(recall_score(y, predicted, zero_division=0)),
            "f1": float(f1_score(y, predicted, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, p)),
            "positive_prevalence": float(np.mean(y)),
            "confusion_matrix_tn_fp_fn_tp": confusion_matrix(y, predicted, labels=[0, 1]).ravel().tolist()}


def train(cfg: Config) -> dict[str, Any]:
    """Evaluate OOF scores, then fit a separate deployment research model on all cells."""
    raw, metadata = load_dataset(cfg)
    frame = validate(raw, metadata, cfg)
    x = frame[cfg["features"]["columns"]].to_numpy(dtype=float)
    y = frame.target.to_numpy(dtype=int)
    xy = frame[["x_m", "y_m"]].to_numpy()
    probability = np.full(len(frame), np.nan)
    fold_ids = np.full(len(frame), -1)
    fold_reports = []
    importance = []
    assignments = []
    threshold = cfg["validation"]["probability_threshold"]
    for fold, (train_idx, test_idx) in enumerate(spatial_splits(frame, cfg)):
        model = fit_model(x[train_idx], y[train_idx], xy[train_idx], cfg)
        probability[test_idx] = predict(model, x[test_idx], xy[test_idx], cfg)
        fold_ids[test_idx] = fold
        fold_reports.append({"fold": fold, "n_train": len(train_idx), "n_test": len(test_idx),
                             **metrics(y[test_idx], probability[test_idx], threshold)})
        importance.append({"fold": fold, **permutation_importance(model, x[test_idx], y[test_idx], xy[test_idx], cfg)})
        assignments.append({"fold": fold, "train_ids": frame.iloc[train_idx].cell_id.tolist(),
                            "test_ids": frame.iloc[test_idx].cell_id.tolist()})
    if not np.isfinite(probability).all() or (fold_ids < 0).any():
        raise AssertionError("Every eligible node needs exactly one held-out prediction")
    output = resolve(cfg, "reports")
    output.mkdir(parents=True, exist_ok=True)
    scores = frame.copy()
    scores["risk_score_oof"] = probability
    scores["fold"] = fold_ids
    scores["flag_for_review"] = probability >= threshold
    scores["data_mode"] = metadata["mode"]
    scores = scores.merge(carbon_scenario(frame, cfg), on="cell_id", validate="one_to_one")
    scores.to_csv(output / "predictions.csv", index=False)
    pd.DataFrame(importance).to_csv(output / "permutation_importance.csv", index=False)
    write_json(output / "fold_assignments.json", assignments)
    final_model = fit_model(x, y, xy, cfg)
    joblib.dump({"model": final_model, "features": cfg["features"]["columns"],
                 "config": public_config(cfg)}, output / "model.joblib")
    versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "PyYAML", "xgboost", "torch", "torch-geometric"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    report = {"data_mode": metadata["mode"], "model": cfg["model"]["kind"],
              "n_input": len(raw), "n_eligible": len(frame), "n_excluded": len(raw) - len(frame),
              "folds": fold_reports, "pooled_oof": metrics(y, probability, threshold),
              "config": public_config(cfg), "config_sha256": fingerprint(cfg),
              "dataset_sha256": metadata["dataset_sha256"], "python": platform.python_version(),
              "versions": versions, "prediction_sha256": sha256(output / "predictions.csv"),
              "interpretation": "Model associations only. Risk scores are uncalibrated. Human review required.",
              "limitations": ["Synthetic metrics are software checks, not forest-risk evidence." if metadata["mode"] == "synthetic"
                              else "Hindcast by observation cutoff; operational publication-time availability is not verified.",
                              "Tree-cover loss does not establish deforestation or its cause.",
                              "Spatial validation does not establish transfer to future years or other regions.",
                              "Permutation importance reflects model association and can be distorted by correlated predictors.",
                              "Carbon is an illustrative above-ground stock scenario, not emissions or avoided emissions."]}
    write_json(output / "metrics.json", report)
    (output / "requirements-observed.txt").write_text(
        "\n".join(f"{k}=={v}" for k, v in versions.items()) + "\n", encoding="utf-8")
    return report
