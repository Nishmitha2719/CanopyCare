# CanopyCare

> Where is forest loss likely, why, what factors, which neighbors, and what to prioritize?

“Why” and “factors” mean model associations, never proven causation. The system
recommends; a human decides.

## Repository setup

```text
canopycare/
  config.yaml  requirements.txt  requirements-lock.txt  pyproject.toml
  data/{raw,interim,processed}/
  src/{data,features,models,xai,carbon,exposure,agent,dashboard}/
  src/utils.py
  notebooks/  tests/  reports/  README.md
```

Use the existing Python 3.11 environment, or create one with
`py -3.11 -m venv .venv`. In PowerShell, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Optional: activate so the exact acceptance command resolves to Python 3.11.
.\.venv\Scripts\Activate.ps1
python -m src.utils
```

If activation is blocked by PowerShell policy, use
`.\.venv\Scripts\python.exe -m src.utils` directly. No policy change is required.
`requirements.txt` pins direct setup and baseline dependencies;
`requirements-lock.txt` records every installed distribution in the verified
Windows/Python 3.11 environment, excluding the editable project itself. Install
that lock instead to reproduce its transitive dependencies. Optional full-stack
extras remain in `pyproject.toml`; these are not installed by the minimal setup file.

### Configuration and projection

`study_area.shapefile` is a historical key name that also accepts GeoJSON. It points
to `data/raw/study_area.geojson`, a supplied **illustrative rectangle**, not an
administrative boundary. Replace the path and update `bbox_wgs84` together for your
actual study area. Paths resolve relative to `config.yaml`.

We use **EPSG:32643, WGS84 / UTM zone 43N**, with a 75°E central meridian and metre
units. The illustrative western Karnataka/Kodagu subset lies within 72–78°E and
north of the equator, making this zone suitable for 1,000 m square cells. Karnataka
is not wholly contained in one UTM zone; reconsider the projection for an AOI east
of 78°E or a statewide study. Geographic longitude/latitude degrees are not metres.
The setup utility verifies projection units and a longitude/latitude round trip.

The config declares T=2020, a four-year target window (2021–2024), seed=42, carbon
fraction=0.47, and provisional risk-score bands: low <0.30, medium [0.30,0.70),
high >=0.70. These bands are **unvalidated placeholders**, separate from the binary
classification threshold (0.5). Validate thresholds within training folds and
with human reviewers; do not tune against the final holdout.

### Earth Engine authentication and smoke test

Register a Cloud project for Earth Engine, enable its API, and grant your account
access. Put its ID in `earth_engine.project`, or set `EE_PROJECT`:

```powershell
$env:EE_PROJECT = "YOUR_ACTUAL_PROJECT_ID"
python -m src.data.gee_init --authenticate
# Subsequent runs reuse local credentials; no interactive login unless requested.
python -m src.data.gee_init
```

Successful output must say **GEE initialized; real server smoke test passed: 1 + 1 = 2**.
An import or mocked unit test does not meet this condition. Failures return a
nonzero exit code. Credentials stay in Google's local credential store and must
not be committed. The extraction pipeline uses this same initialization helper.
See [Google's authentication guide](https://developers.google.com/earth-engine/guides/auth).

### Setup verification checklist

- [ ] `python --version` reports Python 3.11 from `.venv`.
- [ ] `python -m pip check` reports no broken requirements.
- [ ] `python -m src.utils` exits 0; config, boundary existence and CRS checks pass.
- [ ] Replace/confirm the illustrative boundary; inspect extent, UTM zone and 1 km grid.
- [ ] Confirm T, horizon, seed, carbon fraction and provisional risk thresholds.
- [ ] `python -m unittest discover -s tests -p test_setup.py -v` passes offline checks.
- [ ] Authenticate and run `python -m src.data.gee_init`; verify real server result 2.
- [ ] Optional live test: set `CANOPYCARE_RUN_GEE_TEST=1`, then rerun setup tests.
- [ ] After changing config, regenerate demo/data and model reports before using the dashboard.

## Existing research workflow

A modular research baseline for forest-loss risk prediction, spatial evaluation,
model explanations, and human review. The default runs entirely on **synthetic
fixtures**. Its metrics are software verification, not evidence of ecological skill.

The working directory is the repository root (`D:\CanopyCare`), corresponding to
`canopycare/` in the requested layout. All scientific assumptions are in
[`config.yaml`](config.yaml). The illustrative bounding box is `[75.65, 11.60,
76.20, 12.35]` (west, south, east, north), not a Kodagu/Wayanad administrative boundary.
Replace it with your study boundary before using real results.

## Run the complete synthetic workflow

Use Python **3.11** in a virtual environment. PowerShell:

```powershell
cd D:\CanopyCare
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dashboard]"
.\.venv\Scripts\python.exe -m src.cli demo
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run src/dashboard/app.py
```

The demo creates 900 projected 1 km cells (`N0001` onward), features, labels,
buffered spatial folds, held-out predictions, fold metrics, permutation importance,
a final fitted model, carbon scenarios, and input/configuration fingerprints.
The demo grid is a synthetic rectangle; it does **not** represent the configured
study-area polygon. Commands rerun into the configured paths and replace their own
artifacts. Use distinct `paths.reports` directories when comparing models.

If `py -3.11` is unavailable, install Python 3.11 and use its executable in the first
command. The source supports 3.11–3.13; setup utilities are verified in the local Python 3.11 environment.

## Real Earth Engine workflow

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[geo,boost,dashboard]"
.\.venv\Scripts\earthengine.exe authenticate
# Set earth_engine.project and confirm study_area in config.yaml.
.\.venv\Scripts\python.exe -m src.cli extract
.\.venv\Scripts\python.exe -m src.cli train
```

