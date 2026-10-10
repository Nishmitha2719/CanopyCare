"""Bind input provenance to exact dataset bytes and scientific configuration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import Config, public_config, resolve, write_json


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_contract(cfg: Config) -> dict[str, Any]:
    public = public_config(cfg)
    return {key: public[key] for key in ("study_area", "grid", "time", "earth_engine", "forest", "features", "demo", "seed")}


def save_dataset(frame: pd.DataFrame, cfg: Config, mode: str) -> None:
    path = resolve(cfg, "dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    cutoff = cfg["time"]["prediction_start_year"]
    write_json(resolve(cfg, "provenance"), {
        "mode": mode, "dataset_sha256": sha256(path), "data_contract": data_contract(cfg),
        "features": {name: {"observation_end_year": (cfg["earth_engine"]["elevation_source_end_year"]
                                if mode == "earth_engine" and name in ("elevation_m", "slope_deg") else cutoff),
                            "source": "synthetic" if mode == "synthetic" else cfg["earth_engine"][
                                "elevation_asset" if name in ("elevation_m", "slope_deg") else "feature_asset"]}
                     for name in cfg["features"]["columns"]},
        "label_start_year": cutoff + 1,
        "label_end_year": cutoff + cfg["time"]["horizon_years"],
        "note": "Observation-cutoff hindcast; source publication availability at prediction time is not certified.",
    })


def load_dataset(cfg: Config) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = resolve(cfg, "dataset")
    metadata = json.loads(resolve(cfg, "provenance").read_text(encoding="utf-8"))
    if metadata["dataset_sha256"] != sha256(path) or metadata["data_contract"] != data_contract(cfg):
        raise ValueError("Dataset/config/provenance mismatch; regenerate or re-extract data")
    if metadata["mode"] not in ("synthetic", "earth_engine"):
        raise ValueError("Unknown dataset source mode")
    return pd.read_csv(path), metadata
