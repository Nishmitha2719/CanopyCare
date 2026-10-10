# CanopyCare data catalog

Study area: configured illustrative Kodagu/Wayanad polygon; replace it before administrative claims.
Output CRS: **EPSG:32643**. Date ranges ending January/May 1 are end-exclusive for annual/seasonal collections.
Completion: **25/25 local layers verified**. See `raw/collection/validation.json` for full per-band coverage and checksums.

## Alignment and export policy

All rasters share the same UTM anchor snapped to 3,000 m. They retain different pixel sizes: 20 m optical, 30 m terrain/forest-change, 100 m population density, and 1 km climate/biomass. These are spatially registered, not identical arrays. Resample explicitly before stacking. Climate sampling at 1 km does not add detail beyond its native grid.

Local downloads use <=30 MiB uncompressed tiles with bounded retries and identical-contract resume. Each final GeoTIFF has a checksum, band labels and nodata=-9999. Optional Drive tasks are recorded as submitted and do not satisfy local completion. Vectors are clipped and saved as UTM GeoPackages; original responses/source files are retained.

## Temporal safety

Collection is not feature admission. `predictor_allowed=false` blocks GEDI's post-2020 observations, the latest Hansen release, unverified WorldPop covariate dates, and mining with undated supporting imagery. Post-T Sentinel/climate layers are reference/target-period data only. Historical OSM is queried as of 2020-12-31, without current-data fallback. All source products are retrospective releases; operational publication-time availability is not certified.

Predictor eligibility must be checked again in feature engineering; existing model code never auto-loads these new files.

## sentinel2_2019

- Source/version: COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- Native resolution/CRS: 10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM.
- License: Copernicus Sentinel Data Terms and Conditions.
- Observation dates: 2019-01-01 to 2019-05-01.
- Local status: verified.
- File: `data\raw\collection\sentinel2_2019\sentinel2_2019.tif`.
- Output CRS: EPSG:32643; resolution: 20 m.
- Bands/units: {'B2': 'reflectance', 'B3': 'reflectance', 'B4': 'reflectance', 'B8': 'reflectance', 'B11': 'reflectance', 'B12': 'reflectance', 'clear_count': 'observations'}
- Pre-T predictor admission: True.
- Processing/limitations: End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.
- SHA-256: `19eaffb1773de9eafa11084e50fe225b4c5a0dbe42cf62fc8706931938239c0f`.

AOI valid coverage: B2: 99.99%; B3: 99.99%; B4: 99.99%; B8: 99.99%; B11: 99.99%; B12: 99.99%; clear_count: 99.99%.
## sentinel2_2020

- Source/version: COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- Native resolution/CRS: 10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM.
- License: Copernicus Sentinel Data Terms and Conditions.
- Observation dates: 2020-01-01 to 2020-05-01.
- Local status: verified.
- File: `data\raw\collection\sentinel2_2020\sentinel2_2020.tif`.
- Output CRS: EPSG:32643; resolution: 20 m.
- Bands/units: {'B2': 'reflectance', 'B3': 'reflectance', 'B4': 'reflectance', 'B8': 'reflectance', 'B11': 'reflectance', 'B12': 'reflectance', 'clear_count': 'observations'}
- Pre-T predictor admission: True.
- Processing/limitations: End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.
- SHA-256: `82d829256ac467612ee0a02c528aeb89cf7babcdce3e91959524244189e1c9c1`.

AOI valid coverage: B2: 99.99%; B3: 99.99%; B4: 99.99%; B8: 99.99%; B11: 99.99%; B12: 99.99%; clear_count: 99.99%.
## sentinel2_2021

- Source/version: COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- Native resolution/CRS: 10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM.
- License: Copernicus Sentinel Data Terms and Conditions.
- Observation dates: 2021-01-01 to 2021-05-01.
- Local status: verified.
- File: `data\raw\collection\sentinel2_2021\sentinel2_2021.tif`.
- Output CRS: EPSG:32643; resolution: 20 m.
- Bands/units: {'B2': 'reflectance', 'B3': 'reflectance', 'B4': 'reflectance', 'B8': 'reflectance', 'B11': 'reflectance', 'B12': 'reflectance', 'clear_count': 'observations'}
- Pre-T predictor admission: False.
- Processing/limitations: End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.
- SHA-256: `b7e36449dd11ace8dc13d6279edd71b01428d6a0558637ca5cc43971e7856b22`.

