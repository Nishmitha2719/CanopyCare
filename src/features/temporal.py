"""Pure cutoff-aware forest masks and fail-closed feature provenance checks."""
from __future__ import annotations
from typing import Any
import numpy as np


def history_masks(treecover: np.ndarray, lossyear: np.ndarray, datamask: np.ndarray,
                  cutoff_year: int, canopy_threshold: float, windows: list[int]) -> dict[str, np.ndarray]:
    """Use ONLY loss years 2001..T; future-year substitutions cannot change outputs.

    Fractions are later divided by observed land pixels. Gain/regrowth is excluded.
    Window n includes T-n+1..T (the final observed year is included).
    """
    t = cutoff_year-2000
    valid = np.isfinite(treecover) & np.isfinite(lossyear) & (datamask == 1)
    baseline = valid & (treecover >= canopy_threshold)
    historic = baseline & (lossyear > 0) & (lossyear <= t)
    result = {"valid": valid, "baseline": baseline, "cumulative": historic,
              "remaining": baseline & ~historic}
    for window in windows:
        result[f"last_{window}"] = historic & (lossyear > t-window)
    return result


def target_mask(remaining: np.ndarray, label_lossyear: np.ndarray, label_datamask: np.ndarray,
                cutoff_year: int, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Return future loss and valid-label masks; never return predictor fields."""
    valid = np.isfinite(label_lossyear) & (label_datamask == 1)
    future = remaining & valid & (label_lossyear > cutoff_year-2000) & (label_lossyear <= cutoff_year-2000+horizon)
    return future, valid


def audit_features(registry: dict[str, dict[str, Any]], cutoff: int, sources: dict[str,dict[str,Any]] | None = None) -> None:
    """Reject future/label lineage even when the output name sounds historical."""
    for name, meta in registry.items():
        if meta["status"] == "unavailable":
            continue
        if meta["role"] != "predictor" or not meta.get("predictor_allowed", False):
            raise ValueError(f"Forbidden predictor lineage: {name}")
        end = meta.get("observation_end_year")
        if not isinstance(end, int) or end > cutoff:
            raise ValueError(f"Temporal leakage in {name}: observation end={end}, T={cutoff}")
        if meta.get("max_lossyear_used", cutoff) > cutoff:
            raise ValueError(f"Future lossyear used by {name}")

        if sources is not None:
            dependencies = meta["source"] if isinstance(meta["source"],list) else [meta["source"]]
            for dependency in dependencies:
                if dependency not in sources: raise ValueError(f"Unregistered input {dependency}")
                source = sources[dependency]
                if source.get("reason"): continue # an explicitly unavailable spectral year contributes no data
                if source.get("role") != "predictor" or source["observation_end_year"] > cutoff:
                    raise ValueError(f"Future/label source dependency in {name}: {dependency}")