Earth Engine must be registered and authorized for your Cloud project. Extraction
is synchronous in configured batches and fails visibly on service errors. Large
areas may need batch exports; automatic retries and resumable exports are not
implemented. No authentication or remote extraction was performed during setup.

Grids use EPSG:32643 and metre coordinates. The grid retains **full** 1 km squares
that intersect the AOI, including their area outside the boundary. IDs are stable
for a fixed footprint and grid convention; they may change if the footprint changes.
The GeoJSON is exported in WGS84 for interoperability while x/y remain UTM metres.

Features are remaining baseline forest fraction, recent historical loss fraction,
elevation, and slope. Forest is tree cover >= the configured canopy threshold in
2000, excluding observed losses through T. Regrowth and plantations are not
separately modeled. Historical loss fraction uses full-cell area; future loss
fraction uses forest area remaining at T. Eligibility requires sufficient forest
and valid coverage. Future coverage is used only to assess label eligibility.
Excluded-cell counts are reported; this selection can limit generalizability.

With T=2020, labels cover 2021–2024. A cell is positive if cumulative future loss
is >= 1% of forest remaining at T by default. Change that assumption in config.
The extractor uses separate Hansen releases for features (ending 2020) and labels
(ending 2024), never the future release to reconstruct historical predictors.
Do not use Hansen's aggregate gain or latest imagery bands as historical features.

This is an **observation-cutoff hindcast**, not a reconstruction of what was
published and available on December 31, 2020. Annual releases can be published
later. Operational historical forecasts require verified release dates and may
require lagged features. SRTM V3 has auxiliary void filling; its configured source
end year is an explicit conservative assumption to review. The code checks metadata,
but does not independently certify the truth of provider provenance.

## Models, metrics, and explanations

