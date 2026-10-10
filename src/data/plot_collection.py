"""Local-only sanity figures for every collected layer, without remote map services."""
from __future__ import annotations
import json
import math
from pathlib import Path
from collections.abc import Iterator
from typing import Any
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from src.config import Config
from src.data.exporting import area_geometry
from src.data.inspect_collection import expected_names


def figures(cfg: Config) -> Iterator[tuple[str, Any]]:
    """Plot each band with the actual AOI outline; preserve nodata and empty vectors."""
    root=Path(cfg["_root"])
    geo,utm,_=area_geometry(cfg)
    outline=gpd.GeoSeries([utm],crs=cfg["study_area"]["crs"])
    maximum=cfg["collection"]["quality"]["preview_max_pixels"]
    for name in expected_names(cfg):
        meta=json.loads((root/cfg["collection"]["raw_directory"]/name/"metadata.json").read_text())
        path=root/meta["file"]
        if path.suffix==".tif":
            with rasterio.open(path) as src:
                ratio=min(1,maximum/max(src.width,src.height))
                data=src.read(out_shape=(src.count,max(1,round(src.height*ratio)),max(1,round(src.width*ratio))),
                              masked=True,resampling=Resampling.nearest)
                columns=min(3,src.count);rows=math.ceil(src.count/columns)
                fig,axes=plt.subplots(rows,columns,figsize=(5*columns,4.5*rows),squeeze=False)
                for i,ax in enumerate(axes.flat):
                    if i>=src.count:ax.set_visible(False);continue
                    values=data[i].compressed()
                    low,high=np.quantile(values,[0.02,0.98]) if len(values) else (0,1)
                    if high<=low:high=low+1
                    categorical=src.descriptions[i] in ("loss","gain","lossyear","datamask","QF")
                    if categorical and len(values):
                        low,high=float(values.min()),float(values.max())
                        if high<=low:high=low+1
                    cmap="twilight" if src.descriptions[i]=="aspect" else "viridis"
                    im=ax.imshow(data[i],extent=[src.bounds.left,src.bounds.right,src.bounds.bottom,src.bounds.top],
                                 origin="upper",cmap=cmap,vmin=low,vmax=high)
                    outline.boundary.plot(ax=ax,color="red",linewidth=0.6)
                    ax.set_title(src.descriptions[i]);ax.set_xlabel("Easting (m)");ax.set_ylabel("Northing (m)")
                    bar=fig.colorbar(im,ax=ax,shrink=0.7,label=meta["units"][i])
                    if categorical and len(values):
                        unique=np.unique(values)
                        bar.set_ticks(unique if len(unique)<=8 else np.unique(np.linspace(unique.min(),unique.max(),6).astype(int)))
        else:
            frame=gpd.read_file(path)
            fig,ax=plt.subplots(figsize=(7,8))
            outline.boundary.plot(ax=ax,color="red",linewidth=1)
            if not frame.empty:frame.plot(ax=ax,color="#225e49",linewidth=0.35,markersize=3)
            else:ax.text(0.5,0.5,"No source polygons intersect this AOI.\nThis does not prove real-world absence.",ha="center",transform=ax.transAxes)
            ax.set_xlabel("Easting (m)");ax.set_ylabel("Northing (m)")
        fig.suptitle(name+" | "+cfg["study_area"]["crs"]+" | historical predictor allowed: "+str(meta["predictor_allowed"]))
        credit=("© OpenStreetMap contributors | ODbL 1.0 | snapshot " + meta["version"] if name in ("roads","settlements")
                else "Maus et al. (2022) | CC-BY-SA-4.0" if name=="mining"
                else "Source: " + meta["source"] + " | License and citation: DATA_CATALOG.md")
        fig.text(0.5,0.005,credit,ha="center",fontsize=7)
        fig.tight_layout(rect=(0,0.025,1,1))
        yield name,fig
