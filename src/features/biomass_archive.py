"""Small OPeNDAP subset of the original pre-cutoff ESA CCI biomass release."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
import requests
from shapely.geometry import mapping
from src.config import Config, load_config, write_json
from src.data.exporting import area_geometry, file_hash, raster_layout


def parse_rows(response: str, rows: int, columns: int) -> np.ndarray:
    """Parse DAP ASCII array rows, refusing truncated/misaligned responses."""
    lines = re.findall(r"^\[0\]\[(\d+)\], (.+)$",response,re.MULTILINE)
    if len(lines) != rows: raise ValueError("Biomass response row count mismatch")
    data = np.empty((rows,columns),dtype="float32")
    for expected,(index,values) in enumerate(lines):
        if int(index) != expected: raise ValueError("Biomass response row order mismatch")
        array = np.fromstring(values,sep=",")
        if len(array) != columns: raise ValueError("Biomass response column count mismatch")
        data[expected] = array
    return data


def collect(cfg: Config) -> None:
    """Cache exact source attributes and query, reproject AGB density, preserve nodata."""
    s = cfg["preprocessing"]["biomass_archive"]
    if s["observation_end_year"] > cfg["time"]["prediction_start_year"]:
        raise ValueError("Biomass source extends beyond T")
    root = Path(cfg["_root"])
    setting = cfg["preprocessing"]["vetted_biomass"]
    path,metadata = root/setting["path"],root/setting["metadata"]
    path.parent.mkdir(parents=True,exist_ok=True)
    geo,utm,bounds = area_geometry(cfg)
    contract = hashlib.sha256(json.dumps({"settings":s,"aoi":mapping(geo),"crs":cfg["study_area"]["crs"],
                                         "nodata":cfg["collection"]["nodata"],"snap":cfg["collection"]["grid_origin_snap_m"]},sort_keys=True).encode()).hexdigest()
    if metadata.exists():
        meta = json.loads(metadata.read_text())
        if meta.get("contract_sha256") != contract: raise ValueError("Biomass archive configuration changed; choose a new path")
        if path.exists() and file_hash(path) == meta["sha256"]:
            print("REUSE biomass CCI 2017 v1",flush=True); return
    attributes = requests.get(s["url"]+".das",timeout=s["timeout_seconds"])
    attributes.raise_for_status()
    (path.parent/"source_attributes.das").write_text(attributes.text,encoding="utf-8")
    text = attributes.text
    for expected in ('String units "Mg/ha";', 'String product_version "1.0";', 'String date_created "31-Oct-2019', 'String time_coverage_end "20171231'):
        if expected not in text: raise ValueError(f"Unexpected biomass source metadata: {expected}")
    transform_string = re.search(r'String GeoTransform "([^"]+)"',text)
    if transform_string is None: raise ValueError("Missing biomass geotransform")
    x0,dx,rx,y0,ry,dy = map(float,transform_string.group(1).split())
    if rx or ry or dx <= 0 or dy >= 0: raise ValueError("Unexpected geographic biomass grid")
    fill_match = re.search(r'Int16 _FillValue (-?\d+)',text)
    if fill_match is None: raise ValueError("Missing biomass nodata metadata")
    nodata = int(fill_match.group(1))
    west,south,east,north = geo.bounds
    pad = s["padding_pixels"]
    c0,c1 = math.floor((west-x0)/dx)-pad,math.ceil((east-x0)/dx)+pad
    r0,r1 = math.floor((y0-north)/-dy)-pad,math.ceil((y0-south)/-dy)+pad
    constraint = f"{s['band']}[0][{r0}:{r1}][{c0}:{c1}]"
    response = requests.get(s["url"]+".ascii",params=constraint,timeout=s["timeout_seconds"])
    response.raise_for_status()
    ascii_path = path.parent/"agb_subset.ascii"
    ascii_path.write_text(response.text,encoding="utf-8")
    values = parse_rows(response.text,r1-r0+1,c1-c0+1)
    values[values < 0] = nodata
    src_transform = from_origin(x0+c0*dx,y0+r0*dy,dx,-dy)
    transform,width,height = raster_layout(bounds,s["export_scale_m"],cfg["collection"]["grid_origin_snap_m"])
    output = np.full((height,width),cfg["collection"]["nodata"],dtype="float32")
    if s["resampling"] != "average": raise ValueError("Only density-preserving average resampling supported")
    reproject(values,output,src_transform=src_transform,src_crs=4326,src_nodata=nodata,
              dst_transform=transform,dst_crs=cfg["study_area"]["crs"],dst_nodata=cfg["collection"]["nodata"],resampling=Resampling.average)
    outside = geometry_mask([mapping(utm)],out_shape=output.shape,transform=transform,invert=False)
    output[outside] = cfg["collection"]["nodata"]
    with rasterio.open(path,"w",driver="GTiff",width=width,height=height,count=1,dtype="float32",crs=cfg["study_area"]["crs"],transform=transform,nodata=cfg["collection"]["nodata"],compress="deflate") as dst:
        dst.write(output,1); dst.set_band_description(1,"agb_mg_ha")
    write_json(metadata,{"name":"biomass_cci_2017","source":s["url"],"doi":s["doi"],"version":s["version"],
                         "status":"complete","contract_sha256":contract,"predictor_allowed":True,
                         "observation_year":s["year"],"observation_end_year":s["observation_end_year"],
                         "source_created":"2019-10-31","units":"Mg/ha","native_crs":"EPSG:4326",
                         "native_resolution_degrees":dx,"output_crs":cfg["study_area"]["crs"],"output_scale_m":s["export_scale_m"],
                         "query":constraint,"subset_sha256":file_hash(ascii_path),"attributes_sha256":file_hash(path.parent/"source_attributes.das"),
                         "license":"ESA CCI Data Policy, free/open access; cite dataset DOI and acknowledge ESA CCI Biomass",
                         "file":str(path.relative_to(root)),"sha256":file_hash(path),
                         "notes":"2017 woody AGB, not a 2020 stock estimate; excludes roots/soil. Original v1 created before cutoff. Conservative 2019 source-information bound."})
    print("Downloaded historical ESA CCI biomass 2017 v1",flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config",default="config.yaml")
    collect(load_config(parser.parse_args().config))

if __name__ == "__main__": main()