Set `model.kind` to `logistic`, `xgboost`, or `gnn`.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[boost,graph]"
.\.venv\Scripts\python.exe -m src.cli train
```

Blocks are 5 km by default. Stratified group folds assign entire blocks, then remove
training centroids within 1 km of any test centroid. Every retained node receives
one held-out prediction. This is block CV across a region, not a single contiguous
geographic holdout. Adjust scale based on spatial autocorrelation and perform an
independent regional/temporal holdout before making deployment claims.

Scaling, class weights, and graph construction are fold-local. The GCN uses separate
training and held-out graphs; no cross-fold message passing occurs. Class weighting
addresses imbalance only in training. There is no random node split or global
resampling. Fixed epochs and a prespecified score threshold avoid using outer test
labels for tuning. Hyperparameter selection requires a separate nested spatial CV
implementation; do not repeatedly tune against these outer-fold scores.

Reports include trapezoidal **PR-AUC**, **average precision** (a distinct summary),
recall, F1, ROC-AUC, prevalence, and confusion counts, both by fold and pooled OOF.
Class-weighted scores are **uncalibrated**, not reliable event probabilities. No
accuracy-only claim is made. Invalid single-class folds fail instead of hiding
undefined metrics. Pooled OOF metrics are not performance of the all-data final fit.

Held-out permutation importance is built into every model run. Negative importance
is retained. `src/xai/explain.py` also provides optional tree SHAP and graph Captum
Integrated Gradients functions. SHAP uses raw-margin contributions; graph IG uses
training feature means as baseline and returns contributions from all graph nodes
plus numerical convergence delta. These adapters are not automatically run by the
CLI. Grad-CAM is not included because this version has no raster-image CNN; applying
it to tabular models would be inappropriate. Rasterio/geemap are optional geospatial
dependencies for extending the workflow, not mandatory steps of the current extractor.

All explanations describe **model association, never established causation**.

## Human-in-the-loop agent

A deterministic shortlist needs no LLM:

```powershell
.\.venv\Scripts\python.exe -m src.cli recommend --limit 5
```

For a local LLM, run your installed Ollama service, install a tool-capable model,
and set `agent.ollama_model` to that exact model name. Then:

```powershell
.\.venv\Scripts\python.exe -m src.cli agent --question "Inspect N0001 and recommend evidence to check."
```

The loop follows [Ollama's documented tool-calling message format](https://docs.ollama.com/capabilities/tool-calling).
It offers three read-only tools: inspect a cell, read validation, and prioritize
cells. It has bounded rounds, an allowlist, argument checks, local-only transport,
and an audit trail in `reports/agent_review.json`. There are no dispatch, patrol,
publishing, notification, or intervention tools. The LLM prose is an **unverified
draft**; prompt instructions cannot guarantee its factual or causal correctness.
A human must inspect the evidence and decide. Local LLM inference is not guaranteed
bit-for-bit reproducible even with a fixed seed. No live LLM inference was verified
at setup; a fake-provider integration test exercises the complete tool cycle.

The dashboard permits downloading a human review record. It does not store decisions
in a remote system. A note or shortlist does not execute an intervention.

## Carbon and exposure

Above-ground carbon = forest hectares × assumed dry biomass (Mg/ha) × carbon fraction.
The hypothetical CO2 mass equivalent additionally multiplies a configured loss
fraction and CO2/C ratio. These are illustrative stock scenarios, **not measured
stocks, predicted emissions, avoided emissions, or intervention benefits**. A binary
loss score cannot supply expected loss area; the pipeline does not multiply it into
carbon estimates. Below-ground biomass, soil, deadwood, combustion, and timing are
not modeled. Replace assumptions with defensible local estimates and uncertainty
ranges before interpreting carbon quantities.

`src/exposure/proximity.py` counts supplied assets within a configured radius using
the same metre CRS. No exposure dataset is bundled; these counts are contextual
summaries and never added to predictors without historical provenance.

## Outputs and reproducibility

- `data/processed/cells.csv` and `provenance.json`: features, labels, source mode,
  temporal contract, and byte hash. Labels and IDs are explicitly excluded from X.
- `reports/metrics.json`: fold/pooled metrics, exclusion counts, full config, seed,
  dependency versions, Python version, data hash, and prediction hash.
- `reports/fold_assignments.json`: actual training/test cell IDs after buffering.
- `reports/predictions.csv`: held-out scores, fold IDs, review flags, carbon scenarios.
- `reports/permutation_importance.csv`: fold-specific feature associations.
- `reports/model.joblib`: all-data model, feature order, and config. Load only trusted
  locally produced joblib files; serialization is not a secure exchange format.
- `reports/requirements-observed.txt`: versions of principal installed libraries,
  not a complete cross-platform lock file. For your validated Python 3.11 environment,
  save `python -m pip freeze > requirements-lock.txt` and preserve the source revision.

Dependencies have compatibility bounds, not an asserted tested Python 3.11 lock.
Archive source, the config, data, hashes, and a complete environment lock together.
The source has no downloaded geospatial data or embedded credentials.

## Validation checklist before scientific use

1. Confirm AOI, UTM zone, exact 1,000 m square sides, boundary behavior, and stable IDs.
2. Inspect dataset provenance and source observation dates; verify operational release
   dates separately if claiming a real historical forecast. Test rejection of post-T data.
3. Manually inspect loss masks and no-data areas in several positive/negative cells;
   verify numerator/denominator, loss threshold, eligibility, and 2021–2024 horizon.
4. Plot block assignments, verify disjoint groups and buffer distances, examine spatial
   autocorrelation, and check both classes in each fold. Preserve an independent holdout.
5. Compare PR-AUC/AP to prevalence; inspect recall, F1, ROC-AUC, confusion counts, and
   variation across folds. Tune/calibrate only in inner training folds.
6. Repeat the same run and compare hashes/scores. Test each optional backend in the
   intended Python 3.11 environment; verify GCN graph isolation and SHAP/IG completeness.
7. Confirm explanations use associational language; test correlated predictors and
   explanation sensitivity. Do not infer a driver's causal contribution.
8. Review biomass/carbon assumptions, units, and uncertainty. Validate asset CRS and
   timestamps before adding exposure data. Do not label stock scenarios as emissions.
9. Exercise invalid/malicious agent calls, bounded rounds, synthetic warnings, stale
   artifact rejection, and human review records. Check every LLM factual claim.

## Sources

- [Hansen 2024 download metadata and Earth Engine asset](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html)
- [NASA SRTM catalog, including auxiliary void filling](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003)
- [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Average precision definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)

## Setup verification (2026-10-07)

Verified on this machine with Python 3.13.3:

- 16 automated tests passed, including temporal contracts, spatial buffers,
  integrity checks, fold-local preprocessing, agent restrictions, and Streamlit controls.
- The 900-cell synthetic logistic workflow completed and repeated prediction CSVs
  were byte-identical.
- The XGBoost synthetic workflow completed all four spatial folds.
- Tree SHAP raw-margin additivity passed on 100 synthetic cells.
- All Python source compiled successfully.

Not verified here: Python 3.11 installation, real Earth Engine extraction and grid
execution (geospatial extra/account needed), GCN/Captum (optional packages needed),
and live Ollama inference (a local model/service is needed). None of the synthetic
results establishes real-world forest-loss prediction performance.

## Repository setup verification update

The setup task was checked with Python 3.11.9: `python -m src.utils` passed,
config and CRS checks passed, `pip check` reported no broken requirements, and
the synthetic pipeline completed. The complete test suite passed 23 tests with
one explicitly skipped live-GEE test. GEE initialization is **not yet verified**:
the initial run had no Cloud project ID. This was subsequently resolved as recorded below. Earlier Python 3.13 verification notes describe the preceding baseline run.

## Earth Engine acceptance completed (2026-10-07)

`earth_engine.project` is set to `canopycare`. Browser OAuth completed successfully,
and the real GEE initialization/smoke test passed with server result `1 + 1 = 2`.
The setup acceptance criteria are met: config loads, `python -m src.utils` runs,
and GEE initializes. Credentials are stored outside the repository by Google's
authentication library. This verifies API access; dataset extraction remains a
separate workflow and the supplied study boundary remains illustrative.

## Multi-source data collection

The collectors in `src/data/layers.py` build Sentinel-2, Hansen, SRTM, CHIRPS,
ERA5-Land, GEDI and WorldPop products. `src/data/vectors.py` downloads historical
OSM roads/settlements and the original Maus mining polygons. All parameters,
source IDs, dry-season months, export scales, endpoint settings and nodata choices
are in `config.yaml` under `collection`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-collection.txt
.\.venv\Scripts\python.exe -m src.data.collect
.\.venv\Scripts\python.exe -m src.data.inspect_collection
.\.venv\Scripts\python.exe -m src.data.run_sanity_notebook
```

