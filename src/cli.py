"""Command-line entry point for the reproducible CanopyCare workflow."""
from __future__ import annotations
import argparse
import json
from src.config import load_config, resolve, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Generate synthetic data and run complete training")
    sub.add_parser("extract", help="Extract real Earth Engine data with configured account")
    sub.add_parser("train", help="Validate and train on extracted/generated data")
    review = sub.add_parser("recommend", help="Create a deterministic human-review shortlist")
    review.add_argument("--limit", type=int, default=5)
    agent = sub.add_parser("agent", help="Use a configured local tool-capable Ollama model")
    agent.add_argument("--question", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.command in ("demo", "extract"):
        from src.data.provenance import save_dataset
        if args.command == "demo":
            from src.data.demo import make_demo
            frame, mode = make_demo(cfg), "synthetic"
        else:
            from src.data.earth_engine import extract
            frame, mode = extract(cfg), "earth_engine"
        save_dataset(frame, cfg, mode)
        print(f"Saved {len(frame)} {mode} cells to {resolve(cfg, 'dataset')}")
    if args.command in ("train", "demo"):
        from src.models.train import train
        report = train(cfg)
        print(json.dumps({"data_mode": report["data_mode"], "model": report["model"],
                          "pooled_oof": report["pooled_oof"], "reports": str(resolve(cfg, "reports"))}, indent=2))
    if args.command == "recommend":
        from src.agent.tools import EvidenceTools
        print(json.dumps(EvidenceTools(cfg).call("prioritize", {"limit": args.limit}), indent=2))
    if args.command == "agent":
        from src.agent.loop import ollama_completion, run_agent
        result = run_agent(args.question, cfg, ollama_completion(cfg))
        write_json(resolve(cfg, "reports") / "agent_review.json", result)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
