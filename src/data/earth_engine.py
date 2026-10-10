"""Hansen observation-cutoff extraction with separate feature and label assets."""
from __future__ import annotations

import json

import pandas as pd

from src.config import Config, resolve
from src.data.grid import make_grid


def extract(cfg: Config) -> pd.DataFrame:
    """Extract in bounded batches using an already authenticated EE account.

    Remaining forest is baseline tree cover excluding loss through T. Regrowth is
    not included. Loss is tree-cover disturbance, not necessarily deforestation.
    """
    from src.data.gee_init import initialize

    settings = cfg["earth_engine"]
    ee = initialize(cfg)
    grid = make_grid(cfg)
    path = resolve(cfg, "grid")
    path.parent.mkdir(parents=True, exist_ok=True)
    grid.to_crs("EPSG:4326").to_file(path, driver="GeoJSON")
    t = cfg["time"]["prediction_start_year"] - 2000
    horizon = cfg["time"]["horizon_years"]
    historical = ee.Image(settings["feature_asset"])
    labels = ee.Image(settings["label_asset"])
    year = historical.select("lossyear").unmask(0).updateMask(historical.select("datamask").eq(1))
    land = historical.select("datamask").eq(1)
    base = historical.select("treecover2000").gte(cfg["forest"]["canopy_threshold_pct"]).And(land)
    remaining = base.And(year.eq(0).Or(year.gt(t)))
    recent = base.And(year.gt(t - cfg["time"]["historical_loss_window_years"])).And(year.lte(t))
    future_year = labels.select("lossyear").unmask(0).updateMask(labels.select("datamask").eq(1))
    future_valid = labels.select("datamask").eq(1)
    # Future coverage is an eligibility/label-quality check, never a predictor.
    valid = land.And(future_valid)
    future = remaining.And(future_year.gt(t)).And(future_year.lte(t + horizon))
    elevation = ee.Image(settings["elevation_asset"]).select("elevation")
    terrain_valid = elevation.mask()
    pixel_area = ee.Image.pixelArea()
    sums = ee.Image.cat([
        pixel_area.rename("total_m2"),
        pixel_area.multiply(valid.And(terrain_valid)).rename("valid_m2"),
        pixel_area.multiply(remaining).rename("forest_m2"),
        pixel_area.multiply(recent).rename("history_m2"),
        pixel_area.multiply(future).rename("future_m2"),
        pixel_area.multiply(elevation).rename("elevation_weighted"),
        pixel_area.multiply(ee.Terrain.slope(elevation)).rename("slope_weighted"),
        pixel_area.updateMask(elevation.mask()).rename("terrain_m2"),
        pixel_area.updateMask(ee.Terrain.slope(elevation).mask()).rename("slope_m2"),
    ])
    records = []
    chunk = settings["chunk_cells"]
    for start in range(0, len(grid), chunk):
        geojson = json.loads(grid.iloc[start:start + chunk].to_crs("EPSG:4326").to_json())
        reduced = sums.reduceRegions(
            collection=ee.FeatureCollection(geojson), reducer=ee.Reducer.sum(),
            scale=settings["scale_m"], crs=cfg["study_area"]["crs"], tileScale=settings["tile_scale"],
        ).getInfo()
        records.extend(item["properties"] for item in reduced["features"])
        print(f"Extracted {min(start + chunk, len(grid))}/{len(grid)} cells", flush=True)
    raw = pd.DataFrame(records)
    if raw.empty:
        raise ValueError("No cells extracted")
    frame = raw[["cell_id", "x_m", "y_m", "area_ha"]].copy()
    frame["valid_fraction"] = raw.valid_m2 / raw.total_m2
    frame["forest_fraction"] = raw.forest_m2 / raw.total_m2
    frame["historical_loss_fraction"] = raw.history_m2 / raw.total_m2
    frame["elevation_m"] = raw.elevation_weighted / raw.terrain_m2
    frame["slope_deg"] = raw.slope_weighted / raw.slope_m2
    frame["future_loss_fraction"] = raw.future_m2 / raw.forest_m2.where(raw.forest_m2 > 0)
    frame["target"] = (frame.future_loss_fraction >= cfg["forest"]["loss_threshold_fraction"]).astype(int)
    return frame
