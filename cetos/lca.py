"""
Life Cycle Analysis (LCA) comparison of propulsion systems.

Compares diesel (internal combustion), battery-electric, and hydrogen
fuel cell propulsion for a given vessel and voyage, covering:
  - Well-to-Wake operational emissions (WtW)
  - Equipment manufacturing emissions (battery packs, fuel cells, H2 tanks)
  - Equipment replacement over vessel lifetime

All emission factors are loaded from YAML data files in cetos/data/ which
include full provenance metadata (source documents, dates, URLs, pages).
See cetos/data/lca_factors.yaml and cetos/data/emissions_factors.yaml.
"""

from cetos.emissions import (
    estimate_air_pollutant_emissions,
    estimate_well_to_wake_emissions,
)
from cetos.energy_systems import (
    REFERENCE_VALUES,
    estimate_internal_combustion_system,
)
from cetos.factors import (
    BATTERY_LIFETIME_CYCLES,
    BATTERY_MANUFACTURING_FACTORS,
    CHARGING_EFFICIENCY,
    ELECTRIC_MOTOR_EFFICIENCY,
    FUEL_CELL_LIFETIME_HOURS,
    FUEL_CELL_MANUFACTURING_KG_CO2EQ_PER_KW,
    GRID_EMISSION_FACTORS,
    HYDROGEN_LCV_MJ_PER_KG,
    HYDROGEN_TANK_KG_CO2EQ_PER_KG,
    HYDROGEN_WTT_FACTORS,
)
from cetos.imo import estimate_energy_consumption
from cetos.models import VesselData, VoyageProfile


def compare_propulsion_systems(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    vessel_lifetime_years=25,
    voyages_per_year=250,
    grid_source="default",
    hydrogen_source="default",
    battery_type="default",
    reference_values=None,
):
    """Compare diesel, battery-electric, and hydrogen propulsion LCA.

    Takes a diesel vessel definition and voyage profile, then calculates
    the lifecycle emissions for three propulsion alternatives:
      1. Diesel (current configuration) — operational WtW emissions
      2. Battery-electric — grid electricity + battery manufacturing
      3. Hydrogen fuel cell — H2 production + fuel cell manufacturing

    Arguments:
    ----------

        vessel_data: VesselData
            Vessel specification (diesel baseline).

        voyage_profile: VoyageProfile
            Single representative voyage.

        vessel_lifetime_years: int
            Expected vessel service life. Default: 25 years.

        voyages_per_year: int
            Number of voyages per year. Default: 250.

        grid_source: str
            Electricity grid for battery charging. One of the keys in
            GRID_EMISSION_FACTORS. Default: "default" (EU average).

        hydrogen_source: str
            Hydrogen production pathway. One of the keys in
            HYDROGEN_WTT_FACTORS. Default: "default" (grey).

        battery_type: str
            Battery chemistry/origin for manufacturing footprint. One of
            the keys in BATTERY_MANUFACTURING_FACTORS. Default: "default".

        reference_values: dict or None
            Reference hardware specs for battery packs, fuel cells, and
            H2 tanks. If None, uses cetos.energy_systems.REFERENCE_VALUES.

    Returns:
    --------

        Dict with keys "diesel", "battery", "hydrogen", each containing:
            - operational_co2eq_per_voyage_kg
            - operational_co2eq_lifetime_kg
            - manufacturing_co2eq_kg
            - total_lifecycle_co2eq_kg
            - nox_lifetime_kg, sox_lifetime_kg, pm_lifetime_kg
            - system_weight_kg, system_volume_m3
            - details (sub-component breakdown)

        Plus a "comparison" key with relative percentages.
    """
    if reference_values is None:
        reference_values = REFERENCE_VALUES

    total_voyages = vessel_lifetime_years * voyages_per_year

    # --- 1. Diesel baseline ---
    diesel = _calc_diesel(vessel_data, voyage_profile, total_voyages)

    # --- 2. Battery-electric ---
    battery = _calc_battery(
        vessel_data,
        voyage_profile,
        total_voyages,
        vessel_lifetime_years,
        voyages_per_year,
        grid_source,
        battery_type,
        reference_values,
    )

    # --- 3. Hydrogen fuel cell ---
    hydrogen = _calc_hydrogen(
        vessel_data,
        voyage_profile,
        total_voyages,
        vessel_lifetime_years,
        hydrogen_source,
        reference_values,
    )

    # --- Comparison ---
    diesel_total = diesel["total_lifecycle_co2eq_kg"]
    comparison = {
        "diesel_vs_baseline_pct": 100.0,
        "battery_vs_baseline_pct": (
            battery["total_lifecycle_co2eq_kg"] / diesel_total * 100
            if diesel_total > 0
            else 0.0
        ),
        "hydrogen_vs_baseline_pct": (
            hydrogen["total_lifecycle_co2eq_kg"] / diesel_total * 100
            if diesel_total > 0
            else 0.0
        ),
    }

    return {
        "diesel": diesel,
        "battery": battery,
        "hydrogen": hydrogen,
        "comparison": comparison,
        "parameters": {
            "vessel_lifetime_years": vessel_lifetime_years,
            "voyages_per_year": voyages_per_year,
            "total_voyages": total_voyages,
            "grid_source": grid_source,
            "hydrogen_source": hydrogen_source,
            "battery_type": battery_type,
        },
    }


