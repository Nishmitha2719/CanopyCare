"""Leakage, zonal, geometry and fold-preprocessing regression tests."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from shapely.geometry import box
from src.config import load_config
from src.features.temporal import history_masks, target_mask, audit_features
from src.features.zonal import Zones, spectral_indices, time_summary
from src.features.pipeline import Builder, validate_settings
from src.features.imputation import make_preprocessor, model_columns


class PreprocessingTests(unittest.TestCase):
    def test_future_lossyear_cannot_change_any_history_mask(self):
        cover = np.array([80,80,80,80,80,10,80],dtype=float)
        year = np.array([0,1,16,20,21,24,25],dtype=float)
        land = np.ones(7)
        expected = history_masks(cover,year,land,2020,30,[1,3,5])
        changed = year.copy(); changed[year > 20] = [22,99,23]
        actual = history_masks(cover,changed,land,2020,30,[1,3,5])
        for key in expected: np.testing.assert_array_equal(expected[key],actual[key])
        self.assertEqual(int(expected["cumulative"].sum()),3)
        self.assertEqual(int(expected["last_1"].sum()),1)
        self.assertEqual(int(expected["last_5"].sum()),2)

    def test_label_window_is_exact_and_cannot_resurrect_lost_forest(self):
        future,valid = target_mask(np.array([1,1,1,1,0],bool),np.array([20,21,24,25,22]),np.ones(5),2020,4)
        np.testing.assert_array_equal(future,[False,True,True,False,False])
        self.assertTrue(valid.all())

    def test_cutoff_audit_rejects_future_label_and_unapproved_sources(self):
        base = {"role":"predictor","predictor_allowed":True,"observation_end_year":2020,"status":"available"}
        audit_features({"safe":base},2020)
        for update in ({"observation_end_year":2021},{"role":"labels"},{"predictor_allowed":False},{"max_lossyear_used":2024}):
            with self.assertRaises(ValueError): audit_features({"unsafe":base|update},2020)

    def test_pixel_center_stats_and_missing_coverage(self):
        grid = gpd.GeoDataFrame(geometry=[box(0,0,1000,1000),box(1000,0,2000,1000)],crs=32643)
        with MemoryFile() as mem:
            with mem.open(driver="GTiff",height=2,width=4,count=1,dtype="float32",crs=32643,transform=from_origin(0,1000,500,500)) as raster:
                zones = Zones(grid,raster)
                values = np.array([[1,3,10,np.nan],[5,7,20,np.nan]],dtype=float)
                stats = zones.stats(values,.75)
                self.assertAlmostEqual(stats["mean"][0],4)
                self.assertAlmostEqual(stats["std"][0],np.sqrt(5))
                self.assertEqual(stats["max"][0],7)
                self.assertTrue(np.isnan(stats["mean"][1]))
                self.assertEqual(stats["coverage"][1],.5)

    def test_index_formula_and_undefined_denominator(self):
        cfg = load_config("config.yaml")
        bands = {b:np.array([v,0],dtype=float) for b,v in {"B2":.1,"B4":.2,"B8":.6,"B11":.3,"B12":.4}.items()}
        output = spectral_indices(bands,cfg["preprocessing"])
        self.assertAlmostEqual(output["ndvi"][0],.5)
        self.assertAlmostEqual(output["nbr"][0],.2)
        self.assertAlmostEqual(output["ndmi"][0],1/3)
        self.assertTrue(np.isnan(output["ndvi"][1]))

    def test_trend_real_spacing_and_insufficient_years(self):
        trend,anomaly,count = time_summary(np.array([[.1,.2,np.nan,.4],[np.nan,np.nan,.3,.4]]),[2017,2018,2019,2020],3)
        self.assertAlmostEqual(trend[0],.1)
        self.assertAlmostEqual(anomaly[0],.4-(.1+.2+.4)/3)
        self.assertTrue(np.isnan(trend[1])); self.assertTrue(np.isnan(anomaly[1]))
        self.assertEqual(count.tolist(),[3,2])

    def test_imputer_never_learns_from_held_out_extreme(self):
        preprocessing = make_preprocessor()
        train = pd.DataFrame({"x":[1.,3.,np.nan]})
        preprocessing.fit(train)
        self.assertEqual(preprocessing.named_steps["impute"].statistics_[0],2)
        preprocessing.transform(pd.DataFrame({"x":[100000.,np.nan]}))
        self.assertEqual(preprocessing.named_steps["impute"].statistics_[0],2)

    def test_model_allowlist_rejects_target(self):
        manifest = {"cutoff_year":2020,"features":{},"model_features":["y"],"label_columns":["y"]}
        with self.assertRaises(ValueError): model_columns(manifest)

    def test_grid_is_full_square_and_has_unique_ids(self):
        builder = Builder(load_config("config.yaml"))
        self.assertTrue(builder.grid.node_id.is_unique)
        self.assertFalse(builder.grid[["row","col"]].duplicated().any())
        np.testing.assert_allclose(builder.grid.geometry.area,1e6)
        self.assertTrue(builder.grid.centroid_lon.between(75,77).all())

    def test_invalid_season_config_fails(self):
        cfg = load_config("config.yaml"); cfg["preprocessing"]["wet_months"].append(4)
        with self.assertRaises(ValueError): validate_settings(cfg)


    def test_source_dependency_audit_catches_false_feature_date(self):
        meta = {"role":"predictor","predictor_allowed":True,"observation_end_year":2020,"status":"available","source":"future"}
        with self.assertRaises(ValueError):
            audit_features({"renamed_history":meta},2020,{"future":{"role":"predictor","observation_end_year":2024}})

    def test_biomass_subset_parser_rejects_truncation(self):
        from src.features.biomass_archive import parse_rows
        text = "[0][0], 10, 20\n[0][1], 30, 40\n"
        np.testing.assert_array_equal(parse_rows(text,2,2),[[10,20],[30,40]])
        with self.assertRaises(ValueError): parse_rows(text,3,2)
        with self.assertRaises(ValueError): parse_rows(text,2,3)

    def test_quarry_relation_retains_hole(self):
        from src.features.historical_human import quarry_geometry
        def member(points,role):
            return {"type":"way","role":role,"geometry":[{"lon":x,"lat":y} for x,y in points]}
        item = {"type":"relation","members":[member([(0,0),(4,0),(4,4),(0,4),(0,0)],"outer"),
                                              member([(1,1),(2,1),(2,2),(1,2),(1,1)],"inner")]}
        self.assertAlmostEqual(quarry_geometry(item).area,15)

    def test_future_label_perturbation_leaves_all_history_features_identical(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        import rasterio
        cfg = load_config("config.yaml")
        grid = gpd.GeoDataFrame({"node_id":["N0001","N0002"],"x_m":[500.,1500.],"y_m":[500.,500.]},
                                geometry=[box(0,0,1000,1000),box(1000,0,2000,1000)],crs=32643)
        with TemporaryDirectory(dir="reports") as directory:
            root = Path(directory)
            hist = np.array([[[80,80,80,80],[80,80,80,80]],[[0,20,0,0],[0,0,0,0]],[[1,1,1,1],[1,1,1,1]]],dtype="float32")
            label = np.array([[[0,20,0,0],[0,0,0,0]],[[1,1,1,1],[1,1,1,1]]],dtype="float32")
            def save(name,data):
                with rasterio.open(root/name,"w",driver="GTiff",width=4,height=2,count=len(data),dtype="float32",crs=32643,transform=from_origin(0,1000,500,500),nodata=-9999) as dst: dst.write(data)
            save("history.tif",hist); save("labels.tif",label)
            def extract():
                builder = Builder.__new__(Builder)
                builder.cfg = cfg; builder.p = cfg["preprocessing"]; builder.t = 2020
                builder.grid = grid; builder.frame = pd.DataFrame(grid.drop(columns="geometry"))
                builder.registry = {}; builder.sources = {}; builder.quality_columns = []
                builder.boundary_distance = np.full(2,10000.)
                with patch.object(builder,"source",side_effect=lambda name,**kwargs:(root/f"{name}.tif",{})):
                    builder.history()
                return builder.frame,list(builder.registry)
            before,features = extract()
            label[0,1,:] = 21; save("labels.tif",label)
            after,_ = extract()
            pd.testing.assert_frame_equal(before[features],after[features])
            self.assertFalse(before.y.equals(after.y))

    def test_saved_nodes_and_manifest_when_present(self):
        output = Path("data/processed/preprocessing")
        if not (output/"feature_manifest.json").exists(): self.skipTest("Run pipeline for artifact integration test")
        manifest = json.loads((output/"feature_manifest.json").read_text())
        audit_features(manifest["features"],manifest["cutoff_year"],manifest["sources"])
        nodes = pd.read_parquet(output/"forest_nodes.parquet")
        self.assertTrue(nodes.node_id.is_unique)
        self.assertTrue(nodes.y.isin([0,1]).all())
        self.assertTrue((nodes.forest_fraction_T >= manifest["config"]["forest"]["min_forest_fraction"]).all())
        self.assertTrue((nodes.y == (nodes.future_loss_fraction >= manifest["target_threshold"])).all())
        self.assertFalse(set(model_columns(manifest)) & set(manifest["label_columns"]))
        self.assertTrue((nodes.label_valid_forest_fraction == 1).all())
        self.assertFalse(np.isinf(nodes[model_columns(manifest)].to_numpy()).any())

if __name__ == "__main__": unittest.main()