AOI valid coverage: B2: 100.00%; B3: 100.00%; B4: 100.00%; B8: 100.00%; B11: 100.00%; B12: 100.00%; clear_count: 100.00%.
## sentinel2_2022

- Source/version: COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- Native resolution/CRS: 10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM.
- License: Copernicus Sentinel Data Terms and Conditions.
- Observation dates: 2022-01-01 to 2022-05-01.
- Local status: verified.
- File: `data\raw\collection\sentinel2_2022\sentinel2_2022.tif`.
- Output CRS: EPSG:32643; resolution: 20 m.
- Bands/units: {'B2': 'reflectance', 'B3': 'reflectance', 'B4': 'reflectance', 'B8': 'reflectance', 'B11': 'reflectance', 'B12': 'reflectance', 'clear_count': 'observations'}
- Pre-T predictor admission: False.
- Processing/limitations: End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.
- SHA-256: `3ef73e350d34ad43e244b9956251b0728709b5f5d76da753f8789959f1829023`.

AOI valid coverage: B2: 100.00%; B3: 100.00%; B4: 100.00%; B8: 100.00%; B11: 100.00%; B12: 100.00%; clear_count: 100.00%.
## sentinel2_2023

- Source/version: COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- Native resolution/CRS: 10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM.
- License: Copernicus Sentinel Data Terms and Conditions.
- Observation dates: 2023-01-01 to 2023-05-01.
- Local status: verified.
- File: `data\raw\collection\sentinel2_2023\sentinel2_2023.tif`.
- Output CRS: EPSG:32643; resolution: 20 m.
- Bands/units: {'B2': 'reflectance', 'B3': 'reflectance', 'B4': 'reflectance', 'B8': 'reflectance', 'B11': 'reflectance', 'B12': 'reflectance', 'clear_count': 'observations'}
- Pre-T predictor admission: False.
- Processing/limitations: End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.
- SHA-256: `2e161502ca0e2e37a87f3ec0afe9a39e60bef61f9adab9fb2e3e54d0e64e5534`.

AOI valid coverage: B2: 99.99%; B3: 99.99%; B4: 99.99%; B8: 99.99%; B11: 99.99%; B12: 99.99%; clear_count: 99.99%.
## sentinel2_2024

- Source/version: COPERNICUS/S2_SR_HARMONIZED; L2A harmonized collection, source scene IDs preserved. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
- Native resolution/CRS: 10 m B2/B3/B4/B8; 20 m B11/B12 and SCL; native per-tile UTM.
- License: Copernicus Sentinel Data Terms and Conditions.
- Observation dates: 2024-01-01 to 2024-05-01.
- Local status: verified.
- File: `data\raw\collection\sentinel2_2024\sentinel2_2024.tif`.
- Output CRS: EPSG:32643; resolution: 20 m.
- Bands/units: {'B2': 'reflectance', 'B3': 'reflectance', 'B4': 'reflectance', 'B8': 'reflectance', 'B11': 'reflectance', 'B12': 'reflectance', 'clear_count': 'observations'}
- Pre-T predictor admission: False.
- Processing/limitations: End date exclusive. Median at export grid; nearest-neighbor sampling, 20 m common band grid. SCL7 retained; inspect residual clouds.
- SHA-256: `90408a1817ee59d545e4b1462f2d52300b38cfb29d16337f3501719b637807bd`.

AOI valid coverage: B2: 99.99%; B3: 99.99%; B4: 99.99%; B8: 99.99%; B11: 99.99%; B12: 99.99%; clear_count: 99.99%.
## rainfall_2019

- Source/version: CHIRPS v2.0 Final daily. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- Native resolution/CRS: 0.05 degrees (~5.6 km), EPSG:4326.
- License: Public domain / copyright waiver.
- Observation dates: 2019-01-01 to 2020-01-01.
- Local status: verified.
- File: `data\raw\collection\rainfall_2019\rainfall_2019.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'annual_rainfall_mm': 'mm/year', 'valid_days': 'days'}
- Pre-T predictor admission: True.
- Processing/limitations: Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.
- SHA-256: `e6b524dc4f90b176203db20d9c585e9ce1198c9d0892e0013fca48927983c78d`.

AOI valid coverage: annual_rainfall_mm: 100.00%; valid_days: 100.00%.
## rainfall_2020

- Source/version: CHIRPS v2.0 Final daily. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- Native resolution/CRS: 0.05 degrees (~5.6 km), EPSG:4326.
- License: Public domain / copyright waiver.
- Observation dates: 2020-01-01 to 2021-01-01.
- Local status: verified.
- File: `data\raw\collection\rainfall_2020\rainfall_2020.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'annual_rainfall_mm': 'mm/year', 'valid_days': 'days'}
- Pre-T predictor admission: True.
- Processing/limitations: Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.
- SHA-256: `f1fe491c86b9c60f254ef01a21fc8d3f033080ff4c439ceb222e6ffc100bbef0`.

