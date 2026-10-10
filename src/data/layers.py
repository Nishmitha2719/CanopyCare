"""Earth Engine source builders. These collect observations, not training predictors."""
from __future__ import annotations
import calendar
from dataclasses import dataclass, field
from typing import Any
from src.config import Config

@dataclass
class Layer:
    name: str
    image: Any
    bands: list[str]
    scale: int
    source: str
    start: str
    end: str
    units: list[str]
    predictor_allowed: bool
    notes: str
    metadata: dict[str, Any] = field(default_factory=dict)


def sentinel2(ee: Any, aoi: Any, cfg: Config, year: int) -> Layer:
    """SCL-mask each observation then take per-band dry-season medians."""
    s=cfg["collection"]["sentinel2"]
    start=f"{year}-{s['start_month']:02d}-01"
    end=f"{year}-{s['end_month_exclusive']:02d}-01"
    source=(ee.ImageCollection(s["asset"]).filterBounds(aoi).filterDate(start,end)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE",s["max_scene_cloud_pct"])))
    count=source.size().getInfo()
    if count == 0: raise ValueError(f"No Sentinel-2 scenes for {year}")
    def mask(im: Any) -> Any:
        valid=im.select("SCL").remap(s["scl_keep"],[1]*len(s["scl_keep"]),0).eq(1)
        return im.select(s["bands"]).multiply(s["reflectance_multiplier"]).updateMask(valid)
    clean=source.map(mask)
    image=clean.median().addBands(clean.select("B2").count().rename("clear_count"))
    return Layer(f"sentinel2_{year}",image,s["bands"]+["clear_count"],s["export_scale_m"],s["asset"],
                 start,end,["reflectance"]*6+["observations"],year<=cfg["time"]["prediction_start_year"],
                 "End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.",
                 {"scene_count":count,"scene_ids":source.aggregate_array("system:index").getInfo()})


def hansen(ee: Any, cfg: Config) -> Layer:
    s=cfg["collection"]["hansen"]
    return Layer("hansen_latest",ee.Image(s["asset"]).select(s["bands"]),s["bands"],s["export_scale_m"],s["asset"],
                 "2000-01-01",f"{s['end_year']}-12-31",["percent","binary","year offset from 2000","binary","class"],False,
                 "Reference/labels only: latest release is forbidden as a historical predictor. Gain covers 2000-2012 only, not through 2025.")


def dem(ee: Any, cfg: Config) -> Layer:
    s=cfg["collection"]["dem"]
    image=ee.Terrain.products(ee.Image(s["asset"])).select(["elevation","slope","aspect"])
    return Layer("dem",image,["elevation","slope","aspect"],s["export_scale_m"],s["asset"],"2000-02-11","2000-02-22",
                 ["m","degrees","degrees clockwise from north"],True,
                 "SRTM V3 contains auxiliary void filling; conservative auxiliary source bound is configured separately. Flat-area aspect has little meaning.")


def rainfall(ee: Any, aoi: Any, cfg: Config, year: int) -> Layer:
    s=cfg["collection"]["chirps"]
    start,end=f"{year}-01-01",f"{year+1}-01-01"
    coll=ee.ImageCollection(s["asset"]).filterBounds(aoi).filterDate(start,end).select("precipitation")
    count=coll.size().getInfo()
    if count != 365+calendar.isleap(year): raise ValueError(f"Incomplete CHIRPS year {year}: {count} days")
    image=coll.sum().rename("annual_rainfall_mm").addBands(coll.count().rename("valid_days"))
    return Layer(f"rainfall_{year}",image,["annual_rainfall_mm","valid_days"],s["export_scale_m"],s["asset"],start,end,
                 ["mm/year","days"],year<=cfg["time"]["prediction_start_year"],
                 "Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.",{"daily_images":count})


def climate(ee: Any, aoi: Any, cfg: Config, year: int) -> Layer:
    s=cfg["collection"]["era5"]
    start,end=f"{year}-01-01",f"{year+1}-01-01"
    coll=ee.ImageCollection(s["asset"]).filterBounds(aoi).filterDate(start,end)
    if coll.size().getInfo()!=12: raise ValueError(f"Incomplete ERA5-Land year {year}")
    def weighted(im: Any) -> Any:
        date=ee.Date(im.get("system:time_start"))
        days=date.advance(1,"month").difference(date,"day")
        return im.select([s["temperature_band"],s["moisture_band"]]).multiply(days)
    mean=coll.map(weighted).sum().divide(365+calendar.isleap(year))
    temp=mean.select(s["temperature_band"]).subtract(s["kelvin_offset"]).rename("temperature_c")
    moisture=mean.select(s["moisture_band"]).rename("soil_moisture_m3_m3")
    return Layer(f"climate_{year}",temp.addBands(moisture),["temperature_c","soil_moisture_m3_m3"],s["export_scale_m"],s["asset"],start,end,
                 ["degrees Celsius","m3/m3"],year<=cfg["time"]["prediction_start_year"],
                 "Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.")


def biomass(ee: Any, cfg: Config) -> Layer:
    s=cfg["collection"]["biomass"]
    return Layer("biomass_gedi",ee.Image(s["asset"]).select(s["bands"]),s["bands"],s["export_scale_m"],s["asset"],
                 s["observation_start"],s["observation_end"],["Mg dry biomass/ha","Mg dry biomass/ha","quality flag","samples"],False,
                 "GEDI L4B v2 mean AGBD and standard error; includes 2021 observations: forbidden for T=2020 predictors. Gaps/quality flags are retained.")


def population(ee: Any, aoi: Any, cfg: Config) -> Layer:
    s=cfg["collection"]["population"]
    coll=(ee.ImageCollection(s["asset"]).filter(ee.Filter.eq("country",s["country"]))
          .filter(ee.Filter.eq("year",s["year"])).filterBounds(aoi))
    if coll.size().getInfo()!=1: raise ValueError("Expected exactly one WorldPop country/year raster")
    image=ee.Image(coll.first()).select("population")
    # Convert source counts to a density at their native pixel area before reprojection.
    area=ee.Image.pixelArea().reproject(image.projection())
    density=image.divide(area).multiply(1e6).rename("population_per_km2")
    return Layer(f"population_{s['year']}",density,["population_per_km2"],s["export_scale_m"],s["asset"],
                 f"{s['year']}-01-01",f"{s['year']}-12-31",["people/km2"],False,
                 "Density derived from native pixel counts; resampling does not exactly conserve population totals. Covariate vintage unverified: not approved as historical predictor.")