Use `--only sentinel2`, `--only vectors`, or another source name to resume a subset.
Completed raster tiles are reused only for the same export contract. If scientific
parameters or AOI change, use a new `collection.raw_directory`. OSM raw responses
are cached by exact query, including the historical date. HTTP/network errors never
become fake empty datasets. A genuine empty mining intersection is retained and labeled.

`--mode drive` submits Earth Engine raster tasks to `CanopyCare_raw` in Drive;
it records task IDs and does not claim local completion. The local mode tiles every
request below GEE's download-size limit, then writes compressed mosaics. Interrupted
mosaics are rebuilt from already completed tiles. Do not launch overlapping collectors
for the same layer concurrently. Do not treat a submitted Drive task as a downloaded file.

See [data/DATA_CATALOG.md](data/DATA_CATALOG.md) for source/version, license,
native/output resolution, CRS, observation window, units, leakage flags and checksums.
`data/raw/collection/validation.json` contains per-band coverage and grid validation.
The executed `notebooks/01_collection_sanity.ipynb` plots every layer and band over
the AOI; exported figures are in `reports/collection_sanity/`.

The newly collected files are not automatically fed into model training. The admission
flag is conservative and must be checked by future feature-engineering code. This
pipeline does not claim operational vintage verification for retrospectively processed
satellite/climate releases. Population covariates and mining supporting imagery need
additional temporal review before feature use. All findings are associations.