AOI valid coverage: annual_rainfall_mm: 100.00%; valid_days: 100.00%.
## rainfall_2021

- Source/version: CHIRPS v2.0 Final daily. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- Native resolution/CRS: 0.05 degrees (~5.6 km), EPSG:4326.
- License: Public domain / copyright waiver.
- Observation dates: 2021-01-01 to 2022-01-01.
- Local status: verified.
- File: `data\raw\collection\rainfall_2021\rainfall_2021.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'annual_rainfall_mm': 'mm/year', 'valid_days': 'days'}
- Pre-T predictor admission: False.
- Processing/limitations: Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.
- SHA-256: `4382b9355724d1283af096dc126fba46a49529a23090d6738d0696b12fc80349`.

AOI valid coverage: annual_rainfall_mm: 100.00%; valid_days: 100.00%.
## rainfall_2022

- Source/version: CHIRPS v2.0 Final daily. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- Native resolution/CRS: 0.05 degrees (~5.6 km), EPSG:4326.
- License: Public domain / copyright waiver.
- Observation dates: 2022-01-01 to 2023-01-01.
- Local status: verified.
- File: `data\raw\collection\rainfall_2022\rainfall_2022.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'annual_rainfall_mm': 'mm/year', 'valid_days': 'days'}
- Pre-T predictor admission: False.
- Processing/limitations: Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.
- SHA-256: `89bf1c0f54f394a836a8c2ac36a5c6572e41d6fb7cd5cdc47af3b7af0f2c3128`.

AOI valid coverage: annual_rainfall_mm: 100.00%; valid_days: 100.00%.
## rainfall_2023

- Source/version: CHIRPS v2.0 Final daily. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- Native resolution/CRS: 0.05 degrees (~5.6 km), EPSG:4326.
- License: Public domain / copyright waiver.
- Observation dates: 2023-01-01 to 2024-01-01.
- Local status: verified.
- File: `data\raw\collection\rainfall_2023\rainfall_2023.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'annual_rainfall_mm': 'mm/year', 'valid_days': 'days'}
- Pre-T predictor admission: False.
- Processing/limitations: Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.
- SHA-256: `1b29b593d4b351398a604c473b82bee316a74a5b26f38b7ee45210b7285d414d`.

AOI valid coverage: annual_rainfall_mm: 100.00%; valid_days: 100.00%.
## rainfall_2024

- Source/version: CHIRPS v2.0 Final daily. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- Native resolution/CRS: 0.05 degrees (~5.6 km), EPSG:4326.
- License: Public domain / copyright waiver.
- Observation dates: 2024-01-01 to 2025-01-01.
- Local status: verified.
- File: `data\raw\collection\rainfall_2024\rainfall_2024.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'annual_rainfall_mm': 'mm/year', 'valid_days': 'days'}
- Pre-T predictor admission: False.
- Processing/limitations: Sum of daily precipitation; source information remains 0.05 degrees despite 1 km sampling.
- SHA-256: `2bb9c028e28523b019b668438c11ef2c76f0764f1c4e30567d90f52aa0bdefee`.

AOI valid coverage: annual_rainfall_mm: 100.00%; valid_days: 100.00%.
## climate_2019

- Source/version: ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR)
- Native resolution/CRS: 0.1 degrees (~11.1 km), EPSG:4326.
- License: Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data.
- Observation dates: 2019-01-01 to 2020-01-01.
- Local status: verified.
- File: `data\raw\collection\climate_2019\climate_2019.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'temperature_c': 'degrees Celsius', 'soil_moisture_m3_m3': 'm3/m3'}
- Pre-T predictor admission: True.
- Processing/limitations: Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.
- SHA-256: `2264ca67d521e5d6eeab9c9a60e2ec7482933f20bd7c3a75cda5a66cf2ca303f`.

AOI valid coverage: temperature_c: 100.00%; soil_moisture_m3_m3: 100.00%.
## climate_2020

- Source/version: ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR)
- Native resolution/CRS: 0.1 degrees (~11.1 km), EPSG:4326.
- License: Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data.
- Observation dates: 2020-01-01 to 2021-01-01.
- Local status: verified.
- File: `data\raw\collection\climate_2020\climate_2020.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'temperature_c': 'degrees Celsius', 'soil_moisture_m3_m3': 'm3/m3'}
- Pre-T predictor admission: True.
- Processing/limitations: Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.
- SHA-256: `1c2d8047e480e54a457a5ef5d46687b2ea95a754a744e3965b5782eadebb9b24`.

