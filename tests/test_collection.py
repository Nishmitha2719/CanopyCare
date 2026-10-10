"""Collection contract tests independent of live cloud services."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
import numpy as np
from src.utils import load_config
from src.data.exporting import raster_layout, area_geometry
from src.data.inspect_collection import expected_names
from src.data.layers import hansen, biomass
from unittest.mock import MagicMock


class CollectionContracts(unittest.TestCase):
    def test_grid_anchor_and_coverage(self):
        bounds=(578321.3,1289011.4,639482.9,1368123.1)
        origins=[]
        for scale in (20,30,100,1000):
            transform,width,height=raster_layout(bounds,scale,3000)
            self.assertLessEqual(transform.c,bounds[0])
            self.assertGreaterEqual(transform.f,bounds[3])
            self.assertGreaterEqual(transform.c+width*scale,bounds[2])
            self.assertLessEqual(transform.f-height*scale,bounds[1])
            self.assertEqual(transform.a,scale)
            self.assertEqual(transform.e,-scale)
            origins.append((transform.c,transform.f))
        self.assertEqual(len(set(origins)),1)

    def test_tile_byte_limit(self):
        cfg=load_config()
        count=len(cfg["collection"]["sentinel2"]["bands"])+1
        self.assertLess(cfg["collection"]["tile_pixels"]**2*4*count,32*1024*1024)

    def test_required_layer_inventory(self):
        names=expected_names(load_config())
        self.assertEqual(len(names),25)
        self.assertEqual(len(names),len(set(names)))
        self.assertIn("sentinel2_2024",names)
        self.assertIn("settlements",names)

    def test_post_cutoff_products_blocked(self):
        cfg=load_config();ee=MagicMock()
        self.assertFalse(hansen(ee,cfg).predictor_allowed)
        self.assertFalse(biomass(ee,cfg).predictor_allowed)
        self.assertGreater(int(biomass(ee,cfg).end[:4]),cfg["time"]["prediction_start_year"])

    def test_aoi_round_trip(self):
        from pyproj import Transformer
        cfg=load_config();geo,utm,bounds=area_geometry(cfg)
        self.assertTrue(geo.is_valid and utm.is_valid)
        self.assertGreater(utm.area,0)
        transformer=Transformer.from_crs(cfg["study_area"]["crs"],4326,always_xy=True)
        lon,lat=transformer.transform(utm.centroid.x,utm.centroid.y)
        self.assertTrue(geo.contains(__import__("shapely").geometry.Point(lon,lat)))

    def test_historical_osm_snapshot(self):
        cfg=load_config()
        self.assertLessEqual(int(cfg["collection"]["osm"]["snapshot"][:4]),cfg["time"]["prediction_start_year"])
