"""Reproducible descriptive quality report; no model selection or global imputation."""
from __future__ import annotations
import html
import os
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from src.config import Config, write_json


def report(nodes: pd.DataFrame, manifest: dict[str,Any], cfg: Config) -> None:
    root = Path(cfg["_root"])/cfg["preprocessing"]["report_directory"]
    root.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR",str(root/".matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    features = list(manifest["features"])
    rows = []
    for column in features:
        values = nodes[column].dropna()
        q1,q3 = values.quantile([.25,.75]) if len(values) else (np.nan,np.nan)
        margin = cfg["preprocessing"]["outlier_iqr_multiplier"]*(q3-q1)
        rows.append({"feature":column,"missing_count":int(nodes[column].isna().sum()),
                     "missing_fraction":float(nodes[column].isna().mean()),"unique":int(values.nunique()),
                     "min":float(values.min()) if len(values) else None,"max":float(values.max()) if len(values) else None,
                     "median":float(values.median()) if len(values) else None,
                     "iqr_outliers":int(((values < q1-margin) | (values > q3+margin)).sum()),
                     "infinite_count":int(np.isinf(nodes[column]).sum())})
    summary = pd.DataFrame(rows)
    summary.to_csv(root/"feature_quality.csv",index=False)
    correlation = nodes[manifest["model_features"]].corr(method="pearson")
    correlation.to_csv(root/"feature_correlations.csv")
    fig,ax = plt.subplots(figsize=(22,20))
    im = ax.imshow(correlation, vmin=-1,vmax=1,cmap="RdBu_r",interpolation="nearest")
    ax.set_xticks(range(len(correlation)),correlation.columns,rotation=90,fontsize=6)
    ax.set_yticks(range(len(correlation)),correlation.columns,fontsize=6)
    ax.set_title("Forest-node feature associations (Pearson r; pairwise complete observations)")
    fig.colorbar(im,ax=ax,shrink=.7,label="Correlation; not causation")
    fig.tight_layout(); fig.savefig(root/"correlation_heatmap.png",dpi=150); plt.close(fig)
    pages = []
    for start in range(0,len(features),12):
        fig,axes = plt.subplots(4,3,figsize=(15,14))
        for ax,column in zip(axes.ravel(),features[start:start+12]):
            values = nodes[column].dropna()
            if len(values): ax.hist(values,bins=cfg["preprocessing"]["histogram_bins"],color="#23836a")
            else: ax.text(.5,.5,"Unavailable - no imputation",ha="center",va="center",transform=ax.transAxes)
            ax.set_title(column,fontsize=9)
            ax.set_ylabel("Nodes")
        for ax in axes.ravel()[len(features[start:start+12]):]: ax.set_visible(False)
        fig.suptitle("Feature distributions - retained forest nodes; descriptive only")
        fig.tight_layout()
        filename = f"distributions_{start//12+1:02d}.png"
        fig.savefig(root/filename,dpi=120); plt.close(fig); pages.append(filename)
    classes = {str(int(k)):int(v) for k,v in nodes.y.value_counts().sort_index().items()}
    fig,axes = plt.subplots(1,2,figsize=(12,5))
    axes[0].bar(list(classes),list(classes.values()),color=["#23836a","#d88432"][:len(classes)])
    axes[0].set(xlabel="Future-loss target y",ylabel="Nodes",title="Class balance")
    points = axes[1].scatter(nodes.x_m,nodes.y_m,c=nodes.y,cmap="cividis",s=4,vmin=0,vmax=1)
    axes[1].set(xlabel="UTM easting (m)",ylabel="UTM northing (m)",title="Retained 1 km nodes")
    axes[1].set_aspect("equal"); fig.colorbar(points,ax=axes[1],ticks=[0,1])
    fig.tight_layout(); fig.savefig(root/"class_balance_map.png",dpi=150); plt.close(fig)
    checks = {"unique_node_ids":bool(nodes.node_id.is_unique),"one_row_per_node":len(nodes)==nodes.node_id.nunique(),
              "no_infinite_features":int(summary.infinite_count.sum()) == 0,
              "finite_binary_targets":bool(nodes.y.isin([0,1]).all()),
              "forest_eligibility":bool((nodes.forest_fraction_T >= cfg["forest"]["min_forest_fraction"]).all()),
              "target_agreement":bool((nodes.y == (nodes.future_loss_fraction >= cfg["forest"]["loss_threshold_fraction"])).all()),
              "feature_temporal_audit":manifest["leakage_audit"] == "passed"}
    quality = {"checks":checks,"nodes":len(nodes),"classes":classes,"positive_fraction":float(nodes.y.mean()),
               "missing_features":manifest["all_missing_features"],"constant_features_for_review":manifest["constant_features"],
               "feature_count":len(features),"model_feature_count":len(manifest["model_features"]),
               "exclusion_counts_nonexclusive":manifest["exclusion_counts_nonexclusive"],
               "imputation":"None in exported nodes. Within each spatial training fold: median + missing indicators; fit only on train. Globally unavailable source columns are excluded. Never impute labels.",
               "outliers":f"Descriptive {cfg['preprocessing']['outlier_iqr_multiplier']:g}-IQR flags only; no clipping, filtering or feature selection based on this full-data report."}
    write_json(root/"quality_summary.json",quality)
    if not all(checks.values()): raise ValueError("Data-quality structural checks failed")
    missing = "".join(f"<li>{html.escape(c)}: {html.escape(manifest['features'][c]['definition'])}</li>" for c in manifest["all_missing_features"])
    exclusions = "".join(f"<li>{html.escape(k)}: {v}</li>" for k,v in manifest["exclusion_counts_nonexclusive"].items())
    body = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>CanopyCare preprocessing quality</title>