def _calc_diesel(vessel_data, voyage_profile, total_voyages):
    """Calculate diesel propulsion lifecycle emissions."""
    # Operational emissions per voyage
    wtw = estimate_well_to_wake_emissions(vessel_data, voyage_profile)
    air = estimate_air_pollutant_emissions(vessel_data, voyage_profile)
    ice = estimate_internal_combustion_system(vessel_data, voyage_profile)

    co2eq_per_voyage = wtw["wtw_kg_co2eq"]

    return {
        "operational_co2eq_per_voyage_kg": co2eq_per_voyage,
        "operational_co2eq_lifetime_kg": co2eq_per_voyage * total_voyages,
        "manufacturing_co2eq_kg": 0.0,  # Engine manufacturing excluded
        "total_lifecycle_co2eq_kg": co2eq_per_voyage * total_voyages,
        "nox_per_voyage_kg": air["total_kg_nox"],
        "sox_per_voyage_kg": air["total_kg_sox"],
        "pm_per_voyage_kg": air["total_kg_pm"],
        "nox_lifetime_kg": air["total_kg_nox"] * total_voyages,
        "sox_lifetime_kg": air["total_kg_sox"] * total_voyages,
        "pm_lifetime_kg": air["total_kg_pm"] * total_voyages,
        "fuel_per_voyage_kg": wtw["total_fuel_kg"],
        "fuel_lifetime_kg": wtw["total_fuel_kg"] * total_voyages,
        "system_weight_kg": ice["total_weight_kg"],
        "system_volume_m3": ice["total_volume_m3"],
        "ghg_intensity_gco2eq_per_mj": wtw["ghg_intensity_gco2eq_per_mj"],
        "details": {
            "wtt_per_voyage_kg": wtw["wtt_kg_co2eq"],
            "ttw_per_voyage_kg": wtw["ttw_kg_co2eq"],
            "fuel_type": wtw["fuel_type"],
        },
    }


