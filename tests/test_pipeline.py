"""Scientific-integrity regression checks, runnable without pytest."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from src.config import load_config, resolve
from src.data.demo import make_demo
from src.data.provenance import save_dataset, load_dataset
from src.features.validation import validate
from src.models.spatial import spatial_splits
from src.models.estimators import fit_model
from src.models.train import train
from src.agent.tools import EvidenceTools
from src.agent.loop import run_agent
from src.carbon.scenario import carbon_scenario

ROOT = Path(__file__).resolve().parents[1]


class Contracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.cfg = load_config(ROOT / "config.yaml")
        self.cfg["_root"] = self.temp.name
        self.frame = make_demo(self.cfg)
        save_dataset(self.frame, self.cfg, "synthetic")
        self.frame, self.meta = load_dataset(self.cfg)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_future_feature_rejected(self) -> None:
        self.meta["features"]["forest_fraction"]["observation_end_year"] += 1
        with self.assertRaisesRegex(ValueError, "past T"):
            validate(self.frame, self.meta, self.cfg)

    def test_future_dataset_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg.pop("_root")
        cfg["time"]["feature_dataset_end_year"] += 1
        import yaml
        path = Path(self.temp.name) / "invalid.yaml"
        path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "release must end at T"):
            load_config(path)

    def test_tampered_dataset_rejected(self) -> None:
        with resolve(self.cfg, "dataset").open("a") as output:
            output.write("\n")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            load_dataset(self.cfg)

    def test_changed_science_requires_reextraction(self) -> None:
        self.cfg["forest"]["canopy_threshold_pct"] = 40
        with self.assertRaisesRegex(ValueError, "mismatch"):
            load_dataset(self.cfg)

    def test_target_threshold_checked(self) -> None:
        self.frame.loc[0, "target"] = 1 - self.frame.loc[0, "target"]
        with self.assertRaisesRegex(ValueError, "Targets disagree"):
            validate(self.frame, self.meta, self.cfg)

    def test_missing_predictor_rejected(self) -> None:
        self.frame.loc[0, "elevation_m"] = np.nan
        with self.assertRaisesRegex(ValueError, "non-finite"):
            validate(self.frame, self.meta, self.cfg)

    def test_boundary_threshold_inclusive(self) -> None:
        self.frame.loc[0, "future_loss_fraction"] = self.cfg["forest"]["loss_threshold_fraction"]
        self.frame.loc[0, "target"] = 1
        self.assertEqual(validate(self.frame, self.meta, self.cfg).loc[0, "target"], 1)

    def test_spatial_folds_buffer_and_coverage(self) -> None:
        seen = []
        xy = self.frame[["x_m", "y_m"]].to_numpy()
        blocks = np.floor(xy / self.cfg["validation"]["block_size_m"])
        splits = list(spatial_splits(self.frame, self.cfg))
        again = list(spatial_splits(self.frame, self.cfg))
        for (tr, te), (tr2, te2) in zip(splits, again):
            self.assertFalse(set(map(tuple, blocks[tr])) & set(map(tuple, blocks[te])))
            self.assertGreater(cKDTree(xy[te]).query(xy[tr])[0].min(), self.cfg["validation"]["buffer_m"])
            np.testing.assert_array_equal(tr, tr2)
            np.testing.assert_array_equal(te, te2)
            seen.extend(te)
        self.assertEqual(sorted(seen), list(range(len(self.frame))))

    def test_preprocessing_fitted_to_training_only(self) -> None:
        tr, te = next(spatial_splits(self.frame, self.cfg))
        x = self.frame[self.cfg["features"]["columns"]].to_numpy()
        x[te] += 99999
        model = fit_model(x[tr], self.frame.target.to_numpy()[tr], self.frame[["x_m", "y_m"]].to_numpy()[tr], self.cfg)
        np.testing.assert_allclose(model.named_steps["standardscaler"].mean_, x[tr].mean(axis=0))

    def test_carbon_does_not_multiply_binary_probability(self) -> None:
        first = carbon_scenario(self.frame, self.cfg)
        changed = self.frame.assign(risk_score_oof=0.999)
        np.testing.assert_array_equal(first, carbon_scenario(changed, self.cfg))

    def test_demo_reproducible(self) -> None:
        np.testing.assert_array_equal(make_demo(self.cfg), make_demo(self.cfg))


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.cfg = load_config(ROOT / "config.yaml")
        cls.cfg["_root"] = cls.temp.name
        save_dataset(make_demo(cls.cfg), cls.cfg, "synthetic")
        cls.report = train(cls.cfg)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_end_to_end_metrics_and_artifacts(self) -> None:
        for name in ("pr_auc", "average_precision", "recall", "f1", "roc_auc"):
            self.assertTrue(0 <= self.report["pooled_oof"][name] <= 1)
        self.assertEqual(self.report["n_eligible"], 900)
        self.assertEqual(len(self.report["folds"]), 4)
        self.assertTrue((resolve(self.cfg, "reports") / "model.joblib").exists())

    def test_tool_allowlist(self) -> None:
        tools = EvidenceTools(self.cfg)
        for name, args in [("delete_file", {"path": "x"}), ("prioritize", {"limit": 999}),
                           ("get_cell", {"cell_id": "N0001", "command": "x"})]:
            with self.assertRaises(ValueError):
                tools.call(name, args)
        result = tools.call("prioritize", {"limit": 3})
        self.assertEqual(len(result["cells"]), 3)
        self.assertEqual(result["status"], "requires_human_review")

    def test_agent_tool_cycle(self) -> None:
        responses = iter([
            {"role": "assistant", "tool_calls": [{"function": {"name": "get_cell", "arguments": {"cell_id": "N0001"}}}]},
            {"role": "assistant", "content": "Review N0001 imagery; a human decides."},
        ])
        result = run_agent("Inspect N0001", self.cfg, lambda messages, tools: next(responses))
        self.assertEqual(result["status"], "requires_human_review")
        self.assertEqual(result["audit"][-1]["name"], "get_cell")

    def test_agent_loop_is_bounded(self) -> None:
        def endless(messages, tools):
            return {"tool_calls": [{"function": {"name": "get_validation", "arguments": {}}}]}
        result = run_agent("Repeat", self.cfg, endless)
        self.assertIn("budget reached", result["draft"])
        self.assertEqual(len(result["audit"]), self.cfg["agent"]["max_tool_rounds"] + 1)


if __name__ == "__main__":
    unittest.main()
