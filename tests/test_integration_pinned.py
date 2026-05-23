"""
Pinning tests for end-to-end integration workflows.

These tests capture complete pipelines combining multiple modules:
- AIS data -> vessel estimation -> fuel consumption -> energy alternatives
- Full workflows that users would typically execute

They serve as comprehensive regression tests during refactoring.
"""

from dataclasses import asdict, is_dataclass
from datetime import datetime

import pytest

from cetos import imo
from cetos.ais_adapter import guesstimate_vessel_data, guesstimate_voyage_data
from cetos.energy_systems import (
    REFERENCE_VALUES,
    suggest_alternative_energy_systems,
)
from cetos.imo import estimate_energy_consumption, estimate_fuel_consumption
from cetos.models import VoyageLeg, VoyageProfile


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
    "ship_type,to_bow,to_stern,to_port,to_starboard,speed,draught,lat,lon,scenario_name",
    [
        (60, 20, 20, 5, 5, 12, 2.8, 56.0, 12.0, "ferry_pax"),
        (80, 150, 50, 15, 15, 14, 12, 57.0, 11.0, "oil_tanker"),
        (70, 100, 50, 11, 12, 16, 8.5, 58.0, 12.5, "general_cargo"),
    ],
)
def test_ais_to_vessel_data_to_fuel_consumption_pinned(
    ship_type,
    to_bow,
    to_stern,
    to_port,
    to_starboard,
    speed,
    draught,
    lat,
    lon,
    scenario_name,
    pinned,
):
    """
    Pin end-to-end workflow: AIS data -> vessel estimation -> fuel consumption.

    This workflow:
    1. Estimates vessel characteristics from AIS data
    2. Creates a minimal voyage profile
    3. Calculates fuel consumption for that voyage

    Returns the complete fuel consumption result.
    """
    # Step 1: Estimate vessel data from AIS
    vessel_data = guesstimate_vessel_data(
        type_of_ship_and_cargo_type=ship_type,
        dim_a=to_bow,
        dim_b=to_stern,
        dim_c=to_port,
        dim_d=to_starboard,
        speed=speed,
        draft=draught,
        latitude=lat,
        longitude=lon,
    )

    # Step 2: Create a simple voyage profile
    voyage_profile = VoyageProfile(
        time_anchored_h=2.0,
        time_at_berth_h=4.0,
        legs_manoeuvring=[VoyageLeg(1, 5, vessel_data.design_draft_m)],
        legs_at_sea=[VoyageLeg(20, speed, vessel_data.design_draft_m)],
    )

    # Step 3: Calculate fuel consumption
    result = estimate_fuel_consumption(vessel_data, voyage_profile)

    assert result == pinned


def test_complete_ferry_workflow_pinned(pinned):
    """
    Pin complete ferry workflow: AIS -> vessel -> voyage -> fuel -> alternatives.

    This comprehensive workflow:
    1. Estimates vessel data from AIS
    2. Estimates voyage data from AIS waypoints
    3. Calculates fuel consumption
    4. Calculates energy consumption
    5. Suggests alternative energy systems

    Returns a dictionary with all results.
    """
    # Step 1: AIS to vessel data
    vessel_data = guesstimate_vessel_data(
        type_of_ship_and_cargo_type=60,  # Ferry
        dim_a=20,
        dim_b=20,
        dim_c=5,
        dim_d=5,
        speed=12,
        draft=2.8,
        latitude=56.0,
        longitude=12.0,
    )

    # Step 2: AIS waypoints to voyage data
    time1 = datetime.fromtimestamp(0)
    time2 = datetime.fromtimestamp(4 * 3600)  # 4 hour voyage

    voyage_data = guesstimate_voyage_data(
        latitude_1=56.0,
        longitude_1=12.0,
        latitude_2=56.2,
        longitude_2=12.3,
        draft_1=2.8,
        draft_2=2.8,
        speed_1=12,
        speed_2=12,
        time_1=time1,
        time_2=time2,
        design_speed=vessel_data.design_speed_kn,
        design_draft=vessel_data.design_draft_m,
    )

    # Step 3: Calculate fuel consumption
    fuel_consumption = estimate_fuel_consumption(vessel_data, voyage_data)

    # Step 4: Calculate energy consumption
    energy_consumption = estimate_energy_consumption(
        vessel_data, voyage_data, include_steam_boilers=False, limit_7_percent=False
    )

    # Step 5: Suggest alternatives
    gas_system, battery_system = suggest_alternative_energy_systems(
        vessel_data, voyage_data, REFERENCE_VALUES, energy_module=imo
    )

    # Combine all results
    result = {
        "vessel_data": vessel_data,
        "voyage_data": voyage_data,
        "fuel_consumption": fuel_consumption,
        "energy_consumption": energy_consumption,
        "gas_system": gas_system,
        "battery_system": battery_system,
    }

    # Convert dataclasses and tuples to dicts/lists for JSON compatibility
    result = _to_json_serializable(result)
    assert result == pinned


# Note: test_complete_cargo_ship_workflow_pinned removed due to engine power constraints
# The general cargo vessel has engine power > 2000 kW which exceeds the
# estimate_internal_combustion_engine limits used in alternative energy system suggestions


# Note: test_complete_tanker_workflow_with_steam_boilers_pinned removed due to engine power constraints
# The oil tanker vessel has engine power > 2000 kW which exceeds the
# estimate_internal_combustion_engine limits used in alternative energy system suggestions


# Note: test_multi_leg_voyage_workflow_pinned removed due to engine power constraints
# The estimated vessel has engine power > 2000 kW which exceeds the
# estimate_internal_combustion_engine limits used in alternative energy system suggestions