Collection size note: the current AOI uses approximately 2.6 GiB including retained
download tiles, compressed mosaics, and source archives. Tiles are deliberately kept
for resuming or rebuilding interrupted exports. The 20/30/100/1,000 m products share
a common UTM origin but are not interchangeable pixel arrays; use an explicit
resampling/area-weighting strategy during later 1 km feature aggregation.

The notebook and catalog expose source gaps. GEDI biomass estimates are not
wall-to-wall here, while QF and sample-count bands have broader coverage. A valid,
empty mining GeoPackage is an honest source intersection result, not a fabricated
positive polygon or a claim that no quarry exists. Review local evidence before use.

### Collection run verified on 2026-10-07

All 25 catalog entries passed local existence, content-hash, CRS, common-origin,
AOI-intersection and per-band usable-coverage checks: 22 raster mosaics, historical
roads (11,430 features), historical settlements (404 locations), and a valid empty
Maus mining intersection. The notebook executed all code cells without errors and
produced 25 figures. The regression suite passed 29 tests, with one opt-in live-GEE
unit test skipped; actual Earth Engine access was exercised by the completed downloads.
A completed Hansen export was rerun and reused successfully.

Coverage checks establish that files are usable, not that source coverage is complete
or that values are scientifically validated. GEDI MU/SE cover about 31.7% of this AOI.
Review the plots, cloud residuals, source dates, uncertainty/quality flags, population
vintage and mining/OSM completeness before constructing model features.


## Real preprocessing and feature engineering

