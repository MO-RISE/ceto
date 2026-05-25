"""
Pinning tests for cetos.energy_systems module.

These tests capture the complete output behavior of energy system estimations
including internal combustion, battery, hydrogen, and alternative energy systems.
They serve as a safety net during refactoring.
"""

from dataclasses import asdict, is_dataclass

import pytest
from fixtures import (
    FERRY_PAX_DAILY_VOYAGE,
    FERRY_PAX_VESSEL,
    OFFSHORE_SHORT_VOYAGE,
    OFFSHORE_VESSEL,
)

from cetos import imo
from cetos.energy_systems import (
    REFERENCE_VALUES,
    estimate_internal_combustion_system,
    estimate_vessel_battery_system,
    estimate_vessel_gas_hydrogen_system,
    suggest_alternative_energy_systems,
    suggest_alternative_energy_systems_simple,
)


def _to_json_serializable(obj):
    """
    Convert dataclasses and tuples to dicts/lists for JSON serialization compatibility.
    pytest-pinned stores results as JSON, which converts tuples to lists.
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        return {key: _to_json_serializable(value) for key, value in asdict(obj).items()}
    elif isinstance(obj, tuple):
        return [_to_json_serializable(item) for item in obj]
    elif isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _to_json_serializable(value) for key, value in obj.items()}
    else:
        return obj


@pytest.mark.parametrize(
    "vessel_data,voyage_profile,scenario_name",
    [
        (FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, "ferry_pax_daily"),
        # OIL_TANKER_VESSEL has engine power > 2000 kW, outside estimate_internal_combustion_engine range
        # GENERAL_CARGO_VESSEL has engine power > 2000 kW, outside estimate_internal_combustion_engine range
        (OFFSHORE_VESSEL, OFFSHORE_SHORT_VOYAGE, "offshore_short"),
        # ROPAX_VESSEL has engine power > 2000 kW, outside estimate_internal_combustion_engine range
    ],
)
def test_estimate_internal_combustion_system_pinned(
    vessel_data, voyage_profile, scenario_name, pinned
):
    """
    Pin complete internal combustion system estimations.

    Captures weight, volume, and fuel details for the ICE system.
    Note: Only tests vessels with engine power <= 2000 kW due to
    estimate_internal_combustion_engine constraints.
    """
    result = estimate_internal_combustion_system(
        vessel_data, voyage_profile, energy_module=imo
    )
    assert result == pinned


@pytest.mark.parametrize(
    "required_energy_kwh,required_power_kw,required_propulsion_power_kw,scenario_name",
    [
        (1_000, 500, 400, "small_system"),
        (10_000, 2_000, 1_600, "medium_system"),
        (50_000, 10_000, 8_000, "large_system"),
        (100_000, 15_000, 12_000, "very_large_system"),
    ],
)
def test_estimate_vessel_battery_system_pinned(
    required_energy_kwh,
    required_power_kw,
    required_propulsion_power_kw,
    scenario_name,
    pinned,
):
    """
    Pin complete battery system estimations for various energy requirements.

    Captures:
    - Total weight and volume
    - Battery pack details (capacity, weight, volume, number of packs)
    - Electrical engine details (power, weight, volume)
    """
    result = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **REFERENCE_VALUES,
    )
    assert result == pinned


@pytest.mark.parametrize(
    "required_energy_kwh,required_power_kw,required_propulsion_power_kw,scenario_name",
    [
        (1_000, 500, 400, "small_system"),
        (10_000, 2_000, 1_600, "medium_system"),
        (50_000, 10_000, 8_000, "large_system"),
        (100_000, 15_000, 12_000, "very_large_system"),
    ],
)
def test_estimate_vessel_gas_hydrogen_system_pinned(
    required_energy_kwh,
    required_power_kw,
    required_propulsion_power_kw,
    scenario_name,
    pinned,
):
    """
    Pin complete hydrogen gas system estimations for various energy requirements.

    Captures:
    - Total weight and volume
    - Hydrogen details (weight, volume)
    - Gas tank details (weight, volume, number of tanks)
    - Fuel cell details (power, weight, volume, number of cells)
    - Electrical engine details (power, weight, volume)
    """
    result = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **REFERENCE_VALUES,
    )
    assert result == pinned


@pytest.mark.parametrize(
    "vessel_data,voyage_profile,scenario_name",
    [
        (FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, "ferry_pax_daily"),
        # OIL_TANKER_VESSEL has engine power > 2000 kW, outside estimate_internal_combustion_engine range
        # GENERAL_CARGO_VESSEL has engine power > 2000 kW, outside estimate_internal_combustion_engine range
        (OFFSHORE_VESSEL, OFFSHORE_SHORT_VOYAGE, "offshore_short"),
    ],
)
def test_suggest_alternative_energy_systems_pinned(
    vessel_data, voyage_profile, scenario_name, pinned
):
    """
    Pin complete alternative energy system suggestions.

    This is the main user-facing function that suggests both hydrogen and battery
    alternatives for a given vessel and voyage profile. Returns a tuple of
    (gas_system, battery_system) with complete details including draft changes.
    Note: Only tests vessels with engine power <= 2000 kW due to internal constraints.
    """
    result = suggest_alternative_energy_systems(
        vessel_data, voyage_profile, REFERENCE_VALUES, energy_module=imo
    )
    # Result is a tuple (gas_system, battery_system) - convert to list for JSON compatibility
    result = _to_json_serializable(result)
    assert result == pinned


@pytest.mark.parametrize(
    "avg_fuel_consumption_lpnm,fuel_type,propulsion_power_kw,voyage_length_nm,scenario_name",
    [
        (5, "MDO", 330, 20, "small_ferry_short"),
        (10, "MDO", 1_000, 100, "medium_vessel_medium"),
        (50, "HFO", 8_000, 1000, "large_tanker_long"),
        (2, "MDO", 500, 50, "small_cargo_medium"),
    ],
)
def test_suggest_alternative_energy_systems_simple_pinned(
    avg_fuel_consumption_lpnm,
    fuel_type,
    propulsion_power_kw,
    voyage_length_nm,
    scenario_name,
    pinned,
):
    """
    Pin alternative energy system suggestions using simplified inputs.

    This simplified API is useful when full vessel data is not available.
    Returns a tuple of (gas_system, battery_system).
    """
    result = suggest_alternative_energy_systems_simple(
        avg_fuel_consumption_lpnm,
        fuel_type,
        propulsion_power_kw,
        voyage_length_nm,
        REFERENCE_VALUES,
    )
    # Convert tuple result to list for JSON compatibility
    result = _to_json_serializable(result)
    assert result == pinned


def test_estimate_battery_system_high_power_density_pinned(pinned):
    """Pin battery system for high power density scenario (low energy, high power)."""
    result = estimate_vessel_battery_system(5_000, 10_000, 8_000, **REFERENCE_VALUES)
    assert result == pinned


def test_estimate_battery_system_high_energy_density_pinned(pinned):
    """Pin battery system for high energy density scenario (high energy, low power)."""
    result = estimate_vessel_battery_system(100_000, 5_000, 4_000, **REFERENCE_VALUES)
    assert result == pinned


def test_estimate_hydrogen_system_high_power_density_pinned(pinned):
    """Pin hydrogen system for high power density scenario (low energy, high power)."""
    result = estimate_vessel_gas_hydrogen_system(
        5_000, 10_000, 8_000, **REFERENCE_VALUES
    )
    assert result == pinned


def test_estimate_hydrogen_system_high_energy_density_pinned(pinned):
    """Pin hydrogen system for high energy density scenario (high energy, low power)."""
    result = estimate_vessel_gas_hydrogen_system(
        100_000, 5_000, 4_000, **REFERENCE_VALUES
    )
    assert result == pinned