AOI valid coverage: temperature_c: 100.00%; soil_moisture_m3_m3: 100.00%.
## climate_2021

- Source/version: ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR)
- Native resolution/CRS: 0.1 degrees (~11.1 km), EPSG:4326.
- License: Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data.
- Observation dates: 2021-01-01 to 2022-01-01.
- Local status: verified.
- File: `data\raw\collection\climate_2021\climate_2021.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'temperature_c': 'degrees Celsius', 'soil_moisture_m3_m3': 'm3/m3'}
- Pre-T predictor admission: False.
- Processing/limitations: Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.
- SHA-256: `9eef9b27e9b0149cc576ab519313f0fb288c66e106cd89d6dcddcdbb65a6f948`.

AOI valid coverage: temperature_c: 100.00%; soil_moisture_m3_m3: 100.00%.
## climate_2022

- Source/version: ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR)
- Native resolution/CRS: 0.1 degrees (~11.1 km), EPSG:4326.
- License: Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data.
- Observation dates: 2022-01-01 to 2023-01-01.
- Local status: verified.
- File: `data\raw\collection\climate_2022\climate_2022.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'temperature_c': 'degrees Celsius', 'soil_moisture_m3_m3': 'm3/m3'}
- Pre-T predictor admission: False.
- Processing/limitations: Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.
- SHA-256: `12b5e8d4ae275dc1046f46d037382ca269d73ccf49baf4a4361b2aea207c9746`.

AOI valid coverage: temperature_c: 100.00%; soil_moisture_m3_m3: 100.00%.
## climate_2023

- Source/version: ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR)
- Native resolution/CRS: 0.1 degrees (~11.1 km), EPSG:4326.
- License: Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data.
- Observation dates: 2023-01-01 to 2024-01-01.
- Local status: verified.
- File: `data\raw\collection\climate_2023\climate_2023.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'temperature_c': 'degrees Celsius', 'soil_moisture_m3_m3': 'm3/m3'}
- Pre-T predictor admission: False.
- Processing/limitations: Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.
- SHA-256: `84ae45561a0a90b840d07d3c7760fe5a835c9dcc942a8efc83341022e6a650e7`.

AOI valid coverage: temperature_c: 100.00%; soil_moisture_m3_m3: 100.00%.
## climate_2024

- Source/version: ERA5-Land MONTHLY_AGGR (monthly means from hourly reanalysis). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR)
- Native resolution/CRS: 0.1 degrees (~11.1 km), EPSG:4326.
- License: Copernicus C3S/CAMS license; attribute ECMWF/C3S and modified data.
- Observation dates: 2024-01-01 to 2025-01-01.
- Local status: verified.
- File: `data\raw\collection\climate_2024\climate_2024.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'temperature_c': 'degrees Celsius', 'soil_moisture_m3_m3': 'm3/m3'}
- Pre-T predictor admission: False.
- Processing/limitations: Annual mean weighted by days per month; soil layer 0-7 cm. Native ~11 km information is not downscaled by 1 km sampling.
- SHA-256: `4e4bf2f9ff1e029ce00087146f5c8e2712f20560221385a8809f14014430cb81`.

AOI valid coverage: temperature_c: 100.00%; soil_moisture_m3_m3: 100.00%.
## hansen_latest

- Source/version: Hansen GFC v1.13, 2000-2025 (latest verified 2026-10-07). [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2025_v1_13)
- Native resolution/CRS: 0.00025 degrees (~28-31 m), EPSG:4326.
- License: CC-BY-4.0.
- Observation dates: 2000-01-01 to 2025-12-31.
- Local status: verified.
- File: `data\raw\collection\hansen_latest\hansen_latest.tif`.
- Output CRS: EPSG:32643; resolution: 30 m.
- Bands/units: {'treecover2000': 'percent', 'loss': 'binary', 'lossyear': 'year offset from 2000', 'gain': 'binary', 'datamask': 'class'}
- Pre-T predictor admission: False.
- Processing/limitations: Reference/labels only: latest release is forbidden as a historical predictor. Gain covers 2000-2012 only, not through 2025.
- SHA-256: `7b4337bbd948f4a2ec55dd5be0312674e32558263c3d31f624bcefc61d4f0da6`.

