"""Projected full-square grids with stable row-major cell identifiers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.config import Config


def make_grid(cfg: Config) -> Any:
    """Return a GeoDataFrame; geographic inputs are projected before gridding."""
    import geopandas as gpd
    from pyproj import CRS
    from shapely.geometry import box

    area = cfg["study_area"]
    crs = CRS.from_user_input(area["crs"])
    if not crs.is_projected or any(a.unit_name != "metre" for a in crs.axis_info):
        raise ValueError("Grid CRS must be projected in metres")
    if area["shapefile"]:
        region = gpd.read_file(Path(cfg["_root"]) / area["shapefile"])
        if region.crs is None:
            raise ValueError("Study-area file must declare a CRS")
    else:
        region = gpd.GeoDataFrame(geometry=[box(*area["bbox_wgs84"])], crs="EPSG:4326")
    region = region.to_crs(crs)
    if region.empty or not region.is_valid.all():
        raise ValueError("Study-area geometry is empty or invalid")
    footprint = region.geometry.union_all()
    if footprint.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Study area must contain polygons")
    size = cfg["grid"]["cell_size_m"]
    xmin, ymin, xmax, ymax = region.total_bounds
    squares = [box(x, y, x + size, y + size)
               for y in np.arange(np.floor(ymin / size) * size, ymax, size)
               for x in np.arange(np.floor(xmin / size) * size, xmax, size)
               if box(x, y, x + size, y + size).intersection(footprint).area > 0]
    grid = gpd.GeoDataFrame({"cell_id": [f"N{i+1:04d}" for i in range(len(squares))]},
                            geometry=squares, crs=crs)
    grid["x_m"] = grid.geometry.centroid.x
    grid["y_m"] = grid.geometry.centroid.y
    grid["area_ha"] = grid.geometry.area / 10000
    return grid
