"""Historical OSM vectors and published Maus v2 mining polygons."""
from __future__ import annotations
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, Point
from src.config import Config, write_json
from src.data.exporting import area_geometry, file_hash


def _root(cfg: Config) -> Path:
    root=Path(cfg["_root"])/cfg["collection"]["raw_directory"]
    root.mkdir(parents=True,exist_ok=True)
    return root


def _save(frame: gpd.GeoDataFrame, name: str, cfg: Config, metadata: dict[str,Any]) -> None:
    """Save only AOI intersections in the common projected CRS; empty results stay explicit."""
    _,utm,_=area_geometry(cfg)
    frame=frame.to_crs(cfg["study_area"]["crs"])
    if not frame.empty:
        frame=frame.loc[frame.intersects(utm)].copy()
        frame.geometry=frame.geometry.intersection(utm)
        frame=frame.loc[~frame.geometry.is_empty].copy()
    directory=_root(cfg)/name;directory.mkdir(parents=True,exist_ok=True)
    path=directory/(name+".gpkg")
    frame.to_file(path,driver="GPKG",layer=name,index=False)
    metadata.update(name=name,status="complete",feature_count=len(frame),output_crs=cfg["study_area"]["crs"],
                    file=str(path.relative_to(Path(cfg["_root"]))),sha256=file_hash(path),
                    acquired_utc=datetime.now(timezone.utc).isoformat())
    write_json(directory/"metadata.json",metadata)
    print(f"SAVED {name}: {len(frame)} features",flush=True)


def collect_osm(cfg: Config) -> None:
    """Query attic snapshots in bounded boxes; current OSM is never silently substituted."""
    s=cfg["collection"]["osm"]
    geo,_,_=area_geometry(cfg)
    west,south,east,north=geo.bounds
    step=s["tile_degrees"]
    cache=_root(cfg)/"osm_queries";cache.mkdir(parents=True,exist_ok=True)
    preferred_endpoint=cfg["networking"]["overpass_primary"]
    for kind in ("roads","settlements"):
        elements={};queries=[]
        for row in range(math.ceil((north-south)/step)):
            for col in range(math.ceil((east-west)/step)):
                bounds=(south+row*step,west+col*step,min(north,south+(row+1)*step),min(east,west+(col+1)*step))
                bbox=",".join(map(str,bounds))
                selector=f'way["highway"]({bbox});out geom;' if kind=="roads" else f'nwr["place"~"^({"|".join(s["place_types"])})$"]({bbox});out center;'
                query=f'[out:json][timeout:{s["timeout_seconds"]}][date:"{s["snapshot"]}"];'+selector
                import hashlib
                key=hashlib.sha256(query.encode()).hexdigest()[:16]
                path=cache/f"{kind}_{key}.json"
                if path.exists():result=json.loads(path.read_text(encoding="utf-8"))
                else:
                    result=None
                    for endpoint in dict.fromkeys([preferred_endpoint,cfg["networking"]["overpass_primary"]]+s["endpoints"]):
                        try:
                            response=requests.post(endpoint,data={"data":query},headers={"User-Agent":s["user_agent"]},timeout=s["timeout_seconds"]+30)
                            response.raise_for_status();candidate=response.json()
                            if candidate.get("remark") or "elements" not in candidate: raise ValueError("Overpass returned an incomplete response")
                            result=candidate;preferred_endpoint=endpoint;write_json(path,result);break
                        except (requests.RequestException,ValueError) as error:
                            print(f"Overpass {endpoint}: {type(error).__name__}: {str(error)[:180]}",flush=True)
                            time.sleep(cfg["collection"]["retry_backoff_seconds"])
                    if result is None: raise RuntimeError(f"All Overpass endpoints failed for {kind} tile {row},{col}; no empty layer fabricated")
                queries.append({"query":query,"response_sha256":file_hash(path)})
                for item in result["elements"]:elements[(item["type"],item["id"])]=item
                print(f"OSM {kind} tile {row},{col}: {len(result['elements'])} elements",flush=True)
        records=[]
        for (typ,ident),item in elements.items():
            if kind=="roads":
                coords=[(p["lon"],p["lat"]) for p in item.get("geometry",[]) if "lon" in p]
                if len(coords)<2: continue
                geometry=LineString(coords)
            else:
                point=item if "lon" in item else item.get("center")
                if point is None:raise ValueError("Settlement without coordinates")
                geometry=Point(point["lon"],point["lat"])
            records.append({"osm_id":f"{typ}/{ident}","tags_json":json.dumps(item.get("tags",{})),"geometry":geometry})
        frame=gpd.GeoDataFrame(records,columns=["osm_id","tags_json","geometry"],geometry="geometry",crs=4326)
        _save(frame,kind,cfg,{"source":"OpenStreetMap via Overpass attic","version":s["snapshot"],"start":s["snapshot"],"end":s["snapshot"],
                            "native_crs":"EPSG:4326","resolution":"vector; variable completeness/positional accuracy","license":"ODbL 1.0; Ãƒâ€šÃ‚Â© OpenStreetMap contributors",
                            "predictor_allowed":int(s["snapshot"][:4])<=cfg["time"]["prediction_start_year"],"queries":queries,
                            "notes":"Snapshot records mapped knowledge at that date, not construction dates. Roads are highway-tagged ways; settlement ways/relations are represented by centres. Incomplete rural coverage is possible."})


def collect_mining(cfg: Config) -> None:
    """Use the original published polygons, preserve the archive and clip to the AOI."""
    settings=cfg["collection"]["mining"]
    archive=_root(cfg)/"mining_source.gpkg"
    if not archive.exists():
        response=requests.get(settings["url"],timeout=cfg["collection"]["http_timeout_seconds"])
        response.raise_for_status()
        if not response.content.startswith(b"SQLite format 3"):raise ValueError("Mining download is not a GeoPackage")
        temp=archive.with_suffix(".partial");temp.write_bytes(response.content);temp.replace(archive)
    geo,_,_=area_geometry(cfg)
    frame=gpd.read_file(archive,bbox=geo.bounds)
    if frame.crs is None: raise ValueError("Mining source lacks CRS")
    _save(frame,"mining",cfg,{"source":settings["url"],"source_sha256":file_hash(archive),"version":settings["version"],
         "start":"2019-01-01","end":"2019-12-31","publication_year":2022,"native_crs":frame.crs.to_string(),
         "resolution":"polygons manually digitized primarily against 10 m Sentinel-2 imagery","license":"CC-BY-SA-4.0",
         "predictor_allowed":False,"notes":"Maus et al. v2 uses 2019 primary imagery plus undated Google/Bing supporting imagery. Mapping was restricted around known mine coordinates; India coverage is not exhaustive, especially unlisted small/artisanal quarries. Empty AOI intersection is not evidence of no mining. Historical predictor use blocked until temporal provenance is reviewed."})