AOI valid coverage: treecover2000: 100.00%; loss: 100.00%; lossyear: 2.25%; gain: 100.00%; datamask: 100.00%.
## dem

- Source/version: NASA/USGS SRTMGL1 v003; acquisition February 2000. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003)
- Native resolution/CRS: 1 arc-second (~30 m), EPSG:4326.
- License: Publicly available NASA/JPL data; JPL image-use policy (see catalog).
- Observation dates: 2000-02-11 to 2000-02-22.
- Local status: verified.
- File: `data\raw\collection\dem\dem.tif`.
- Output CRS: EPSG:32643; resolution: 30 m.
- Bands/units: {'elevation': 'm', 'slope': 'degrees', 'aspect': 'degrees clockwise from north'}
- Pre-T predictor admission: True.
- Processing/limitations: SRTM V3 contains auxiliary void filling; conservative auxiliary source bound is configured separately. Flat-area aspect has little meaning.
- SHA-256: `944cd85deb5706fab88611ad3b8d92c22e5bb2e18199e8256504ff82f550f6ca`.

AOI valid coverage: elevation: 100.00%; slope: 100.00%; aspect: 100.00%.
## biomass_gedi

- Source/version: GEDI L4B version 2; 2019-04-18 through 2021-08-04. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/LARSE_GEDI_GEDI04_B_002)
- Native resolution/CRS: ~1 km, EPSG:6933 EASE-Grid 2.0 Global.
- License: Public domain; NASA Earth Science Data policy.
- Observation dates: 2019-04-18 to 2021-08-04.
- Local status: verified.
- File: `data\raw\collection\biomass_gedi\biomass_gedi.tif`.
- Output CRS: EPSG:32643; resolution: 1000 m.
- Bands/units: {'MU': 'Mg dry biomass/ha', 'SE': 'Mg dry biomass/ha', 'QF': 'quality flag', 'NS': 'samples'}
- Pre-T predictor admission: False.
- Processing/limitations: GEDI L4B v2 mean AGBD and standard error; includes 2021 observations: forbidden for T=2020 predictors. Gaps/quality flags are retained.
- SHA-256: `81dc379fa4d1def7940122dff73f06ff31ca5cd19bda3c0ddffcdf5ed3f28f55`.

AOI valid coverage: MU: 31.72%; SE: 31.72%; QF: 100.00%; NS: 100.00%.
QF 1 denotes land; QF 2 meets the GEDI precision requirement. Many land pixels have no MU/SE estimate; do not replace those missing estimates with zero.
## population_2020