<style>body{{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 20px;color:#182e26}}img{{max-width:100%}}table{{border-collapse:collapse;font-size:12px}}th,td{{padding:5px;border:1px solid #ccc}}h1,h2{{color:#17694e}}</style>
<h1>CanopyCare: forest-node data quality</h1>
<p>{len(nodes):,} retained nodes from {manifest['grid_count']:,} intersecting 1 km squares; T={manifest['cutoff_year']}; target {manifest['target_start_year']}-{manifest['target_end_year']}.</p>
<p>Positive target: {int(nodes.y.sum()):,} ({nodes.y.mean():.2%}). {len(features)} declared feature fields, {len(manifest['model_features'])} temporally approved fields (no full-data feature selection). Temporal audit and structural checks passed.</p>
<h2>Eligibility and label</h2><p>Retain at least {cfg['forest']['min_forest_fraction']:.0%} remaining baseline forest (about 10 ha at complete coverage); a provisional minimum to avoid tiny forest fragments dominating a forest-risk study. Use {cfg['forest']['canopy_threshold_pct']}% tree-cover threshold in 2000, subtract all detected loss through T. Regrowth is not mapped. The target is loss of at least {cfg['forest']['loss_threshold_fraction']:.0%} of forest remaining at T. It describes tree-cover disturbance, not necessarily permanent deforestation. Sensitivity to both thresholds needs validation.</p>
<p>Whole squares are preserved, with at least {cfg['preprocessing']['min_aoi_fraction']:.0%} AOI coverage and {cfg['forest']['min_valid_fraction']:.0%} historical land coverage; all remaining-forest pixels must have valid labels. Exclusions may overlap:</p><ul>{exclusions}</ul>
<img src="class_balance_map.png" alt="Class balance and spatial distribution">
<h2>Missing data and imputation</h2><p>{html.escape(quality['imputation'])} Missing source values are not zeros. Boundary-censored distances mean an unseen object outside the AOI might be closer. Historical OSM mapped absence is not verified real-world absence.</p><ul>{missing}</ul>
<h2>Historical proxy vintages</h2><p>AGB uses original ESA CCI 2017 v1, created in October 2019, with carbon density = AGB times the configured carbon fraction. Population uses GHSL P2016 epoch 2015, expressed as people/km2. Neither is a 2020 stock estimate. Mining uses OSM landuse=quarry at the 2020 snapshot; this is an incomplete quarry proxy, not an exhaustive mine inventory. Zero mapped quarry area does not establish no mining. Road density includes configured motor-road/track tags; nearest village uses configured rural place tags.</p><h2>Definitions and limitations</h2><p>EPSG:32643 (WGS84 / UTM 43N) provides metre coordinates for this Karnataka/Kerala subset. Zonal statistics use equal-area pixel centers, so 30 m raster edges approximate square area. Climate layers retain their coarse native information despite 1 km export. Indices are computed from dry-season median reflectance; EVI outside the configured physical range is masked. Trends use actual year spacing and require at least the configured number of years. Anomalies use the short 2017-2020 inclusive mean, not a climate normal. Circular aspect is the normalized mean sine/cosine direction, not an arithmetic degree mean; flat and ambiguous directions are missing.</p>
<p>This is retrospective observation-cutoff research. Historical release availability at the forecast date has not been proved. Do not claim a prospectively issued 2020 forecast. Source hashes, dates, formulas and model-column allowlist are in feature_manifest.json. Source credits: UMD/GLAD Hansen CC BY 4.0; Copernicus Sentinel-2; NASA/USGS SRTM; UCSB CHIRPS public domain; Copernicus/ECMWF ERA5-Land; OpenStreetMap contributors, ODbL; ESA CCI Biomass v1, open data with acknowledgement (doi:10.5285/bedc59f37c9545c981a839eb552e4084); GHSL EC JRC/CIESIN, open reuse with acknowledgement.</p>
<h2>Missing values and outliers</h2><p>{html.escape(quality['outliers'])}</p>{summary.to_html(index=False,escape=True)}
<h2>Feature associations</h2><p>Pairwise correlations describe association, never proven causation. No feature selection has been performed using these full-data correlations.</p><a href="correlation_heatmap.png"><img src="correlation_heatmap.png" alt="Feature correlation heatmap"></a>
<h2>Feature distributions</h2>"""
    body += "".join(f'<img src="{name}" alt="Feature distribution panel">' for name in pages)
    body += '<h2>Before modeling</h2><p>Review threshold sensitivity, source completeness, and boundary coverage with a human. Use buffered spatial cross-validation; fit preprocessing independently inside each fold. Report PR-AUC, recall, F1 and ROC-AUC. These outputs support human decisions.</p></html>'
    (root/"data_quality.html").write_text(body,encoding="utf-8")
