"""Conditional biomass scenarios, never avoided-emissions estimates."""
from __future__ import annotations
import pandas as pd
from src.config import Config


def carbon_scenario(frame: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Compute stock and a hypothetical loss scenario independently of binary risk."""
    c = cfg["carbon"]
    result = frame[["cell_id"]].copy()
    result["aboveground_carbon_mg"] = (frame.area_ha * frame.forest_fraction
        * c["biomass_mg_per_ha"] * c["carbon_fraction"])
    result["scenario_co2_mass_equivalent_mg"] = (result.aboveground_carbon_mg
        * c["scenario_loss_fraction"] * c["co2_to_c_ratio"])
    return result
