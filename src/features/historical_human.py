"""Pre-cutoff GHSL population and explicitly incomplete OSM quarry proxies."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import geopandas as gpd
import requests
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import polygonize, unary_union
from src.config import Config, load_config, write_json
from src.data.exporting import area_geometry, export_layer, file_hash
from src.data.gee_init import initialize
from src.data.layers import Layer
from src.data.vectors import _save


def population(cfg: Config) -> None:
    s = cfg["preprocessing"]["population_archive"]
    if s["observation_end_year"] > cfg["time"]["prediction_start_year"]: raise ValueError("Population vintage exceeds T")
    ee = initialize(cfg)
    c = copy.deepcopy(cfg); c["collection"]["raw_directory"] = cfg["preprocessing"]["input_directory"]
    source = ee.Image(s["asset"]).select("population_count")
    density = source.divide(ee.Image.pixelArea().reproject(source.projection())).multiply(1e6).rename("population_per_km2")
    layer = Layer("population_ghsl_2015",density,["population_per_km2"],s["export_scale_m"],s["asset"],
                  f"{s['epoch']}-01-01",f"{s['epoch']}-12-31",["people/km2"],True,
                  "GHSL P2016 epoch 2015, native 250m World Mollweide population count converted to density. Not 2020 population; no trend extrapolation. EC JRC open reuse with acknowledgement.",
                  {"observation_end_year":s["observation_end_year"],"epoch":s["epoch"]})
    meta = export_layer(ee,layer,c)
    approved = meta | {"units":"people/km2","observation_end_year":s["observation_end_year"],"epoch":s["epoch"]}
    write_json(Path(cfg["_root"])/cfg["preprocessing"]["vetted_population"]["metadata"],approved)


def quarry_geometry(item: dict) -> object:
    """Assemble complete OSM outer/inner rings; fail rather than drop relations."""
    def coordinates(element: dict) -> list[tuple[float,float]]:
        points = element.get("geometry",[])
        if not points or any("lon" not in x for x in points): raise ValueError("Incomplete OSM quarry geometry")
        return [(x["lon"],x["lat"]) for x in points]
    if item["type"] == "node": return Point(item["lon"],item["lat"])
    if item["type"] == "way":
        coords = coordinates(item)
        if len(coords) < 4 or coords[0] != coords[-1]: raise ValueError("Quarry way is not a closed polygon")
        return Polygon(coords)
    outers,inners = [],[]
    for member in item.get("members",[]):
        if member["type"] != "way": continue
        line = LineString(coordinates(member))
        if member.get("role","") in ("outer",""): outers.append(line)
        elif member["role"] == "inner": inners.append(line)
    outer = unary_union(list(polygonize(unary_union(outers))))
    if outer.is_empty: raise ValueError("Quarry relation has no complete outer rings")
    return outer.difference(unary_union(list(polygonize(unary_union(inners))))) if inners else outer


def mining(cfg: Config) -> None:
    s = cfg["collection"]["osm"]
    proxy = cfg["preprocessing"]["mining_proxy"]
    if int(s["snapshot"][:4]) > cfg["time"]["prediction_start_year"]: raise ValueError("Quarry snapshot exceeds T")
    geo,_,_ = area_geometry(cfg)
    west,south,east,north = geo.bounds
    query = f'[out:json][timeout:{s["timeout_seconds"]}][date:"{s["snapshot"]}"];nwr["{proxy["tag_key"]}"="{proxy["tag_value"]}"]({south},{west},{north},{east});out geom;'
    directory = Path(cfg["_root"])/cfg["preprocessing"]["input_directory"]/"mining_osm_2020"
    directory.mkdir(parents=True,exist_ok=True)
    cache = directory/(hashlib.sha256(query.encode()).hexdigest()+".json")
    if cache.exists(): result = json.loads(cache.read_text())
    else:
        response = requests.post(cfg["networking"]["overpass_primary"],data={"data":query},headers={"User-Agent":s["user_agent"]},timeout=s["timeout_seconds"]+30)
        response.raise_for_status(); result = response.json()
        if result.get("remark") or "elements" not in result: raise ValueError("Incomplete Overpass response")
        write_json(cache,result)
    records = [{"osm_id":f"{item['type']}/{item['id']}","tags_json":json.dumps(item.get("tags",{})),"geometry":quarry_geometry(item)} for item in result["elements"]]
    frame = gpd.GeoDataFrame(records,columns=["osm_id","tags_json","geometry"],geometry="geometry",crs=4326)
    if not frame.is_valid.all(): raise ValueError("Invalid quarry geometry")
    c = copy.deepcopy(cfg); c["collection"]["raw_directory"] = cfg["preprocessing"]["input_directory"]
    _save(frame,"mining_osm_2020",c,{"source":proxy["source"],"query":query,"response_sha256":file_hash(cache),"version":s["snapshot"],
          "observation_end_year":int(s["snapshot"][:4]),"predictor_allowed":True,"start":s["snapshot"],"end":s["snapshot"],
          "license":"ODbL 1.0; OpenStreetMap contributors","units":"mapped quarry polygons/points",
          "notes":"Incomplete proxy: OSM landuse=quarry at T; excludes unmapped mines and underground sites. Mining area is mapped quarry footprint only; zero is mapped absence, not verified absence."})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config",default="config.yaml")
    parser.add_argument("--source",choices=["population","mining","all"],default="all")
    args = parser.parse_args(); cfg = load_config(args.config)
    if args.source in ("population","all"): population(cfg)
    if args.source in ("mining","all"): mining(cfg)

if __name__ == "__main__": main()