- Source/version: WorldPop Global Project country-year 2020, India. [Provider documentation](https://developers.google.com/earth-engine/datasets/catalog/WorldPop_GP_100m_pop)
- Native resolution/CRS: 3 arc-seconds (~93 m at equator), EPSG:4326.
- License: CC-BY-4.0; attribution to WorldPop.
- Observation dates: 2020-01-01 to 2020-12-31.
- Local status: verified.
- File: `data\raw\collection\population_2020\population_2020.tif`.
- Output CRS: EPSG:32643; resolution: 100 m.
- Bands/units: {'population_per_km2': 'people/km2'}
- Pre-T predictor admission: False.
- Processing/limitations: Density derived from native pixel counts; resampling does not exactly conserve population totals. Covariate vintage unverified: not approved as historical predictor.
- SHA-256: `829b8f58e3bf3a3e15e006e9560cd6b9bfb9eea32ddf198ba75a49fba2cfdfd9`.

AOI valid coverage: population_per_km2: 99.71%.
## roads

- Source/version: OpenStreetMap contributors, Overpass historical attic snapshot. [Provider documentation](https://www.openstreetmap.org/copyright)
- Native resolution/CRS: Vector, EPSG:4326; variable positional accuracy.
- License: ODbL-1.0; Ã‚Â© OpenStreetMap contributors.
- Observation dates: 2020-12-31T23:59:59Z to 2020-12-31T23:59:59Z.
- Local status: verified.
- File: `data\raw\collection\roads\roads.gpkg`.
- Output CRS: EPSG:32643; resolution: vector.
- Bands/units: See vector attributes; geometry is the observation.
- Pre-T predictor admission: True.
- Processing/limitations: Snapshot records mapped knowledge at that date, not construction dates. Roads are highway-tagged ways; settlement ways/relations are represented by centres. Incomplete rural coverage is possible.
- SHA-256: `867913d2a1059e600980bdfbfee7f5245709b8265f3ded733f3705b14842931a`.

AOI features: 11430. 
## settlements

- Source/version: OpenStreetMap place-tagged nodes/way centres/relation centres. [Provider documentation](https://www.openstreetmap.org/copyright)
- Native resolution/CRS: Vector points, EPSG:4326; variable completeness.
- License: ODbL-1.0; Ã‚Â© OpenStreetMap contributors.
- Observation dates: 2020-12-31T23:59:59Z to 2020-12-31T23:59:59Z.
- Local status: verified.
- File: `data\raw\collection\settlements\settlements.gpkg`.
- Output CRS: EPSG:32643; resolution: vector.
- Bands/units: See vector attributes; geometry is the observation.
- Pre-T predictor admission: True.
- Processing/limitations: Snapshot records mapped knowledge at that date, not construction dates. Roads are highway-tagged ways; settlement ways/relations are represented by centres. Incomplete rural coverage is possible.
- SHA-256: `957ee4a740d95f45e06d9f7d6e62e80c1d08317745c7d50b638127244ec81319`.

AOI features: 404. 
## mining

- Source/version: Maus et al. global mining polygons version 2, published 2022. [Provider documentation](https://doi.pangaea.de/10.1594/PANGAEA.942325)
- Native resolution/CRS: Vector; primarily 2019 10 m imagery, EPSG:4326.
- License: CC-BY-SA-4.0.
- Observation dates: 2019-01-01 to 2019-12-31.
- Local status: verified.
- File: `data\raw\collection\mining\mining.gpkg`.
- Output CRS: EPSG:32643; resolution: vector.
- Bands/units: See vector attributes; geometry is the observation.
- Pre-T predictor admission: False.
- Processing/limitations: Maus et al. v2 uses 2019 primary imagery plus undated Google/Bing supporting imagery. Mapping was restricted around known mine coordinates; India coverage is not exhaustive, especially unlisted small/artisanal quarries. Empty AOI intersection is not evidence of no mining. Historical predictor use blocked until temporal provenance is reviewed.
- SHA-256: `29709137d61801b467f6d5569321a67bf86270ba58329b0b41fbe917b19d8aed`.

AOI features: 0. Valid empty source intersection; does not prove real-world absence.
## Interpretation and source limitations

SCL masking leaves potential thin cloud/shadow errors; clear_count reports retained granule samples, not unique acquisition dates. Overlapping source tiles can increase the count. Reflectances above 1 are retained and require visual review rather than silent clipping. Hansen tree loss is disturbance, not automatically deforestation. Gain is only 2000-2012. Aspect is circular and must not be averaged as a scalar across north. GEDI MU is mean aboveground dry biomass in Mg/ha, including forest and non-forest; retain SE/QF for uncertainty and quality assessment.

CHIRPS annual totals are sums of daily mm; ERA5 temperature and topsoil water are day-weighted annual means from monthly data. Population density is derived before reprojection, avoiding treating resampled source counts as target-cell counts; exact total preservation is not asserted.

Maus v2 is a reproducible published global footprint source, not an exhaustive Indian mining inventory. Its mapping domain was restricted near known mine coordinates; small unlisted quarries and artisanal sites can be absent. Polygons denote mining-associated land cover, not proof of legal status, activity in a specific year, or cause of forest loss. No national completeness claim is made. Consult local records before prioritizing interventions. Maus v2 was chosen for its stable original polygon download, documented 2019 primary imagery, and permissive attribution/share-alike license. Newer global classifications using Maus/Tang unions also exist (https://www.nature.com/articles/s41597-026-06681-x); those are not claimed to be historical 2020 inventories. No source here is claimed to be a complete Indian mine census.

Contains modified Copernicus Climate Change Service information. Neither the European Commission nor ECMWF is responsible for use of these data. Preserve provider citations/licenses when distributing derivatives. Model outputs describe association; humans decide.


## Historical preprocessing additions

See [PREPROCESSING_DATA_CATALOG.md](PREPROCESSING_DATA_CATALOG.md) for the inputs used by the new forest-node pipeline.