Run from the repository root with the Python 3.11 virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-collection.txt
# First run: verify/download additional historical inputs, then build everything.
.\.venv\Scripts\python.exe -m src.features.pipeline --prepare
# Subsequent offline rebuild using cached, hash-checked inputs:
.\.venv\Scripts\python.exe -m src.features.pipeline
.\.venv\Scripts\python.exe -m unittest tests.test_preprocessing -v
```

Outputs are separate from the earlier synthetic baseline: `data/processed/preprocessing/forest_nodes.csv`,
`forest_nodes.parquet`, `forest_nodes.gpkg` (layer `forest_nodes`), `grid_all.gpkg`,
`grid_eligibility.csv`, and `feature_manifest.json`. Open
`reports/preprocessing/data_quality.html` for missingness, outliers, class balance,
spatial coverage, correlation heatmap and feature distributions. Machine-readable
quality summaries and correlation matrices sit beside it. Complete implementations
are in `src/features/`; source additions are documented in `data/PREPROCESSING_DATA_CATALOG.md`.

Grid nodes are full 1 km UTM squares, assigned stable south-to-north, west-to-east
IDs for an unchanged AOI and grid origin. `node_id` equals the legacy `cell_id`.
Row/column indices start at the southwest intersecting-grid origin; latitude/longitude
are projected-square centroids transformed to WGS84. IDs are not renumbered after
filtering. At least 99% AOI coverage, 95% valid historical land coverage, and 10%
remaining baseline forest are required. The 10% threshold gives roughly 10 ha
of forest per node and avoids fitting fragment-dominated cells; it is a provisional
research choice, not an ecological definition. Test sensitivity before modeling.
The retained-node graph has gaps where cells were excluded.

Historical features use Hansen **2020 v1.8**, while labels use **2024 v1.12**.
Archived loss-year rasters mask zero/no-loss pixels; the preparation step restores
zero only where `datamask == 1`. It never fills ocean/off-footprint coverage.
The latest 2025 collection is not used for predictors. Target `y=1` means at least
1% of forest remaining at T was lost during 2021–2024. Every remaining-forest pixel
must have a valid label, and zero-forest/unknown-label cells are excluded. Tree-cover
loss is not necessarily permanent deforestation; regrowth is not represented.

Features include spatial mean/std of NDVI, EVI, NBR and NDMI for 2017–2020;
NDVI OLS slope and anomaly; terrain means/max and circular aspect; four years of
annual/seasonal climate; historical AGB/carbon; population, road/village/quarry
proxies; and cutoff-aware forest-loss history/distance. Indices are calculated from
median reflectance composites. The anomaly baseline includes T and is only four
years long. Slope requires at least three observed years. All observed history
windows end at T: last 1/3/5 means T, T-2..T, T-4..T. History fractions use valid
land as denominator; the target uses remaining forest. Zonal statistics use equal-area
UTM pixel centers, an approximation at square boundaries. Aspect is circular mean
direction encoded as normalized sine/cosine, accompanied by its concentration;
flat or directionally ambiguous cells are missing.

Historical biomass uses **ESA CCI 2017 v1** (created October 2019); carbon density
is AGB density multiplied by 0.47. Population uses **GHSL P2016, epoch 2015**.
These are historical covariates, not 2020 stock estimates. Mining features use
**OSM landuse=quarry at the 2020 snapshot**, an incomplete quarry proxy rather than
an exhaustive inventory of mines. The original Maus layer and post-T GEDI layer
remain available for reference but cannot enter this feature table. Road types and
village/hamlet tags are specified in config. Nearest distances are from cell centroids;
values are missing when a closer feature could be outside the collected AOI.

**Imputation:** exported values stay missing. Never impute labels or fit an imputer
on the entire dataset. Use `model_columns(manifest)` from `src.features.imputation`
to select only approved predictors, then put `make_preprocessor()` inside each
spatial training fold's model pipeline. It fits training medians plus missingness
indicators and scaling. A completely empty training-fold column gets a fixed zero
fallback plus its indicator, without consulting held-out data. Permanently unapproved
sources are excluded by provenance. Constant/all-missing columns are reported;
no full-data correlation/outlier-based selection or trimming is performed. The older
four-feature trainer does not automatically consume this new table.

Validation checklist:
- [ ] Run the preparation and offline pipeline without errors; inspect source metadata/hash records.
- [ ] Confirm CSV, Parquet and GeoPackage contain identical unique node IDs and binary labels.
- [ ] Inspect grid spacing, centroid positions, row/column indexing and excluded boundary cells.
- [ ] Confirm all geometry areas are 1,000,000 m2 in EPSG:32643.
- [ ] Run leakage tests: mutate post-T loss years and future labels; predictors must stay unchanged.
- [ ] Review missing/censored values, physical ranges, class balance and spatial clusters in the quality report.
- [ ] Review sparse 2017 Sentinel coverage, stale biomass/population epochs, and incomplete OSM quarry mapping.
- [ ] Validate 10% minimum forest, 30% canopy, 1% loss and coverage thresholds with domain experts.
- [ ] For modeling use buffered spatial CV and train-fold-only preprocessing; report PR-AUC, recall, F1 and ROC-AUC.
- [ ] Treat all modeled relationships as associations; a human reviews prioritization decisions.
