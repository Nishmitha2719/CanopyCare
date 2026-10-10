"""Collect configured AOI layers: python -m src.data.collect [--only sentinel2]."""
from __future__ import annotations
import argparse
from pathlib import Path
from shapely.geometry import mapping
from src.utils import load_config, DEFAULT_CONFIG
from src.data.gee_init import initialize
from src.data.exporting import area_geometry, export_layer
from src.data import layers
from src.config import write_json


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",default=str(DEFAULT_CONFIG))
    parser.add_argument("--only",choices=["all","sentinel2","hansen","dem","rainfall","climate","biomass","population","vectors"],default="all")
    parser.add_argument("--mode",choices=["local","drive"],default="local")
    args=parser.parse_args();cfg=load_config(args.config)
    root=Path(cfg["_root"])/cfg["collection"]["raw_directory"]
    failures=[]
    if args.only in ("all","vectors"):
        from src.data.vectors import collect_osm, collect_mining
        for func in (collect_osm,collect_mining):
            try: func(cfg)
            except Exception as error:
                failures.append({"layer":func.__name__,"error":str(error)[:1000]})
                print(f"FAILED {func.__name__}: {type(error).__name__}",flush=True)
    if args.only != "vectors":
        ee=initialize(cfg);ee.data.setDeadline(cfg["collection"]["ee_deadline_ms"])
        geo,_,_=area_geometry(cfg)
        aoi=ee.Geometry(mapping(geo),proj="EPSG:4326",geodesic=False)
        jobs=[]
        for name in ("hansen","dem","biomass"):
            if args.only in ("all",name):jobs.append((name,lambda n=name:getattr(layers,n)(ee,cfg)))
        if args.only in ("all","population"):jobs.append(("population",lambda:layers.population(ee,aoi,cfg)))
        for name in ("rainfall","climate","sentinel2"):
            if args.only in ("all",name):
                for year in cfg["collection"]["years"]:
                    jobs.append((f"{name}_{year}",lambda n=name,y=year:getattr(layers,n)(ee,aoi,cfg,y)))
        for name,build in jobs:
            try:
                print(f"BUILD {name}",flush=True)
                export_layer(ee,build(),cfg,args.mode)
            except Exception as error:
                failures.append({"layer":name,"error":str(error)[:1000]})
                print(f"FAILED {name}: {type(error).__name__}: {str(error)[:250]}",flush=True)
    write_json(root/f"failures_{args.only}.json",failures)
    print(f"Collection finished with {len(failures)} failures; Drive submissions are not local completion.",flush=True)
    return bool(failures)

if __name__=="__main__":raise SystemExit(main())
