"""Shared setup utilities. Verify with ``python -m src.utils``."""
from __future__ import annotations
import argparse
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any
import numpy as np
from src.config import Config, load_config as _load_config

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> Config:
    """Load the central config and validate setup-specific assumptions."""
    cfg = _load_config(path)
    risk = cfg["risk"]
    if not 0 < risk["medium_min"] < risk["high_min"] < 1:
        raise ValueError("Risk thresholds must satisfy 0 < medium < high < 1")
    seed = cfg["seed"]
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be an integer in [0, 2**32)")
    if not isinstance(cfg["study_area"]["shapefile"], str):
        raise ValueError("Provide study_area.shapefile as a config-relative path")
    return cfg


def get_logger(name: str = "canopycare", level: int = logging.INFO) -> logging.Logger:
    """Return an idempotent console logger without configuring the root logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def set_seed(seed: int, *, include_torch: bool = False) -> None:
    """Seed Python/NumPy and optionally PyTorch; hash seed must be set before launch.

    PYTHONHASHSEED set here applies to child interpreters only. Deterministic
    algorithms can still differ across hardware or dependency versions.
    """
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be an integer in [0, 2**32)")
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    if include_torch:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def projected_crs(value: str) -> Any:
    """Parse a CRS and reject geographic or non-metre grid coordinates."""
    from pyproj import CRS
    crs = CRS.from_user_input(value)
    if not crs.is_projected or not crs.axis_info or any(a.unit_name != "metre" for a in crs.axis_info):
        raise ValueError("Grid CRS must be projected with metre units")
    return crs


def utm_epsg(longitude: float, latitude: float) -> int:
    """Suggest the standard six-degree UTM zone (not polar/Norway/Svalbard exceptions)."""
    if not (-180 <= longitude <= 180 and -80 <= latitude <= 84):
        raise ValueError("Coordinate outside standard UTM coverage")
    zone = min(60, int((longitude + 180) // 6) + 1)
    return (32600 if latitude >= 0 else 32700) + zone


def transform_xy(x: Any, y: Any, source: str, target: str) -> tuple[Any, Any]:
    """Transform points with x/y order; WGS84 inputs are longitude/latitude."""
    from pyproj import Transformer
    return Transformer.from_crs(source, target, always_xy=True).transform(x, y, errcheck=True)


def study_area_path(cfg: Config) -> Path:
    """Resolve the configured boundary path independently of the working directory."""
    return (Path(cfg["_root"]) / cfg["study_area"]["shapefile"]).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    logger = get_logger()
    try:
        cfg = load_config(args.config)
        set_seed(cfg["seed"])
        crs = projected_crs(cfg["study_area"]["crs"])
        area = study_area_path(cfg)
        if not area.is_file():
            raise ValueError(f"Study-area file is missing: {area}")
        west, south, east, north = cfg["study_area"]["bbox_wgs84"]
        if not (-180 <= west < east <= 180 and -80 <= south < north <= 84):
            raise ValueError("Invalid study-area bounding box")
        lon, lat = (west + east) / 2, (south + north) / 2
        if crs.to_epsg() != utm_epsg(lon, lat):
            raise ValueError("Configured UTM CRS disagrees with the illustrative bounding-box centre")
        x, y = transform_xy(lon, lat, "EPSG:4326", crs.to_string())
        lon2, lat2 = transform_xy(x, y, crs.to_string(), "EPSG:4326")
        if not np.allclose([lon, lat], [lon2, lat2], atol=1e-7, rtol=0):
            raise ValueError("CRS round-trip check failed")
        t = cfg["time"]["prediction_start_year"]
        logger.info("Config OK | %s | grid=%s m | T=%s | target=%s-%s | seed=%s",
                    crs.to_string(), cfg["grid"]["cell_size_m"], t, t+1,
                    t+cfg["time"]["horizon_years"], cfg["seed"])
        logger.info("Study area exists: %s", area)
        logger.info("CRS round trip OK. Risk thresholds are unvalidated placeholders.")
        return 0
    except (ValueError, OSError, KeyError, ImportError) as error:
        logger.error("Setup check failed: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