def _calc_battery(
    vessel_data,
    voyage_profile,
    total_voyages,
    vessel_lifetime_years,
    voyages_per_year,
    grid_source,
    battery_type,
    reference_values,
):
    """Calculate battery-electric propulsion lifecycle emissions."""
    # Get energy requirements from the diesel baseline
    energy = estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=False,
        limit_7_percent=False,
        delta_w=0.8,
    )
    required_energy_kwh = energy["total_kwh"]
    required_power_kw = energy["maximum_required_total_power_kw"]

    # Energy from grid (accounting for charging and motor efficiency)
    grid_energy_per_voyage_kwh = required_energy_kwh / (
        CHARGING_EFFICIENCY * ELECTRIC_MOTOR_EFFICIENCY
    )

    # Grid emissions per voyage
    grid_factor = GRID_EMISSION_FACTORS[grid_source]
    operational_co2eq_per_voyage = grid_energy_per_voyage_kwh * grid_factor / 1000.0

    # Battery system sizing (from energy_systems module)
    from cetos.energy_systems import estimate_vessel_battery_system

    battery_system = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        **reference_values,
    )
    battery_capacity_kwh = battery_system["details"]["battery_packs"]["capacity_kwh"]

    # Battery manufacturing emissions
    mfg_factor = BATTERY_MANUFACTURING_FACTORS[battery_type]
    battery_mfg_co2eq = battery_capacity_kwh * mfg_factor

    # Battery replacements over lifetime
    # Each voyage is roughly one cycle (simplification)
    total_cycles = total_voyages
    cycle_life = BATTERY_LIFETIME_CYCLES.get(
        battery_type, BATTERY_LIFETIME_CYCLES["default"]
    )
    num_battery_sets = max(1, total_cycles // cycle_life)
    total_battery_mfg_co2eq = battery_mfg_co2eq * num_battery_sets

    return {
        "operational_co2eq_per_voyage_kg": operational_co2eq_per_voyage,
        "operational_co2eq_lifetime_kg": operational_co2eq_per_voyage * total_voyages,
        "manufacturing_co2eq_kg": total_battery_mfg_co2eq,
        "total_lifecycle_co2eq_kg": (
            operational_co2eq_per_voyage * total_voyages + total_battery_mfg_co2eq
        ),
        "nox_per_voyage_kg": 0.0,
        "sox_per_voyage_kg": 0.0,
        "pm_per_voyage_kg": 0.0,
        "nox_lifetime_kg": 0.0,
        "sox_lifetime_kg": 0.0,
        "pm_lifetime_kg": 0.0,
        "energy_per_voyage_kwh": required_energy_kwh,
        "grid_energy_per_voyage_kwh": grid_energy_per_voyage_kwh,
        "system_weight_kg": battery_system["total_weight_kg"],
        "system_volume_m3": battery_system["total_volume_m3"],
        "details": {
            "battery_capacity_kwh": battery_capacity_kwh,
            "battery_sets_over_lifetime": num_battery_sets,
            "battery_mfg_co2eq_per_set_kg": battery_mfg_co2eq,
            "grid_source": grid_source,
            "grid_factor_gco2eq_per_kwh": grid_factor,
            "charging_efficiency": CHARGING_EFFICIENCY,
            "motor_efficiency": ELECTRIC_MOTOR_EFFICIENCY,
        },
    }


def _calc_hydrogen(
    vessel_data,
    voyage_profile,
    total_voyages,
    vessel_lifetime_years,
    hydrogen_source,
    reference_values,
):
    """Calculate hydrogen fuel cell propulsion lifecycle emissions."""
    # Get energy requirements
    energy = estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=False,
        limit_7_percent=False,
        delta_w=0.8,
    )
    required_energy_kwh = energy["total_kwh"]
    required_power_kw = energy["maximum_required_total_power_kw"]

    # Hydrogen system sizing (from energy_systems module)
    from cetos.energy_systems import estimate_vessel_gas_hydrogen_system

    h2_system = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        **reference_values,
    )
    h2_kg_per_voyage = h2_system["details"]["hydrogen"]["weight_kg"]
    fc_power_kw = h2_system["details"]["fuel_cell_system"]["power_kw"]

    # Hydrogen WtT emissions per voyage
    h2_energy_mj = h2_kg_per_voyage * HYDROGEN_LCV_MJ_PER_KG
    h2_wtt_factor = HYDROGEN_WTT_FACTORS[hydrogen_source]
    operational_co2eq_per_voyage = h2_energy_mj * h2_wtt_factor / 1000.0
    # TtW for hydrogen is zero (water vapor only)

    # Fuel cell manufacturing emissions
    fc_mfg_co2eq = fc_power_kw * FUEL_CELL_MANUFACTURING_KG_CO2EQ_PER_KW

    # Fuel cell replacements over lifetime
    # Estimate operating hours per voyage
    voyage_hours = 0.0
    for leg in voyage_profile.legs_at_sea:
        voyage_hours += leg.distance_nm / leg.speed_kn
    for leg in voyage_profile.legs_manoeuvring:
        voyage_hours += leg.distance_nm / leg.speed_kn
    voyage_hours += voyage_profile.time_anchored_h
    voyage_hours += voyage_profile.time_at_berth_h

    total_operating_hours = voyage_hours * total_voyages
    num_fc_sets = max(1, int(total_operating_hours / FUEL_CELL_LIFETIME_HOURS))
    total_fc_mfg_co2eq = fc_mfg_co2eq * num_fc_sets

    # H2 tank manufacturing — minor, include as fixed estimate
    tank_weight_kg = h2_system["details"]["gas_tanks"]["weight_kg"]
    tank_mfg_co2eq = tank_weight_kg * HYDROGEN_TANK_KG_CO2EQ_PER_KG

    total_mfg = total_fc_mfg_co2eq + tank_mfg_co2eq

    return {
        "operational_co2eq_per_voyage_kg": operational_co2eq_per_voyage,
        "operational_co2eq_lifetime_kg": operational_co2eq_per_voyage * total_voyages,
        "manufacturing_co2eq_kg": total_mfg,
        "total_lifecycle_co2eq_kg": (
            operational_co2eq_per_voyage * total_voyages + total_mfg
        ),
        "nox_per_voyage_kg": 0.0,
        "sox_per_voyage_kg": 0.0,
        "pm_per_voyage_kg": 0.0,
        "nox_lifetime_kg": 0.0,
        "sox_lifetime_kg": 0.0,
        "pm_lifetime_kg": 0.0,
        "h2_per_voyage_kg": h2_kg_per_voyage,
        "h2_lifetime_kg": h2_kg_per_voyage * total_voyages,
        "system_weight_kg": h2_system["total_weight_kg"],
        "system_volume_m3": h2_system["total_volume_m3"],
        "details": {
            "hydrogen_source": hydrogen_source,
            "h2_wtt_factor_gco2eq_per_mj": h2_wtt_factor,
            "fuel_cell_power_kw": fc_power_kw,
            "fuel_cell_sets_over_lifetime": num_fc_sets,
            "fc_mfg_co2eq_per_set_kg": fc_mfg_co2eq,
            "tank_mfg_co2eq_kg": tank_mfg_co2eq,
            "voyage_hours": voyage_hours,
        },
    }
