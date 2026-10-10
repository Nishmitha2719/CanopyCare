"""Resumable tiled GeoTIFF download, shared UTM anchoring, and optional Drive export."""
from __future__ import annotations
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import fields
from pathlib import Path
from typing import Any
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window
import requests
from shapely.geometry import mapping
from src.config import Config, write_json
from src.data.layers import Layer


def area_geometry(cfg: Config) -> tuple[Any, Any, tuple[float,...]]:
    """Read the actual polygon (not the fallback bbox) and return WGS84/UTM geometry."""
    source=Path(cfg["_root"])/cfg["study_area"]["shapefile"]
    frame=gpd.read_file(source)
    if frame.crs is None or frame.empty or not frame.is_valid.all(): raise ValueError("Invalid AOI")
    utm=frame.to_crs(cfg["study_area"]["crs"]).geometry.union_all()
    geo=frame.to_crs(4326).geometry.union_all()
    if geo.geom_type not in ("Polygon","MultiPolygon"): raise ValueError("AOI must be polygonal")
    return geo,utm,utm.bounds


def raster_layout(bounds: tuple[float,...], scale: int, snap: int) -> tuple[Any,int,int]:
    left=math.floor(bounds[0]/snap)*snap
    top=math.ceil(bounds[3]/snap)*snap
    return from_origin(left,top,scale,scale),math.ceil((bounds[2]-left)/scale),math.ceil((top-bounds[1])/scale)


def file_hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def export_layer(ee: Any, layer: Layer, cfg: Config, mode: str="local") -> dict[str,Any]:
    """Download safe-size tiles, validate headers, then stream into an AOI mosaic.

    Completed tiles can be reused only for an identical source/config/geometry contract.
    A Drive task is explicitly marked submitted, never locally complete.
    """
    s=cfg["collection"]
    raw=Path(cfg["_root"])/s["raw_directory"]
    directory=raw/layer.name; directory.mkdir(parents=True,exist_ok=True)
    geo,utm,bounds=area_geometry(cfg)
    transform,width,height=raster_layout(bounds,layer.scale,s["grid_origin_snap_m"])
    crs=cfg["study_area"]["crs"]
    aoi=ee.Geometry(mapping(geo),proj="EPSG:4326",geodesic=False)
    image=layer.image.clip(aoi).toFloat().unmask(s["nodata"],sameFootprint=False)
    meta={f.name:getattr(layer,f.name) for f in fields(layer) if f.name!="image"}
    # Avoid JSON-serializing EE internals and bind resumability to the computation graph.
    contract={"metadata":meta,"collection":s,"crs":crs,"aoi":mapping(geo),"expression":layer.image.serialize()}
    legacy_digest=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    # User-Agent changes transport only; exclude it from scientific raster contracts.
    contract["collection"]=json.loads(json.dumps(s))
    contract["collection"]["osm"].pop("user_agent",None)
    digest=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    meta.update({"contract_sha256":digest,"output_crs":crs,"transform":list(transform)[:6],
                 "width":width,"height":height,"status":"started"})
    state=directory/"metadata.json"
    if state.exists():
        previous=json.loads(state.read_text())
        if previous.get("contract_sha256") not in (digest,legacy_digest):
            raise ValueError(f"{layer.name}: existing export uses a different contract; choose a new raw_directory")
        output=directory/(layer.name+".tif")
        if previous.get("status")=="complete" and output.exists() and file_hash(output)==previous.get("sha256"):
            previous["contract_sha256"]=digest
            write_json(state,previous)
            print(f"REUSE {layer.name}",flush=True); return previous
    write_json(state,meta)
    if mode=="drive":
        task=ee.batch.Export.image.toDrive(image=image,description=layer.name,folder=s["drive_folder"],
            fileNamePrefix=layer.name,region=aoi,crs=crs,crsTransform=list(transform)[:6],
            maxPixels=s["max_export_pixels"],fileFormat="GeoTIFF",formatOptions={"cloudOptimized":True,"noData":s["nodata"]})
        task.start();meta.update(status="submitted",task_id=task.id);write_json(state,meta);return meta
    size=s["tile_pixels"]
    if size>10000 or size*size*len(layer.bands)*4>30*1024*1024: raise ValueError("Tile exceeds safe GEE request size")
    tiles=[]
    for row in range(0,height,size):
        for col in range(0,width,size):
            w,h=min(size,width-col),min(size,height-row)
            tiles.append((col,row,w,h))
    def download(tile: tuple[int,int,int,int]) -> tuple[Path,Window]:
        col,row,w,h=tile
        path=directory/f"tile_{row}_{col}.tif"
        affine=transform*rasterio.Affine.translation(col,row)
        def valid() -> bool:
            try:
                with rasterio.open(path) as src:
                    if not (src.count==len(layer.bands) and src.width==w and src.height==h and src.crs==crs and src.transform.almost_equals(affine)):
                        return False
                    src.read() # Decode cached pixels: a valid header alone does not establish a complete tile.
                    return True
            except (OSError,rasterio.errors.RasterioError): return False
        if not valid():
            for attempt in range(s["attempts"]):
                try:
                    url=image.getDownloadURL({"crs":crs,"crs_transform":list(affine)[:6],"dimensions":[w,h],
                                              "format":"GEO_TIFF","filePerBand":False})
                    response=requests.get(url,timeout=s["http_timeout_seconds"]);response.raise_for_status()
                    temp=path.with_suffix(".partial")
                    temp.write_bytes(response.content)
                    with rasterio.open(temp) as src:
                        if src.width!=w or src.height!=h or src.count!=len(layer.bands): raise ValueError("Unexpected tile dimensions")
                        if src.crs!=crs or not src.transform.almost_equals(affine): raise ValueError("Unexpected tile grid")
                    temp.replace(path)
                    break
                except Exception:
                    if attempt+1==s["attempts"]: raise
                    time.sleep(s["retry_backoff_seconds"]*(attempt+1))
        return path,Window(col,row,w,h)
    output=directory/(layer.name+".tif")
    partial=directory/(layer.name+".partial.tif")
    with rasterio.open(partial,"w",driver="GTiff",width=width,height=height,count=len(layer.bands),dtype="float32",
                       crs=crs,transform=transform,nodata=s["nodata"],compress="deflate",predictor=3,tiled=True,BIGTIFF="IF_SAFER") as dst:
        for i,band in enumerate(layer.bands,1): dst.set_band_description(i,band)
        with ThreadPoolExecutor(max_workers=s["download_workers"]) as pool:
            jobs=[pool.submit(download,t) for t in tiles]
            for i,job in enumerate(as_completed(jobs),1):
                path,window=job.result()
                with rasterio.open(path) as src: dst.write(src.read(),window=window)
                print(f"{layer.name}: tile {i}/{len(tiles)}",flush=True)
    partial.replace(output)
    meta.update(status="complete",file=str(output.relative_to(Path(cfg["_root"]))),sha256=file_hash(output),tile_count=len(tiles))
    write_json(state,meta)
    return meta
