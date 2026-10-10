# Additional historical preprocessing inputs

These complement `DATA_CATALOG.md`; they do not change the original collection.
All outputs use WGS84 / UTM zone 43N (EPSG:32643), metre units, and AOI clipping.
The study area remains an **illustrative Kodagu–Wayanad rectangle**, not an official district boundary.
Original source metadata, exact queries, SHA-256 hashes, output grids and per-feature
lineage are retained in `data/raw/preprocessing/` and the output feature manifest.
All historical use follows retrospective observation-cutoff semantics, not a claim
that every dataset release was available to a forecaster on 31 December 2020.

## Forest history and labels

- History: `UMD/hansen/global_forest_change_2020_v1_8`, treecover2000, lossyear, datamask;
  observations 2000–2020, native geographic ~30 m, output 30 m.
- Labels: `UMD/hansen/global_forest_change_2024_v1_12`, lossyear/datamask;
  only loss offsets 21–24 enter targets. Never a predictor dependency.
- Units: percent canopy, integer years since 2000, categorical land mask.
- License: CC BY 4.0, Hansen/UMD/GLAD; [provider](https://glad.earthengine.app/view/global-forest-change).
- Restores masked loss-year zeros only on datamask land. Original masked downloads
  are retained separately for diagnosis. All forest eligibility uses the historical release.

## Additional spectral and climate years

- Sentinel-2 SR Harmonized Jan–Apr 2017 and 2018, median reflectance bands and clear counts.
  Actual Earth Engine scene IDs are saved. Although the catalog advertises a March 2017
  start, the live collection returned January/February 2017 IDs; spatial valid coverage
  is measured rather than inferred from catalog dates. No 2021–2024 spectral data enter features.
- Same SCL mask, native 10/20 m bands, output 20 m, and Copernicus Sentinel open-data terms
  as original 2019–2020 layers. Indices are spatial statistics of median reflectance.
- CHIRPS daily 2017–2020 annual, Jan–Apr dry, May–Dec wet totals plus expected-day counts;
  native 0.05 degrees, output 1 km, mm per period; public domain, UCSB/CHG.
- ERA5-Land monthly 2017/2018 joins cached 2019/2020: day-weighted annual temperature
  (degrees C) and 0–7 cm soil water (m3/m3); native 0.1 degrees, output 1 km;
  Copernicus Climate Change Service/ECMWF terms. Resampling adds no local information.

## ESA CCI biomass: valid historical alternative

- Original **2017 v1.0**, created **31 October 2019**, verified in source NetCDF attributes.
- [Dataset DOI](https://doi.org/10.5285/bedc59f37c9545c981a839eb552e4084).
- [CEDA source catalog](https://data.cci.ceda.ac.uk/thredds/catalog/esacci/biomass/data/agb/maps/2017/v1.0/netcdf/catalog.html).
- Native EPSG:4326, 0.0008888889 degrees (nominal 100 m), output 100 m UTM with average resampling.
- AGB = Mg oven-dry woody biomass/ha; carbon = AGB × configured 0.47 in Mg C/ha.
  This excludes soil/belowground carbon and is a **2017 covariate**, not a 2020 stock estimate.
- A small OPeNDAP ASCII subset avoids downloading the 27 GB global file. Source attributes,
  exact subset query and response hash are cached. Conservative information bound 2019.
- ESA CCI open-data policy; cite Santoro & Cartus (2019) and acknowledge ESA CCI Biomass.
- Newer ESA v6 uses later lidar calibration, and GEDI v2 extends into 2021; neither is substituted.

## Historical human-pressure inputs

- Population: `JRC/GHSL/P2016/POP_GPW_GLOBE_V1/2015`, **epoch 2015**, conservative
  information bound 2016. Native 250 m World Mollweide; count/native pixel area converts
  to people/km2 before sampling the 250 m UTM output. This is not a 2020 population estimate.
  [Official catalog and reuse terms](https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2016_POP_GPW_GLOBE_V1):
  EC JRC/CIESIN open reuse with acknowledgement. Original WorldPop covariate vintage remains unverified.
- Roads/villages: reuse original Overpass attic snapshot **2020-12-31T23:59:59Z**,
  native WGS84 vectors, output UTM. Road tags select motor roads/tracks; settlements select
  village/hamlet/isolated dwelling. Exact tag allowlists are in config.
- Mining proxy: new historical OSM `landuse=quarry` query at the same snapshot,
  native WGS84 polygons/points, output UTM; 85 mapped features in the initial run.
  Polygon overlaps are unioned before area calculation; points contribute distance only.
  Exact query/response hash and tags are cached. **Incomplete quarry proxy**, not a comprehensive
  mine inventory; unlisted, artisanal and underground sites may be absent. Zero mapped area
  does not prove no mining. Maus v2 remains excluded because supporting imagery is undated.
- OSM license: [ODbL 1.0](https://www.openstreetmap.org/copyright), OpenStreetMap contributors.
  Snapshot captures recorded mapping knowledge, not construction/extraction start dates.

Distance-to-road/village/quarry/historical-loss features are centroid distances.
A value is censored to missing when the nearest in-AOI object is farther than the AOI boundary,
since an unobserved external object might be closer. Historical loss uses centers of valid
30 m pixels with loss detected no later than T; no future loss pixels enter the search.
