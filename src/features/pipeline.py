"""Build reproducible 1 km forest nodes from verified historical source rasters."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree
from shapely import STRtree
from src.config import Config, load_config, public_config, write_json
from src.data.exporting import area_geometry, file_hash
from src.data.grid import make_grid
from src.features.temporal import audit_features, history_masks, target_mask
from src.features.zonal import Zones, divide, read_band, spectral_indices, time_summary


class Builder:
    """Track every source digest and per-feature temporal lineage during extraction."""
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.p = cfg["preprocessing"]
        self.root = Path(cfg["_root"])
        self.t = cfg["time"]["prediction_start_year"]
        self.years = list(range(self.t-self.p["spectral_lookback_years"]+1,self.t+1))
        _, self.aoi, _ = area_geometry(cfg)
        self.grid = make_grid(cfg)
        self.grid["node_id"] = self.grid.cell_id
        size = cfg["grid"]["cell_size_m"]
        self.grid["row"] = ((self.grid.y_m-self.grid.y_m.min())/size).round().astype(int)
        self.grid["col"] = ((self.grid.x_m-self.grid.x_m.min())/size).round().astype(int)
        centroids = self.grid.geometry.centroid.to_crs(4326)
        self.grid["centroid_lon"] = centroids.x
        self.grid["centroid_lat"] = centroids.y
        self.grid["aoi_fraction"] = self.grid.geometry.intersection(self.aoi).area / self.grid.geometry.area
        self.frame = pd.DataFrame(self.grid.drop(columns="geometry"))
        self.boundary_distance = self.grid.geometry.centroid.distance(self.aoi.boundary).to_numpy()
        self.registry: dict[str,dict[str,Any]] = {}
        self.sources: dict[str,dict[str,Any]] = {}
        self.quality_columns: list[str] = ["aoi_fraction"]

    def source(self, name: str, *, labels: bool = False) -> tuple[Path,dict[str,Any]]:
        """Read/hash-check original metadata, fail closed on date or approval mismatch."""
        candidates = [self.root/self.p["input_directory"]/name,
                      self.root/self.cfg["collection"]["raw_directory"]/name]
        directory = next((x for x in candidates if (x/"metadata.json").exists()),None)
        if directory is None: raise FileNotFoundError(f"Missing input {name}; run src.features.prepare")
        meta = json.loads((directory/"metadata.json").read_text())
        path = self.root/meta["file"]
        if meta.get("status") != "complete" or file_hash(path) != meta["sha256"]:
            raise ValueError(f"Incomplete or modified source {name}")
        end = meta.get("metadata",{}).get("observation_end_year")
        if end is None:
            end = int(meta["end"][:4])
            if meta["end"].endswith("-01-01") and name.startswith(("climate_","rainfall_","rain_season_")):
                end -= 1
        meta["observation_end_year"] = end
        if not labels and (not meta.get("predictor_allowed") or end > self.t):
            raise ValueError(f"Source {name} is forbidden at T={self.t}")
        if labels and name != "labels": raise ValueError("Only dedicated label source may bypass cutoff")
        if name == "history" and meta["source"] != self.cfg["earth_engine"]["feature_asset"]:
            raise ValueError("Wrong Hansen historical release")
        if name == "labels" and meta["source"] != self.cfg["earth_engine"]["label_asset"]:
            raise ValueError("Wrong Hansen label release")
        self.sources[name] = {"file": str(path.relative_to(self.root)), "sha256": meta["sha256"],
                              "source": meta["source"], "observation_end_year": end, "role": "labels" if labels else "predictor"}
        return path,meta

    def add(self, name: str, values: Any, source: str | list[str], units: str,
            end: int | None = None, note: str = "", available: bool = True) -> None:
        self.frame[name] = values
        self.registry[name] = {"source": source, "units": units, "observation_end_year": end if end is not None else self.t,
                               "role": "predictor", "predictor_allowed": available,
                               "status": "available" if available else "unavailable", "definition": note}
        if source == "history": self.registry[name]["max_lossyear_used"] = self.t

    def history(self) -> None:
        """Historical masks determine forest eligibility; future masks determine only y."""
        path,_ = self.source("history")
        with rasterio.open(path) as src:
            z = Zones(self.grid,src)
            cover,year,land = (read_band(src,i) for i in (1,2,3))
            masks = history_masks(cover,year,land,self.t,self.cfg["forest"]["canopy_threshold_pct"],self.p["history_windows_years"])
            counts = {key:z.sums(value.astype(float))[0] for key,value in masks.items()}
            self.frame["history_valid_fraction"] = divide(counts["valid"],z.total)
            self.quality_columns.append("history_valid_fraction")
            self.add("forest_fraction_2000",divide(counts["baseline"],counts["valid"]),"history","fraction of valid land")
            self.add("forest_fraction_T",divide(counts["remaining"],counts["valid"]),"history","fraction of valid land",note="Baseline canopy minus loss through T; excludes regrowth")
            self.add("cumulative_loss_fraction",divide(counts["cumulative"],counts["valid"]),"history","fraction of valid land")
            for window in self.p["history_windows_years"]:
                self.add(f"loss_last_{window}y_fraction",divide(counts[f"last_{window}"],counts["valid"]),"history","fraction of valid land",note=f"Loss in {self.t-window+1}..{self.t}, inclusive")
            max_window = max(self.p["history_windows_years"])
            self.add("loss_rate_per_year",self.frame[f"loss_last_{max_window}y_fraction"]/max_window,"history","land fraction/year",note=f"Last {max_window} year loss fraction divided by {max_window}; not a fitted trend")
            self.add("forest_area_T_ha",counts["remaining"]*z.pixel_area/10000,"history","ha",note="Approximate sum of UTM pixel areas")
            rows,cols = np.where(masks["cumulative"])
            if len(rows):
                xs,ys = rasterio.transform.xy(src.transform,rows,cols)
                distance = cKDTree(np.column_stack((xs,ys))).query(self.grid[["x_m","y_m"]].to_numpy())[0]
            else: distance = np.full(len(self.grid),np.nan)
            censored = ~np.isfinite(distance) | (distance > self.boundary_distance)
            distance[censored] = np.nan
            self.add("distance_to_loss_m",distance,"history","m",note="Centroid to nearest baseline-forest historical loss pixel center; AOI-boundary censored")
            self.frame["loss_distance_censored"] = censored
            self.quality_columns.append("loss_distance_censored")
            label_path,_ = self.source("labels",labels=True)
            with rasterio.open(label_path) as labels:
                if labels.transform != src.transform or labels.shape != src.shape or labels.crs != src.crs:
                    raise ValueError("Historical and label raster grids differ")
                future,label_valid = target_mask(masks["remaining"],read_band(labels,1),read_band(labels,2),self.t,self.cfg["time"]["horizon_years"])
                lost,_ = z.sums(future.astype(float))
                observed,_ = z.sums((label_valid & masks["remaining"]).astype(float))
                self.frame["label_valid_forest_fraction"] = divide(observed,counts["remaining"])
                self.frame["future_loss_area_ha"] = lost*z.pixel_area/10000
                self.frame["future_loss_fraction"] = divide(lost,counts["remaining"])
                valid_label = (self.frame.label_valid_forest_fraction >= self.p["min_label_forest_coverage"]) & (counts["remaining"] > 0)
                self.frame["y"] = np.where(valid_label, (self.frame.future_loss_fraction >= self.cfg["forest"]["loss_threshold_fraction"]).astype(float),np.nan)

    def spectral(self) -> None:
        for year in self.years:
            name = f"sentinel2_{year}"
            unavailable = self.root/self.p["input_directory"]/name/"unavailable.json"
            if unavailable.exists():
                reason = json.loads(unavailable.read_text())
                self.sources[name] = reason
                for index in self.p["spectral_ranges"]:
                    for stat in ("mean","std"):
                        self.add(f"{index}_{stat}_{year}",np.nan,name,"index",year,reason["reason"],available=False)
                continue
            path,_ = self.source(name)
            with rasterio.open(path) as src:
                z = Zones(self.grid,src)
                bands = {b:read_band(src,src.descriptions.index(b)+1) for b in ("B2","B4","B8","B11","B12")}
                indices = spectral_indices(bands,self.p)
                for index,values in indices.items():
                    stats = z.stats(values,self.p["min_zonal_valid_fraction"])
                    for stat in ("mean","std"):
                        self.add(f"{index}_{stat}_{year}",stats[stat],name,"index",year,"Spatial statistic of dry-season median reflectance index")
                    column = f"{index}_coverage_{year}"
                    self.frame[column] = stats["coverage"]
                    self.quality_columns.append(column)
            print(f"Zonal spectral {year}",flush=True)
        values = self.frame[[f"ndvi_mean_{y}" for y in self.years]].to_numpy()
        trend,anomaly,count = time_summary(values,self.years,self.p["min_trend_years"])
        sources = [f"sentinel2_{y}" for y in self.years]
        self.add("ndvi_trend_per_year",trend,sources,"index/year",note="OLS slope against actual year; at least configured min_trend_years")
        self.add("ndvi_anomaly",anomaly,sources,"index",note="NDVI at T minus available-year mean in T-3..T, at least min_trend_years")
        self.frame["ndvi_years_available"] = count
        self.quality_columns.append("ndvi_years_available")

    def terrain(self) -> None:
        path,_ = self.source("dem")
        with rasterio.open(path) as src:
            z = Zones(self.grid,src)
            elevation,slope,aspect = (read_band(src,i) for i in (1,2,3))
            end = self.cfg["earth_engine"]["elevation_source_end_year"]
            self.add("elevation_mean_m",z.stats(elevation,self.p["min_zonal_valid_fraction"])["mean"],"dem","m",end)
            stats = z.stats(slope,self.p["min_zonal_valid_fraction"])
            for kind in ("mean","max"): self.add(f"slope_{kind}_deg",stats[kind],"dem","degrees",end)
            good = np.isfinite(aspect) & (slope >= self.p["flat_slope_degrees"])
            sin = z.stats(np.sin(np.deg2rad(aspect)),0,good)["mean"]
            cos = z.stats(np.cos(np.deg2rad(aspect)),0,good)["mean"]
            resultant = np.hypot(sin,cos)
            direction_sin,direction_cos = divide(sin,resultant),divide(cos,resultant)
            invalid = (resultant < self.p["circular_resultant_min"]) | (stats["coverage"] < self.p["min_zonal_valid_fraction"])
            direction_sin[invalid] = np.nan; direction_cos[invalid] = np.nan
            self.add("aspect_sin",direction_sin,"dem","unitless",end,"Sine of circular mean direction on non-flat pixels")
            self.add("aspect_cos",direction_cos,"dem","unitless",end,"Cosine of circular mean direction on non-flat pixels")
            self.add("aspect_resultant",resultant,"dem","unitless",end,"Circular concentration; 0 ambiguous, 1 aligned")

    def climate(self) -> None:
        import calendar
        for year in self.years:
            name = f"rain_season_{year}"
            path,_ = self.source(name)
            with rasterio.open(path) as src:
                z = Zones(self.grid,src)
                for i,season in ((1,"annual"),(3,"dry"),(5,"wet")):
                    expected = 365+calendar.isleap(year) if season == "annual" else sum(calendar.monthrange(year,m)[1] for m in self.p[f"{season}_months"])
                    values = read_band(src,i); valid = read_band(src,i+1) == expected
                    self.add(f"{season}_rainfall_mm_{year}",z.stats(values,self.p["min_zonal_valid_fraction"],valid)["mean"],name,"mm",year)
            name = f"climate_{year}"
            path,_ = self.source(name)
            with rasterio.open(path) as src:
                z = Zones(self.grid,src)
                for i,band in enumerate(src.descriptions,1):
                    self.add(f"{band}_{year}",z.stats(read_band(src,i),self.p["min_zonal_valid_fraction"])["mean"],name,"degrees C" if "temperature" in band else "m3/m3",year)
        values = self.frame[[f"annual_rainfall_mm_{year}" for year in self.years]].to_numpy()
        _,anomaly,_ = time_summary(values,self.years,len(self.years))
        self.add("rainfall_anomaly_mm",anomaly,[f"rain_season_{y}" for y in self.years],"mm",note="T annual rainfall minus complete T-3..T mean; not a long-term climate normal")

    def vector_features(self, vector: gpd.GeoDataFrame, source: str, *, roads: bool = False, mines: bool = False) -> None:
        if vector.crs is None: raise ValueError("Vector source has no CRS")
        vector = vector.to_crs(self.grid.crs)
        if not vector.is_valid.all(): raise ValueError("Invalid vector geometry")
        tree = STRtree(vector.geometry.to_numpy())
        # Union intersection geometries avoids double-counting duplicate/overlapping roads or mines.
        density = []
        if roads or mines:
            from shapely import union_all
            for polygon in self.grid.geometry:
                index = tree.query(polygon,predicate="intersects")
                clipped = union_all([vector.geometry.iloc[i].intersection(polygon) for i in index])
                density.append(clipped.length/1000 if roads else clipped.area/polygon.area)
            self.add("road_density_km_km2" if roads else "mining_area_fraction",density,source,"km/km2" if roads else "fraction",note="Mapped union length/area within the full 1 km square; OSM completeness not guaranteed")
        if len(vector):
            points = self.grid.geometry.centroid.to_numpy()
            nearest = tree.nearest(points)
            from shapely import distance
            distances = distance(points,vector.geometry.to_numpy()[nearest])
        else: distances = np.full(len(self.grid),np.nan)
        censored = ~np.isfinite(distances) | (distances > self.boundary_distance)
        distances[censored] = np.nan
        kind = "road" if roads else "mine" if mines else "village"
        self.add(f"distance_to_{kind}_m",distances,source,"m",note="Nearest mapped object from centroid; distances beyond AOI boundary distance are censored")
        self.frame[f"{kind}_distance_censored"] = censored
        self.quality_columns.append(f"{kind}_distance_censored")

    def human(self) -> None:
        for name in ("roads","settlements"):
            path,_ = self.source(name)
            vector = gpd.read_file(path)
            tag_key = "highway" if name == "roads" else "place"
            allowed = self.p["road_highway_types" if name == "roads" else "village_place_types"]
            tag_values = vector.tags_json.map(lambda text: json.loads(text).get(tag_key))
            vector = vector.loc[tag_values.isin(allowed)].copy()
            self.sources[name]["selected_features"] = len(vector)
            self.sources[name]["tag_filter"] = {tag_key:allowed}
            self.vector_features(vector,name,roads=name == "roads")
        self.optional("biomass",["agb_mean_mg_ha","carbon_mean_mg_ha"],"Mg/ha",
                      "GEDI includes observations after T; no approved historical AGB raster")
        self.optional("population",["population_density_per_km2"],"people/km2",
                      "WorldPop covariate vintage unverified; population year alone is insufficient")
        self.optional("mining",["distance_to_mine_m","mining_area_fraction"],"m / fraction",
                      "Maus v2 has undated supporting imagery; zero mapped intersections is not evidence of no mines")

    def optional(self, kind: str, columns: list[str], units: str, reason: str) -> None:
        setting = self.p[f"vetted_{kind}"]
        if setting is None:
            for column in columns: self.add(column,np.nan,f"unavailable_{kind}",units,note=reason,available=False)
            return
        meta = json.loads((self.root/setting["metadata"]).read_text())
        end = meta["observation_end_year"]
        if not isinstance(end,int) or end > self.t or not meta["predictor_allowed"]:
            raise ValueError(f"Unapproved optional {kind} vintage")
        path = self.root/setting["path"]
        if file_hash(path) != meta["sha256"]: raise ValueError("Vetted input digest mismatch")
        self.sources[f"vetted_{kind}"] = meta | {"file":str(path.relative_to(self.root)),"role":"predictor"}
        if kind == "mining": self.vector_features(gpd.read_file(path),f"vetted_{kind}",mines=True)
        else:
            if meta["units"] != ("Mg/ha" if kind == "biomass" else "people/km2"): raise ValueError("Unexpected optional raster units")
            with rasterio.open(path) as src:
                z = Zones(self.grid,src)
                values = read_band(src,1)
                values[values < 0] = np.nan
                means = z.stats(values,self.p["min_zonal_valid_fraction"])["mean"]
                self.add(columns[0],means,f"vetted_{kind}",units,end,meta.get("notes",""))
                if kind == "biomass": self.add(columns[1],means*self.cfg["carbon"]["carbon_fraction"],f"vetted_{kind}","Mg C/ha",end,"AGB density times configured carbon fraction; no soil/belowground carbon")
        for column in columns:
            self.registry[column]["observation_end_year"] = end
            self.registry[column]["definition"] += " " + meta.get("notes", "")

    def run(self) -> dict[str,Any]:
        self.history(); print("Historical features and separate future targets ready",flush=True)
        self.spectral(); self.terrain(); self.climate()
        self.frame = self.frame.copy()
        self.human()
        audit_features(self.registry,self.t,self.sources)
        checks = {
            "aoi_coverage":self.frame.aoi_fraction >= self.p["min_aoi_fraction"],
            "historical_coverage":self.frame.history_valid_fraction >= self.cfg["forest"]["min_valid_fraction"],
            "forested_at_T":self.frame.forest_fraction_T >= self.cfg["forest"]["min_forest_fraction"],
            "label_coverage":self.frame.y.notna(),
        }
        eligible = np.logical_and.reduce(list(checks.values()))
        output = self.root/self.p["output_directory"]; output.mkdir(parents=True,exist_ok=True)
        eligibility = self.frame[["node_id","aoi_fraction","history_valid_fraction","forest_fraction_T","label_valid_forest_fraction"]].copy()
        for name,values in checks.items(): eligibility[name] = values
        eligibility["retained"] = eligible
        eligibility.to_csv(output/"grid_eligibility.csv",index=False)
        nodes = self.frame.loc[eligible].copy()
        nodes["y"] = nodes.y.astype("int8")
        if nodes.empty or nodes.node_id.duplicated().any(): raise ValueError("Empty or duplicate node table")
        if not np.isfinite(nodes[["future_loss_fraction","forest_fraction_T"]].to_numpy()).all(): raise ValueError("Non-finite labels/forest eligibility")
        gpkg = output/"forest_nodes.gpkg"
        gpd.GeoDataFrame(nodes,geometry=self.grid.geometry.loc[eligible],crs=self.grid.crs).to_file(gpkg,layer="forest_nodes",driver="GPKG")
        self.grid.to_file(output/"grid_all.gpkg",layer="grid",driver="GPKG")
        nodes.to_csv(output/"forest_nodes.csv",index=False)
        nodes.to_parquet(output/"forest_nodes.parquet",index=False)
        all_missing = [x for x in self.registry if nodes[x].isna().all()]
        constant = [x for x in self.registry if nodes[x].nunique(dropna=True) <= 1 and x not in all_missing]
        active = [x for x in self.registry if self.registry[x]["predictor_allowed"]]
        manifest = {"cutoff_year":self.t,"target_start_year":self.t+1,"target_end_year":self.t+self.cfg["time"]["horizon_years"],
                    "target_definition":"Loss area / forest remaining at T >= configured threshold; only baseline forest loss counts",
                    "target_threshold":self.cfg["forest"]["loss_threshold_fraction"],
                    "temporal_mode":self.cfg["time"]["temporal_mode"],"features":self.registry,"sources":self.sources,
                    "model_features":active,"all_missing_features":all_missing,"constant_features":constant,
                    "quality_columns":self.quality_columns,"label_columns":["y","future_loss_fraction","future_loss_area_ha","label_valid_forest_fraction"],
                    "grid_count":len(self.grid),"node_count":len(nodes),"exclusion_counts_nonexclusive":{k:int((~v).sum()) for k,v in checks.items()},
                    "aoi_sha256":file_hash(self.root/self.cfg["study_area"]["shapefile"]),
                    "code_sha256":{p.name:file_hash(p) for p in (self.root/"src/features").glob("*.py")},
                    "config":public_config(self.cfg),"outputs":{p.name:file_hash(p) for p in (output/"forest_nodes.csv",output/"forest_nodes.parquet",gpkg)},
                    "leakage_audit":"passed"}
        write_json(output/"feature_manifest.json",manifest)
        from src.features.quality import report
        report(nodes,manifest,self.cfg)
        print(json.dumps({"grid_cells":len(self.grid),"forest_nodes":len(nodes),"positive_nodes":int(nodes.y.sum()),"all_missing_features":all_missing,"output":str(output)},indent=2))
        return manifest


def validate_settings(cfg: Config) -> None:
    p = cfg["preprocessing"]
    if p["spectral_lookback_years"] != 4: raise ValueError("Requested spectral window is exactly T-3..T")
    if set(p["dry_months"]) & set(p["wet_months"]) or sorted(p["dry_months"]+p["wet_months"]) != list(range(1,13)):
        raise ValueError("Dry/wet months must partition the year")
    for key in ("min_aoi_fraction","min_zonal_valid_fraction","min_label_forest_coverage"):
        if not 0 < p[key] <= 1: raise ValueError(f"Invalid {key}")
    expected = {"hansen_masked_lossyear":"no_recorded_loss_where_datamask_land",
                "pixel_inclusion":"center","history_fraction_denominator":"valid_land_area",
                "target_fraction_denominator":"forest_remaining_at_T","nearest_distance_origin":"cell_centroid",
                "nearest_loss_geometry":"pixel_center","distance_boundary_policy":"missing_if_nearest_may_lie_outside_AOI",
                "anomaly_baseline":"inclusive_T_minus_3_to_T","imputation":"training_fold_median_with_missing_indicators"}
    for key,value in expected.items():
        if p[key] != value: raise ValueError(f"Unsupported preprocessing policy: {key}")
    if not 2 <= p["min_trend_years"] <= p["spectral_lookback_years"]: raise ValueError("Invalid trend minimum")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",default="config.yaml")
    parser.add_argument("--prepare",action="store_true",help="Acquire missing historical inputs first")
    args = parser.parse_args()
    cfg = load_config(args.config); validate_settings(cfg)
    if args.prepare:
        from src.features.prepare import prepare
        from src.features.biomass_archive import collect as biomass
        from src.features.historical_human import population, mining
        prepare(cfg)
        if cfg["preprocessing"]["vetted_biomass"]: biomass(cfg)
        if cfg["preprocessing"]["vetted_population"]: population(cfg)
        if cfg["preprocessing"]["vetted_mining"]: mining(cfg)
    Builder(cfg).run()

if __name__ == "__main__": main()
