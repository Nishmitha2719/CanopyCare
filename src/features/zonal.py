"""Equal-area pixel-center zonal statistics with explicit valid-coverage masks."""
from __future__ import annotations
from typing import Any
import numpy as np
import rasterio
from rasterio.features import rasterize


class Zones:
    """Rasterize nonoverlapping full squares; aggregate without per-cell raster reads."""
    def __init__(self, grid: Any, dataset: Any) -> None:
        if grid.crs != dataset.crs:
            raise ValueError("Grid/raster CRS mismatch")
        self.count = len(grid)
        self.ids = rasterize([(geom, i+1) for i, geom in enumerate(grid.geometry)],
                             out_shape=(dataset.height, dataset.width), transform=dataset.transform,
                             fill=0, dtype="int32", all_touched=False)
        self.total = np.bincount(self.ids.ravel(), minlength=self.count+1)[1:].astype(float)
        self.pixel_area = abs(dataset.transform.a*dataset.transform.e)
        self.transform = dataset.transform

    def sums(self, values: np.ndarray, valid: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        good = np.isfinite(values) & (self.ids > 0)
        if valid is not None: good &= valid
        ids = self.ids[good]
        counts = np.bincount(ids, minlength=self.count+1)[1:].astype(float)
        sums = np.bincount(ids, weights=values[good], minlength=self.count+1)[1:]
        return sums, counts

    def stats(self, values: np.ndarray, min_coverage: float, valid: np.ndarray | None = None) -> dict[str, np.ndarray]:
        sums, count = self.sums(values, valid)
        square, _ = self.sums(np.square(values, dtype=np.float64), valid)
        mean = divide(sums, count)
        std = np.sqrt(np.maximum(0, divide(square,count)-mean*mean))
        coverage = divide(count, self.total)
        maximum = np.full(self.count+1, -np.inf)
        good = np.isfinite(values) & (self.ids > 0)
        if valid is not None: good &= valid
        np.maximum.at(maximum, self.ids[good], values[good])
        maximum = maximum[1:]
        maximum[~np.isfinite(maximum)] = np.nan
        for array in (mean,std,maximum): array[(coverage < min_coverage) | (count == 0)] = np.nan
        return {"mean": mean, "std": std, "max": maximum, "coverage": coverage}


def divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    result = np.full(np.shape(numerator), np.nan, dtype=float)
    return np.divide(numerator, denominator, out=result, where=denominator > 0)


def read_band(dataset: Any, band: int) -> np.ndarray:
    return dataset.read(band, masked=True).astype("float32").filled(np.nan)


def spectral_indices(bands: dict[str,np.ndarray], settings: dict[str,Any]) -> dict[str,np.ndarray]:
    """Indices of median SR composites, not temporal medians of daily indices."""
    blue, red, nir, swir1, swir2 = (bands[b] for b in ("B2","B4","B8","B11","B12"))
    eps = settings["denominator_epsilon"]
    def ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.divide(a,b,out=np.full_like(a,np.nan),where=np.abs(b)>eps)
    e = settings["evi"]
    result = {"ndvi": ratio(nir-red,nir+red), "nbr": ratio(nir-swir2,nir+swir2),
              "ndmi": ratio(nir-swir1,nir+swir1),
              "evi": e["gain"]*ratio(nir-red,nir+e["red_coefficient"]*red-e["blue_coefficient"]*blue+e["offset"])}
    for name, values in result.items():
        low, high = settings["spectral_ranges"][name]
        values[(values < low) | (values > high)] = np.nan
    return result


def time_summary(values: np.ndarray, years: list[int], min_years: int) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """Per-node OLS slope with actual year spacing; anomaly T minus inclusive mean."""
    good = np.isfinite(values)
    counts = good.sum(axis=1)
    mean = divide(np.nansum(values,axis=1),counts)
    x = np.broadcast_to(np.asarray(years,dtype=float),values.shape)
    xmean = divide(np.where(good,x,0).sum(axis=1),counts)
    dx = x-xmean[:,None]
    numerator = np.where(good,dx*(values-mean[:,None]),0).sum(axis=1)
    denominator = np.where(good,dx*dx,0).sum(axis=1)
    trend = divide(numerator,denominator)
    anomaly = values[:,-1]-mean
    trend[counts < min_years] = np.nan
    anomaly[counts < min_years] = np.nan
    return trend, anomaly, counts
