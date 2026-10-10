"""Explicit GEE authentication, initialization, and real server smoke test."""
from __future__ import annotations
import argparse
import os
import sys
from typing import Any
from src.config import Config
from src.utils import DEFAULT_CONFIG, get_logger, load_config


def project_id(cfg: Config, override: str | None = None) -> str:
    """Resolve project from CLI, EE_PROJECT, then config; never infer an account."""
    value = override or os.environ.get("EE_PROJECT") or cfg["earth_engine"].get("project")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Set earth_engine.project, EE_PROJECT, or --project to your Earth Engine-enabled Cloud project ID")
    return value.strip()


def initialize(cfg: Config, *, project: str | None = None, authenticate: bool = False) -> Any:
    """Initialize GEE. Authentication is interactive only when explicitly requested."""
    selected = project_id(cfg, project)
    import ee
    if authenticate:
        ee.Authenticate(auth_mode="localhost")
    ee.Initialize(project=selected)
    ee.data.setDeadline(cfg["earth_engine"]["request_timeout_ms"])
    return ee


def smoke_test(client: Any) -> dict[str, Any]:
    """Force a server round trip; successful import or mocked init is insufficient."""
    value = client.Number(1).add(1).getInfo()
    if value != 2:
        raise RuntimeError(f"GEE server smoke test returned an unexpected value: {value!r}")
    return {"initialized": True, "server_result": value}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--project")
    parser.add_argument("--authenticate", action="store_true", help="Open the local browser OAuth flow")
    args = parser.parse_args()
    logger = get_logger("canopycare.gee")
    try:
        cfg = load_config(args.config)
        client = initialize(cfg, project=args.project, authenticate=args.authenticate)
        result = smoke_test(client)
        logger.info("GEE initialized; real server smoke test passed: 1 + 1 = %s", result["server_result"])
        return 0
    except Exception as error:
        # OAuth tokens are never printed. Preserve exception type and return failure.
        logger.error("GEE setup failed (%s). Check project registration, permissions, and authentication.", type(error).__name__)
        if isinstance(error, (ValueError, ImportError)):
            logger.error("%s", error)
        logger.info("For first-time login run: python -m src.data.gee_init --project YOUR_PROJECT_ID --authenticate")
        return 1


if __name__ == "__main__":
    sys.exit(main())
