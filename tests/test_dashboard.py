"""Optional Streamlit test with isolated synthetic artifacts, independent of workspace reports."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Install the dashboard extra")
class Dashboard(unittest.TestCase):
    def test_demo_review_controls(self) -> None:
        import yaml
        from streamlit.testing.v1 import AppTest
        from src.config import load_config, public_config
        from src.data.demo import make_demo
        from src.data.provenance import save_dataset
        from src.models.train import train
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            cfg = load_config(root / "config.yaml")
            cfg["_root"] = directory
            path = Path(directory)/"config.yaml"
            path.write_text(yaml.safe_dump(public_config(cfg)),encoding="utf-8")
            save_dataset(make_demo(cfg),cfg,"synthetic")
            train(cfg)
            with patch("sys.argv",["app.py","--config",str(path)]):
                app = AppTest.from_file(str(root / "src/dashboard/app.py")).run(timeout=30)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.metric),4)
                self.assertEqual(len(app.selectbox),2)
                app.selectbox[0].select(app.selectbox[0].options[1]).run()
                self.assertFalse(app.exception)
