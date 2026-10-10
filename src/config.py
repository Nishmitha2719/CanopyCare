"""Configuration and reproducibility utilities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

Config = dict[str, Any]


def load_config(path: str | Path) -> Config:
    """Load and validate explicit scientific assumptions; paths are config-relative."""
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["_root"] = str(path.parent)
    t = cfg["time"]
    if not 2001 <= t["prediction_start_year"] <= t["feature_dataset_end_year"]:
        raise ValueError("Feature dataset must cover T, with T >= 2001")
    if t["feature_dataset_end_year"] != t["prediction_start_year"]:
        raise ValueError("Historical feature release must end at T (no retrospective future release)")
    if t["horizon_years"] < 1 or t["prediction_start_year"] + t["horizon_years"] > t["label_dataset_end_year"]:
        raise ValueError("Label release does not cover the complete future horizon")
    if not 1 <= t["historical_loss_window_years"] <= t["prediction_start_year"] - 2000:
        raise ValueError("Historical loss window must lie in Hansen's observation period")
    if t["temporal_mode"] != "retrospective_observation_cutoff":
        raise ValueError("Operational release-date verification is not implemented")
    for role in ("feature", "label"):
        if f"change_{t[role + '_dataset_end_year']}_" not in cfg["earth_engine"][role + "_asset"]:
            raise ValueError(f"{role} asset and declared end year disagree")
    if cfg["earth_engine"]["elevation_source_end_year"] > t["prediction_start_year"]:
        raise ValueError("Elevation auxiliary source observations exceed T")
    if cfg["grid"]["cell_size_m"] != 1000:
        raise ValueError("This study requires 1 km cells")
    if cfg["grid"]["boundary_policy"] != "intersect_full_cells":
        raise ValueError("Only full intersecting boundary cells are supported")
    v = cfg["validation"]
    if v["n_splits"] < 2 or v["block_size_m"] < 1000 or v["buffer_m"] < 0:
        raise ValueError("Invalid spatial validation configuration")
    for value in (v["probability_threshold"], cfg["forest"]["loss_threshold_fraction"],
                  cfg["forest"]["min_forest_fraction"], cfg["forest"]["min_valid_fraction"]):
        if not 0 < value <= 1:
            raise ValueError("Thresholds must be in (0, 1]")
    if not 0 <= cfg["forest"]["canopy_threshold_pct"] <= 100:
        raise ValueError("Canopy threshold must be a percentage")
    if cfg["features"]["columns"] != ["forest_fraction", "historical_loss_fraction", "elevation_m", "slope_deg"]:
        raise ValueError("New features require an explicit extractor and provenance implementation")
    if cfg["carbon"]["biomass_mg_per_ha"] < 0 or not 0 < cfg["carbon"]["carbon_fraction"] <= 1:
        raise ValueError("Invalid biomass/carbon assumptions")
    if not 0 <= cfg["carbon"]["scenario_loss_fraction"] <= 1:
        raise ValueError("Scenario loss fraction must be in [0, 1]")
    return cfg


def resolve(cfg: Config, name: str) -> Path:
    """Resolve a configured artifact path."""
    return Path(cfg["_root"]) / cfg["paths"][name]


def public_config(cfg: Config) -> Config:
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def fingerprint(cfg: Config) -> str:
    return hashlib.sha256(json.dumps(public_config(cfg), sort_keys=True).encode()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
