"""Run with: python -m streamlit run src/dashboard/app.py -- --config config.yaml."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
# Streamlit executes this file directly rather than as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
import plotly.express as px
import streamlit as st
from src.agent.tools import EvidenceTools
from src.config import load_config, resolve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args, _ = parser.parse_known_args()
    st.set_page_config(page_title="CanopyCare review", layout="wide")
    st.title("CanopyCare · forest-loss review")
    try:
        cfg = load_config(args.config)
        evidence = EvidenceTools(cfg)
    except (OSError, ValueError, KeyError) as error:
        st.error(f"Run the pipeline first: {error}")
        st.stop()
    report, frame = evidence.report, evidence.frame
    if report["data_mode"] == "synthetic":
        st.error("SYNTHETIC DEMO — these cells and scores are not ecological evidence.")
    st.info("Model associations only. Scores are uncalibrated. A human must review and decide.")
    t = cfg["time"]["prediction_start_year"]
    st.caption(f"Observations through {t}; target {t+1}–{t+cfg['time']['horizon_years']}. Buffered spatial out-of-fold evaluation.")
    columns = st.columns(4)
    for column, (label, key) in zip(columns, [("PR-AUC", "pr_auc"), ("Recall", "recall"), ("F1", "f1"), ("ROC-AUC", "roc_auc")]):
        column.metric(label, f"{report['pooled_oof'][key]:.3f}")
    fig = px.scatter(frame, x="x_m", y="y_m", color="risk_score_oof", hover_name="cell_id",
                     color_continuous_scale="YlOrRd", range_color=(0, 1),
                     labels={"x_m": "Easting (m)", "y_m": "Northing (m)", "risk_score_oof": "Held-out risk"})
    fig.update_traces(marker={"symbol": "square", "size": 9})
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Cell centroids in {cfg['study_area']['crs']}; boundary cells are full squares intersecting the AOI.")
    cell = st.selectbox("Inspect a cell", frame.cell_id.tolist())
    selected = evidence.call("get_cell", {"cell_id": cell})["cell"]
    st.json(selected)
    st.caption("Carbon values use illustrative biomass and a configured loss scenario. They are not predicted emissions.")
    st.subheader("Held-out feature associations")
    importance = pd.read_csv(resolve(cfg, "reports") / "permutation_importance.csv").drop(columns="fold")
    st.bar_chart(importance.mean())
    st.caption("Mean held-out average-precision decrease after permutation. Correlated features can distort this measure.")
    with st.expander("Validation and limitations"):
        st.json({"folds": report["folds"], "limitations": report["limitations"], "config": report["config"]})
    note = st.text_area("Reviewer notes", placeholder="Imagery checks, field evidence, uncertainty, next checks")
    decision = st.selectbox("Human review status", ["Pending", "More evidence needed", "Recommend field verification", "No follow-up recommended"])
    st.download_button("Download review record", pd.DataFrame([{
        "cell_id": cell, "human_review_status": decision, "reviewer_note": note,
        "config_sha256": report["config_sha256"], "data_mode": report["data_mode"]
    }]).to_csv(index=False), file_name=f"review_{cell}.csv", mime="text/csv")


if __name__ == "__main__":
    main()
