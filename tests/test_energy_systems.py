from ceto.imo import estimate_energy_consumption
from ceto.energy_systems import (
    estimate_vessel_battery_system,
    estimate_vessel_gas_hydrogen_system,
    REFERENCE_VALUES,
    HYDROGEN_ENERGY_DENSITY_KWHPKG,
    estimate_internal_combustion_system,
    suggest_alternative_energy_systems,
    suggest_alternative_energy_systems_simple,
)

DUMMY_VESSEL_DATA = {
    "length": 39.8,  # meters
    "beam": 10.46,  # meteres
    "design_speed": 13.5,  # knots
    "design_draft": 2.84,  # meters
    "double_ended": False,  # True or False
    "number_of_propulsion_engines": 4,
    "propulsion_engine_power": 330,  # per engine kW
    "propulsion_engine_type": "MSD",
    "propulsion_engine_age": "after_2000",
    "propulsion_engine_fuel_type": "MDO",
    "type": "ferry-pax",
    "size": 686,  # GT
}

DUMMY_VOYAGE_PROFILE = {
    "time_anchored": 10.0,  # time
    "time_at_berth": 10.0,  # time
    "legs_manoeuvring": [
        (10, 10, 3),  # distance (nm), speed (kn), draft (m)
    ],
    "legs_at_sea": [(30, 10, 3), (30, 10, 3)],  # distance (nm), speed (kn), draft (m)
}


def test_estimate_vessel_battery_system():
    required_energy_kwh = 10_000
    required_power_kw = 1_000
    system = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        **REFERENCE_VALUES,
    )
    assert system["details"]["battery_packs"]["capacity_kwh"] == required_energy_kwh / (
        REFERENCE_VALUES["reference_battery_pack_depth_of_discharge_pct"] / 100
    )
    assert system["total_weight_kg"] > system["details"]["battery_packs"]["weight_kg"]
    assert system["details"]["electrical_engines"]["power_kw"] == required_power_kw


def test_estimate_vessel_gas_hydrogen_system():
    required_energy_kwh = 10_000
    required_power_kw = 1_000
    system = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        **REFERENCE_VALUES,
    )
    assert (
        system["details"]["hydrogen"]["weight_kg"]
        == required_energy_kwh
        / (REFERENCE_VALUES["reference_fuel_cell_efficiency_pct"] / 100)
        / HYDROGEN_ENERGY_DENSITY_KWHPKG
    )
    assert system["total_weight_kg"] > system["details"]["gas_tanks"]["weight_kg"]
    assert system["details"]["electrical_engines"]["power_kw"] == required_power_kw


def test_suggest_alternative_energy_systems():
    ice = estimate_internal_combustion_system(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)

    energy = estimate_energy_consumption(
        DUMMY_VESSEL_DATA,
        DUMMY_VOYAGE_PROFILE,
        include_steam_boilers=False,
        limit_7_percent=False,
        delta_w=0.8,
    )

    battery_o = estimate_vessel_battery_system(
        energy["total_kwh"],
        energy["maximum_required_total_power_kw"],
        **REFERENCE_VALUES,
    )
    gas_o = estimate_vessel_gas_hydrogen_system(
        energy["total_kwh"],
        energy["maximum_required_total_power_kw"],
        **REFERENCE_VALUES,
    )

    gas, battery = suggest_alternative_energy_systems(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE, REFERENCE_VALUES
    )

    assert ice["total_weight_kg"] != battery["total_weight_kg"]
    assert ice["total_weight_kg"] != gas["total_weight_kg"]

    # If the draft change is lower than 1% of the design draft there should be no
    # differences
    if abs(battery["change_in_draft_m"]) < DUMMY_VESSEL_DATA["design_draft"] * 0.01:
        assert battery_o["total_weight_kg"] == battery["total_weight_kg"]
    else:
        assert battery_o["total_weight_kg"] != battery["total_weight_kg"]

    if abs(gas["change_in_draft_m"]) < DUMMY_VESSEL_DATA["design_draft"] * 0.01:
        assert gas_o["total_weight_kg"] == gas["total_weight_kg"]
    else:
        assert gas_o["total_weight_kg"] != gas["total_weight_kg"]


def test_suggest_alternative_energy_systems_simple():
    average_fuel_consumption_lpnm = 10
    propulsion_engine_fuel_type = "MDO"
    propulsion_power_kw = 330
    total_voyage_length_nm = 60

    gas, battery = suggest_alternative_energy_systems_simple(
        average_fuel_consumption_lpnm,
        propulsion_engine_fuel_type,
        propulsion_power_kw,
        total_voyage_length_nm,
        REFERENCE_VALUES,
    )

    assert gas["total_weight_kg"] != 0.0
    assert battery["total_weight_kg"] != 0.0
