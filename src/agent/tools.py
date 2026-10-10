"""A narrow tool surface: inspect evidence and prepare recommendations only."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pandas as pd
from src.config import Config, fingerprint, resolve
from src.data.provenance import sha256

TOOLS = [
    {"type": "function", "function": {"name": "get_cell", "description": "Inspect one cell and its held-out score.",
     "parameters": {"type": "object", "properties": {"cell_id": {"type": "string"}}, "required": ["cell_id"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "prioritize", "description": "List highest scored cells for human review.",
     "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1}}, "required": ["limit"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_validation", "description": "Read held-out validation and limitations.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
]


class EvidenceTools:
    """Verified local report access, without file-path or command tools."""
    def __init__(self, cfg: Config):
        self.cfg = cfg
        root = resolve(cfg, "reports")
        self.report = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
        if self.report["config_sha256"] != fingerprint(cfg):
            raise ValueError("Report configuration is stale; retrain before reviewing")
        if self.report["prediction_sha256"] != sha256(root / "predictions.csv"):
            raise ValueError("Predictions do not match the validated run")
        self.frame = pd.read_csv(root / "predictions.csv")

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch strict allowlisted tools; refuse arbitrary paths or actions."""
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        if name == "get_validation" and not arguments:
            return {k: self.report[k] for k in ("data_mode", "pooled_oof", "interpretation", "limitations")}
        if name == "get_cell" and set(arguments) == {"cell_id"}:
            found = self.frame.loc[self.frame.cell_id == arguments["cell_id"]]
            if len(found) != 1:
                raise ValueError("Unknown cell ID")
            return {"cell": found.iloc[0].to_dict(), "status": "requires_human_review",
                    "interpretation": self.report["interpretation"]}
        if name == "prioritize" and set(arguments) == {"limit"}:
            limit = arguments["limit"]
            if type(limit) is not int or not 1 <= limit <= self.cfg["agent"]["max_priority_cells"]:
                raise ValueError("Invalid priority limit")
            fields = ["cell_id", "risk_score_oof", "flag_for_review", "data_mode"]
            return {"cells": self.frame.nlargest(limit, "risk_score_oof")[fields].to_dict(orient="records"),
                    "status": "requires_human_review", "recommendation": "Review imagery and local context before any intervention.",
                    "interpretation": self.report["interpretation"]}
        raise ValueError("Unknown tool or invalid arguments")
