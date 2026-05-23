import pytest

from cetos import imo
from cetos.energy_systems import (
    HYDROGEN_ENERGY_DENSITY_KWHPKG,
    REFERENCE_VALUES,
    estimate_internal_combustion_system,
    estimate_vessel_battery_system,
    estimate_vessel_gas_hydrogen_system,
    suggest_alternative_energy_systems,
    suggest_alternative_energy_systems_simple,
)
from cetos.imo import estimate_energy_consumption
from cetos.models import VesselData, VoyageLeg, VoyageProfile

DUMMY_VESSEL_DATA = VesselData(
    length_m=39.8,
    beam_m=10.46,
    design_speed_kn=13.5,
    design_draft_m=2.84,
    double_ended=False,
    number_of_propulsion_engines=4,
    propulsion_engine_power_kw=330,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="ferry-pax",
    size=686,
)

DUMMY_VOYAGE_PROFILE = VoyageProfile(
    time_anchored_h=10.0,
    time_at_berth_h=10.0,
    legs_manoeuvring=[
        VoyageLeg(10, 10, 3),  # distance (nm), speed (kn), draft (m)
    ],
    legs_at_sea=[
        VoyageLeg(30, 10, 3),
        VoyageLeg(30, 10, 3),
    ],
)


def test_estimate_vessel_battery_system():
    required_energy_kwh = 10_000
    required_power_kw = 1_000
    required_propulsion_power_kw = 800
    system = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **REFERENCE_VALUES,
    )
    assert system["details"]["battery_packs"]["capacity_kwh"] == pytest.approx(
        required_energy_kwh
        / (REFERENCE_VALUES["reference_battery_pack_depth_of_discharge_pct"] / 100)
    )
    assert system["total_weight_kg"] > system["details"]["battery_packs"]["weight_kg"]
    assert (
        system["details"]["electrical_engines"]["power_kw"]
        == required_propulsion_power_kw
    )


def test_estimate_vessel_battery_system_power_bound():
    # Low energy, high power demand: pack count is dictated by power, not energy.
    required_energy_kwh = 100
    required_power_kw = 5_000
    required_propulsion_power_kw = 4_000
    system = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **REFERENCE_VALUES,
    )
    expected_packs = (
        required_power_kw
        / REFERENCE_VALUES["reference_battery_pack_continuous_power_kw"]
    )
    assert system["details"]["battery_packs"]["capacity_kwh"] == pytest.approx(
        expected_packs * REFERENCE_VALUES["reference_battery_pack_capacity_kwh"]
    )


def test_estimate_vessel_gas_hydrogen_system():
    required_energy_kwh = 10_000
    required_power_kw = 1_000
    required_propulsion_power_kw = 800
    system = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **REFERENCE_VALUES,
    )
    assert (
        system["details"]["hydrogen"]["weight_kg"]
        == required_energy_kwh
        / (REFERENCE_VALUES["reference_fuel_cell_efficiency_pct"] / 100)
        / HYDROGEN_ENERGY_DENSITY_KWHPKG
    )
    assert system["total_weight_kg"] > system["details"]["gas_tanks"]["weight_kg"]
    assert system["details"]["fuel_cell_system"]["power_kw"] == required_power_kw
    assert (
        system["details"]["electrical_engines"]["power_kw"]
        == required_propulsion_power_kw
    )


def test_suggest_alternative_energy_systems():
    ice = estimate_internal_combustion_system(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE, energy_module=imo
    )

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
        energy["maximum_required_propulsion_power_kw"],
        **REFERENCE_VALUES,
    )
    gas_o = estimate_vessel_gas_hydrogen_system(
        energy["total_kwh"],
        energy["maximum_required_total_power_kw"],
        energy["maximum_required_propulsion_power_kw"],
        **REFERENCE_VALUES,
    )

    gas, battery = suggest_alternative_energy_systems(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE, REFERENCE_VALUES, energy_module=imo
    )

    assert ice["total_weight_kg"] != battery["total_weight_kg"]
    assert ice["total_weight_kg"] != gas["total_weight_kg"]

    # If the draft change is lower than 1% of the design draft there should be no
    # differences
    if abs(battery["change_in_draft_m"]) < DUMMY_VESSEL_DATA.design_draft_m * 0.01:
        assert battery_o["total_weight_kg"] == battery["total_weight_kg"]
    else:
        assert battery_o["total_weight_kg"] != battery["total_weight_kg"]

    if abs(gas["change_in_draft_m"]) < DUMMY_VESSEL_DATA.design_draft_m * 0.01:
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
