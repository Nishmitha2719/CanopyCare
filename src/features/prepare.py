"""Acquire additional pre-cutoff rasters, keeping labels in a separate asset."""
from __future__ import annotations
import argparse
import calendar
import copy
from pathlib import Path
from typing import Any
from shapely.geometry import mapping
from src.config import Config, load_config, write_json
from src.data.exporting import area_geometry, export_layer
from src.data.gee_init import initialize
from src.data.layers import Layer, sentinel2, climate


def prepare(cfg: Config) -> None:
    """Download bounded raster tiles; refuse current-release Hansen as history."""
    ee = initialize(cfg)
    ee.data.setDeadline(cfg["collection"]["ee_deadline_ms"])
    c = copy.deepcopy(cfg)
    c["collection"]["raw_directory"] = cfg["preprocessing"]["input_directory"]
    p = cfg["preprocessing"]
    t = cfg["time"]["prediction_start_year"]
    geo, _, _ = area_geometry(cfg)
    aoi = ee.Geometry(mapping(geo), geodesic=False)
    for role, end, bands in [
        ("history", t, ["treecover2000", "lossyear", "datamask"]),
        ("labels", t + cfg["time"]["horizon_years"], ["lossyear", "datamask"]),
    ]:
        source = cfg["earth_engine"]["feature_asset" if role == "history" else "label_asset"]
        image = ee.Image(source).select(bands)
        # Archived Hansen loss-year bands mask zero/no-loss pixels. Restore zero
        # only on declared land; never turn off-footprint/ocean nodata into forest.
        land_mask = image.select("datamask").eq(1)
        image = image.addBands(image.select("lossyear").unmask(0).updateMask(land_mask), overwrite=True)
        layer = Layer(role, image, bands, p["history_scale_m"], source,
                      "2000-01-01", f"{end}-12-31", ["percent", "year offset", "class"] if role == "history" else ["year offset", "class"],
                      role == "history", "History and future labels are deliberately separate; CC BY 4.0.",
                      {"observation_end_year": end, "role": role})
        export_layer(ee, layer, c)
    years = range(t-p["spectral_lookback_years"]+1, t+1)
    for year in years:
        if year not in cfg["collection"]["years"]:
            s = cfg["collection"]["sentinel2"]
            scene = (ee.ImageCollection(s["asset"]).filterBounds(aoi)
                     .filterDate(f"{year}-{s['start_month']:02d}-01", f"{year}-{s['end_month_exclusive']:02d}-01")
                     .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", s["max_scene_cloud_pct"])))
            dates = scene.aggregate_array("system:time_start").getInfo()
            from datetime import datetime, timezone
            months = sorted({datetime.fromtimestamp(x/1000, timezone.utc).month for x in dates})
            if len(months) < p["min_season_months"]:
                write_json(Path(cfg["_root"])/p["input_directory"]/f"sentinel2_{year}"/"unavailable.json",
                           {"year": year, "source": s["asset"], "months_present": months,
                            "scene_count": len(dates), "reason": "Incomplete dry-season monthly coverage; no cross-sensor substitution."})
                print(f"Sentinel-2 {year}: unavailable for comparable season, months={months}", flush=True)
            else:
                export_layer(ee, sentinel2(ee, aoi, cfg, year), c)
            export_layer(ee, climate(ee, aoi, cfg, year), c)
        source = cfg["collection"]["chirps"]["asset"]
        daily = ee.ImageCollection(source).filterBounds(aoi).filterDate(f"{year}-01-01", f"{year+1}-01-01").select("precipitation")
        expected = 365+calendar.isleap(year)
        if daily.size().getInfo() != expected:
            raise ValueError(f"Incomplete rainfall year {year}")
        images = [daily.sum().rename("annual_rainfall_mm"), daily.count().rename("valid_days")]
        for season in ("dry", "wet"):
            subset = daily.filter(ee.Filter.Or(*[ee.Filter.calendarRange(m,m,"month") for m in p[f"{season}_months"]]))
            expected_season = sum(calendar.monthrange(year,m)[1] for m in p[f"{season}_months"])
            if subset.size().getInfo() != expected_season: raise ValueError("Incomplete rainfall season")
            images += [subset.sum().rename(f"{season}_rainfall_mm"), subset.count().rename(f"{season}_valid_days")]
        bands = ["annual_rainfall_mm", "valid_days", "dry_rainfall_mm", "dry_valid_days", "wet_rainfall_mm", "wet_valid_days"]
        layer = Layer(f"rain_season_{year}", ee.Image.cat(images), bands, cfg["collection"]["chirps"]["export_scale_m"],
                      source, f"{year}-01-01", f"{year+1}-01-01", ["mm", "days"]*3, True,
                      "End exclusive; Jan-Apr dry, May-Dec wet. Native 0.05 degree information; public domain.",
                      {"observation_end_year": year, "end_exclusive": True})
        export_layer(ee, layer, c)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    prepare(load_config(args.config))

if __name__ == "__main__": main()
