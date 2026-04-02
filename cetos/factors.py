"""Load emission factors from YAML data files.

All emission factors used by cetos.emissions and cetos.lca are stored in
YAML files under cetos/data/ with full provenance metadata. This module
loads them once at import time and exposes them as plain Python dicts,
preserving the same data structures the rest of the codebase expects.
"""

from pathlib import Path

import yaml

_DATA_DIR = Path(__file__).parent / "data"


def _load_yaml(filename):
    """Load and return a YAML file from the data directory."""
    with open(_DATA_DIR / filename) as f:
        return yaml.safe_load(f)


# ---- Load raw YAML --------------------------------------------------------

_emissions = _load_yaml("emissions_factors.yaml")
_lca = _load_yaml("lca_factors.yaml")

# ---- Emissions factors (cetos.emissions) -----------------------------------

GWP_CH4 = _emissions["gwp"]["CH4"]
GWP_N2O = _emissions["gwp"]["N2O"]

# Remove 'source' key from factor dicts to get clean value mappings
CO2_FACTORS = {k: v for k, v in _emissions["co2_factors"].items() if k != "source"}
LCV = {k: v for k, v in _emissions["lcv"].items() if k != "source"}
WTT_FACTORS = {k: v for k, v in _emissions["wtt_factors"].items() if k != "source"}
SOX_FACTORS = {k: v for k, v in _emissions["sox_factors"].items() if k != "source"}
PM_FACTORS = {k: v for k, v in _emissions["pm_factors"].items() if k != "source"}

# CH4 factors: expand into (engine_type, fuel_type) tuples
_ch4_raw = _emissions["ch4_factors"]
_CH4_OIL = _ch4_raw["oil_default"]
_CH4_LNG_OTTO_MS = _ch4_raw["LNG-Otto-MS"]
_CH4_LBSI = _ch4_raw["LBSI"]
_CH4_LNG_NEGLIGIBLE = _ch4_raw["LNG_negligible"]

# N2O factors
_n2o_raw = _emissions["n2o_factors"]
_N2O_OIL = _n2o_raw["oil_default"]
_N2O_LNG = _n2o_raw["LNG"]

# NOx factors: flatten nested dict into (engine_type, engine_age) tuples
_nox_raw = _emissions["nox_factors"]
NOX_FACTORS = {}
for engine_type, ages in _nox_raw.items():
    if engine_type == "source":
        continue
    for age, value in ages.items():
        NOX_FACTORS[(engine_type, age)] = value

# ---- LCA factors (cetos.lca) ----------------------------------------------

_batt_mfg = _lca["battery_manufacturing"]
BATTERY_MANUFACTURING_FACTORS = _batt_mfg["factors"]

_batt_life = _lca["battery_lifetime_cycles"]
BATTERY_LIFETIME_CYCLES = _batt_life["factors"]

_fc = _lca["fuel_cell_manufacturing"]
FUEL_CELL_MANUFACTURING_KG_CO2EQ_PER_KW = _fc["kg_co2eq_per_kw"]
FUEL_CELL_LIFETIME_HOURS = _fc["lifetime_hours"]

_h2_tank = _lca["hydrogen_tank_manufacturing"]
HYDROGEN_TANK_KG_CO2EQ_PER_KG = _h2_tank["kg_co2eq_per_kg_tank"]

_h2_wtt = _lca["hydrogen_wtt"]
HYDROGEN_WTT_FACTORS = _h2_wtt["factors"]
HYDROGEN_LCV_MJ_PER_KG = _h2_wtt["lcv_mj_per_kg"]

_grid = _lca["grid_emission_factors"]
GRID_EMISSION_FACTORS = _grid["factors"]

CHARGING_EFFICIENCY = _lca["charging_efficiency"]
ELECTRIC_MOTOR_EFFICIENCY = _lca["electric_motor_efficiency"]
