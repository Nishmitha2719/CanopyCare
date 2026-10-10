"""Verify local rasters/vectors and produce the source catalog plus a completion manifest."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping
from src.config import Config, write_json
from src.utils import load_config, DEFAULT_CONFIG
from src.data.exporting import area_geometry, file_hash, raster_layout

SOURCES = {
 "sentinel2": ("COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved", "10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM", "Copernicus Sentinel Data Terms and Conditions", "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED"),
 "hansen": ("Hansen GFC v1.13, 2000-2025 (latest verified 2026-10-07)", "0.00025 degrees (~28-31 m), EPSG:4326", "CC-BY-4.0", "https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13"),
 "dem": ("NASA/USGS SRTMGL1 v003; acquisition February 2000", "1 arc-second (~30 m), EPSG:4326", "Publicly available NASA/JPL data; JPL image-use policy (see catalog)", "https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003"),
 "rainfall": ("CHIRPS v2.0 Final daily", "0.05 degrees (~5.6 km), EPSG:4326", "Public domain / copyright waiver", "https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY"),
 "climate": ("ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis)", "0.1 degrees (~11.1 km), EPSG:4326", "Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data", "https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR"),
 "biomass": ("GEDI L4B version 2; 2019-04-18 through 2021-08-04", "~1 km, EPSG:6933 EASE-Grid 2.0 Global", "Public domain; NASA Earth Science Data policy", "https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_B_002"),
 "population": ("WorldPop Global Project country-year 2020, India", "3 arc-seconds (~93 m at equator), EPSG:4326", "CC-BY-4.0; attribution to WorldPop", "https://developers.google.com/earth-engine/datasets/catalog/WorldPop_GP_100m_pop"),
 "roads": ("OpenStreetMap contributors, Overpass historical attic snapshot", "Vector, EPSG:4326; variable positional accuracy", "ODbL-1.0; Ã‚Â© OpenStreetMap contributors", "https://www.openstreetmap.org/copyright"),
 "settlements": ("OpenStreetMap place-tagged nodes/way centres/relation centres", "Vector points, EPSG:4326; variable completeness", "ODbL-1.0; Ã‚Â© OpenStreetMap contributors", "https://www.openstreetmap.org/copyright"),
 "mining": ("Maus et al. global mining polygons version 2, published 2022", "Vector; primarily 2019 10 m imagery, EPSG:4326", "CC-BY-SA-4.0", "https://doi.pangaea.de/10.1594/PANGAEA.942325"),
}


def expected_names(cfg: Config) -> list[str]:
    return ([f"{name}_{year}" for name in ("sentinel2","rainfall","climate") for year in cfg["collection"]["years"]]
            +["hansen_latest","dem","biomass_gedi",f"population_{cfg['collection']['population']['year']}","roads","settlements","mining"])


def inspect(cfg: Config) -> dict[str,Any]:
    """Check exact grid, AOI pixels, every band, vector intersections and content hashes."""
    root=Path(cfg["_root"]);raw=root/cfg["collection"]["raw_directory"]
    _,utm,bounds=area_geometry(cfg)
    records=[]
    for name in expected_names(cfg):
        state=raw/name/"metadata.json"
        record={"name":name,"passed":False}
        try:
            meta=json.loads(state.read_text(encoding="utf-8"));record["metadata"]=meta
            if meta["status"]!="complete":raise ValueError("Export is not complete locally")
            path=root/meta["file"]
            if file_hash(path)!=meta["sha256"]:raise ValueError("File checksum mismatch")
            if path.suffix==".tif":
                affine,width,height=raster_layout(bounds,meta["scale"],cfg["collection"]["grid_origin_snap_m"])
                with rasterio.open(path) as src:
                    if src.crs!=cfg["study_area"]["crs"] or not src.transform.almost_equals(affine):raise ValueError("CRS/grid mismatch")
                    if (src.width,src.height,src.count)!=(width,height,len(meta["bands"])):raise ValueError("Raster shape mismatch")
                    if list(src.descriptions)!=meta["bands"]:raise ValueError("Band names mismatch")
                    inside=geometry_mask([mapping(utm)],out_shape=(height,width),transform=affine,invert=True)
                    stats=[]
                    for i,band in enumerate(meta["bands"],1):
                        data=src.read(i,masked=True)
                        valid=inside & ~np.ma.getmaskarray(data) & np.isfinite(data.data)
                        fraction=float(valid.sum()/inside.sum())
                        if fraction<cfg["collection"]["quality"]["minimum_valid_fraction"]:raise ValueError(f"{band}: insufficient valid AOI coverage ({fraction:.4f})")
                        values=data.data[valid]
                        stats.append({"band":band,"valid_aoi_fraction":fraction,"min":float(values.min()),"max":float(values.max()),"mean":float(values.mean())})
                    record["bands"]=stats
            else:
                frame=gpd.read_file(path)
                if frame.crs!=cfg["study_area"]["crs"]:raise ValueError("Vector CRS mismatch")
                if not frame.is_valid.all() or frame.geometry.is_empty.any():raise ValueError("Invalid vector geometry")
                if len(frame) and not frame.geometry.within(utm.buffer(0.01)).all():raise ValueError("Vector extends outside AOI")
                record["feature_count"]=len(frame)
                if not len(frame):record["warning"]="Valid empty source intersection; does not prove real-world absence."
            record["passed"]=True
        except Exception as error:record["error"]=str(error)
        records.append(record)
    result={"complete":all(r["passed"] for r in records),"expected_layers":len(records),"passed_layers":sum(r["passed"] for r in records),"layers":records}
    write_json(raw/"validation.json",result)
    catalog(cfg,result)
    return result


def catalog(cfg: Config, result: dict[str,Any]) -> None:
    """Generate human-readable catalog, including missing exports rather than hiding them."""
    lines=["# CanopyCare data catalog", "", "Study area: configured illustrative Kodagu/Wayanad polygon; replace it before administrative claims.",
           f"Output CRS: **{cfg['study_area']['crs']}**. Date ranges ending January/May 1 are end-exclusive for annual/seasonal collections.",
           f"Completion: **{result['passed_layers']}/{result['expected_layers']} local layers verified**. See `raw/collection/validation.json` for full per-band coverage and checksums.","",
           "## Alignment and export policy","", "All rasters share the same UTM anchor snapped to 3,000 m. They retain different pixel sizes: 20 m optical, 30 m terrain/forest-change, 100 m population density, and 1 km climate/biomass. These are spatially registered, not identical arrays. Resample explicitly before stacking. Climate sampling at 1 km does not add detail beyond its native grid.",
           "", "Local downloads use <=30 MiB uncompressed tiles with bounded retries and identical-contract resume. Each final GeoTIFF has a checksum, band labels and nodata=-9999. Optional Drive tasks are recorded as submitted and do not satisfy local completion. Vectors are clipped and saved as UTM GeoPackages; original responses/source files are retained.",
           "", "## Temporal safety","", "Collection is not feature admission. `predictor_allowed=false` blocks GEDI's post-2020 observations, the latest Hansen release, unverified WorldPop covariate dates, and mining with undated supporting imagery. Post-T Sentinel/climate layers are reference/target-period data only. Historical OSM is queried as of 2020-12-31, without current-data fallback. All source products are retrospective releases; operational publication-time availability is not certified.",
           "", "Predictor eligibility must be checked again in feature engineering; existing model code never auto-loads these new files.",""]
    for record in result["layers"]:
        name=record["name"];kind=name.split("_")[0];source,res,license,url=SOURCES[kind]
        meta=record.get("metadata",{})
        lines.extend([f"## {name}","",f"- Source/version: {source}. [Provider documentation]({url})",
                      f"- Native resolution/CRS: {res}.",f"- License: {license}.",
                      f"- Observation dates: {meta.get('start','pending')} to {meta.get('end','pending')}.",
                      f"- Local status: {'verified' if record['passed'] else 'MISSING/FAILED: '+record.get('error','unknown')}.",
                      f"- File: `{meta.get('file','not downloaded')}`.",f"- Output CRS: {cfg['study_area']['crs']}; resolution: {str(meta.get('scale'))+' m' if 'scale' in meta else 'vector'}.",
                      f"- Bands/units: {dict(zip(meta.get('bands',[]),meta.get('units',[]))) or 'See vector attributes; geometry is the observation.'}",
                      f"- Pre-T predictor admission: {meta.get('predictor_allowed','pending')}.",
                      f"- Processing/limitations: {meta.get('notes','Pending acquisition.')}",
                      f"- SHA-256: `{meta.get('sha256','pending')}`.",""])
        if "bands" in record:
            lines.append("AOI valid coverage: " + "; ".join(f"{b['band']}: {100*b['valid_aoi_fraction']:.2f}%" for b in record["bands"]) + ".")
            if kind == "biomass":
                lines.append("QF 1 denotes land; QF 2 meets the GEDI precision requirement. Many land pixels have no MU/SE estimate; do not replace those missing estimates with zero.")
        if 'feature_count' in record:lines.append(f"AOI features: {record['feature_count']}. {record.get('warning','')}")
    lines.extend(["## Interpretation and source limitations","",
        "SCL masking leaves potential thin cloud/shadow errors; clear_count reports retained granule samples, not unique acquisition dates. Overlapping source tiles can increase the count. Reflectances above 1 are retained and require visual review rather than silent clipping. Hansen tree loss is disturbance, not automatically deforestation. Gain is only 2000-2012. Aspect is circular and must not be averaged as a scalar across north. GEDI MU is mean aboveground dry biomass in Mg/ha, including forest and non-forest; retain SE/QF for uncertainty and quality assessment.","",
        "CHIRPS annual totals are sums of daily mm; ERA5 temperature and topsoil water are day-weighted annual means from monthly data. Population density is derived before reprojection, avoiding treating resampled source counts as target-cell counts; exact total preservation is not asserted.","",
        "Maus v2 is a reproducible published global footprint source, not an exhaustive Indian mining inventory. Its mapping domain was restricted near known mine coordinates; small unlisted quarries and artisanal sites can be absent. Polygons denote mining-associated land cover, not proof of legal status, activity in a specific year, or cause of forest loss. No national completeness claim is made. Consult local records before prioritizing interventions. Maus v2 was chosen for its stable original polygon download, documented 2019 primary imagery, and permissive attribution/share-alike license. Newer global classifications using Maus/Tang unions also exist (https://www.nature.com/articles/s41597-026-06681-x); those are not claimed to be historical 2020 inventories. No source here is claimed to be a complete Indian mine census.","",
        "Contains modified Copernicus Climate Change Service information. Neither the European Commission nor ECMWF is responsible for use of these data. Preserve provider citations/licenses when distributing derivatives. Model outputs describe association; humans decide.",""])
    lines.extend(["", "## Historical preprocessing additions", "", "See [PREPROCESSING_DATA_CATALOG.md](PREPROCESSING_DATA_CATALOG.md) for cutoff-specific Hansen, 2017/2018 composites, seasonal climate, ESA CCI biomass, GHSL population and historical OSM quarry proxies."])
    (Path(cfg["_root"])/"data/DATA_CATALOG.md").write_text("\n".join(lines),encoding="utf-8")


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--config",default=str(DEFAULT_CONFIG))
    cfg=load_config(parser.parse_args().config);result=inspect(cfg)
    print(f"Verified {result['passed_layers']}/{result['expected_layers']} local layers")
    for item in result["layers"]:
        if not item["passed"]:print(item["name"],item["error"])
    return 0 if result["complete"] else 1

if __name__=="__main__":raise SystemExit(main())
