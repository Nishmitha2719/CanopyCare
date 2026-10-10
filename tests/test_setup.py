"""Offline setup checks; only the explicitly enabled integration test contacts GEE."""
import os
import random
import unittest
from unittest.mock import MagicMock, patch, call
import numpy as np
from src.utils import load_config, get_logger, set_seed, projected_crs, utm_epsg, transform_xy, study_area_path
from src.data.gee_init import initialize, project_id, smoke_test


class Setup(unittest.TestCase):
    def test_config_and_area(self):
        cfg = load_config()
        self.assertTrue(study_area_path(cfg).is_file())
        self.assertEqual(cfg["carbon"]["carbon_fraction"], 0.47)
        self.assertEqual(cfg["grid"]["cell_size_m"], 1000)

    def test_seeds_repeat(self):
        set_seed(42)
        first = (random.random(), np.random.random())
        set_seed(42)
        self.assertEqual(first, (random.random(), np.random.random()))

    def test_logger_idempotent(self):
        logger = get_logger("test.canopycare")
        self.assertIs(logger, get_logger("test.canopycare"))
        self.assertEqual(len(logger.handlers), 1)

    def test_crs(self):
        self.assertEqual(utm_epsg(75.8, 12.0), 32643)
        self.assertEqual(projected_crs("EPSG:32643").to_epsg(), 32643)
        with self.assertRaises(ValueError):
            projected_crs("EPSG:4326")
        x,y = transform_xy(75.8, 12, "EPSG:4326", "EPSG:32643")
        lon,lat = transform_xy(x,y,"EPSG:32643","EPSG:4326")
        self.assertAlmostEqual(lon,75.8,places=7)
        self.assertAlmostEqual(lat,12,places=7)

    @patch.dict(os.environ, {}, clear=True)
    def test_project_required(self):
        cfg=load_config()
        cfg["earth_engine"]["project"]=None
        with self.assertRaises(ValueError):
            project_id(cfg)
        self.assertEqual(project_id(cfg,"explicit-project"),"explicit-project")

    def test_initialization_contract_offline(self):
        client=MagicMock()
        with patch.dict("sys.modules", {"ee":client}):
            self.assertIs(initialize(load_config(),project="test-project"),client)
        client.Authenticate.assert_not_called()
        client.Initialize.assert_called_once_with(project="test-project")
        self.assertEqual(client.mock_calls, [call.Initialize(project="test-project"), call.data.setDeadline(60000)])

    def test_smoke_checks_server_value_offline(self):
        client=MagicMock()
        client.Number.return_value.add.return_value.getInfo.return_value=2
        self.assertTrue(smoke_test(client)["initialized"])
        client.Number.return_value.add.return_value.getInfo.return_value=3
        with self.assertRaises(RuntimeError):
            smoke_test(client)


@unittest.skipUnless(os.environ.get("CANOPYCARE_RUN_GEE_TEST") == "1", "Live GEE test requires explicit opt-in and credentials")
class LiveEarthEngine(unittest.TestCase):
    def test_real_server(self):
        self.assertEqual(smoke_test(initialize(load_config()))["server_result"], 2)
