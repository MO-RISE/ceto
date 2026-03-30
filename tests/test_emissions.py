from pytest import approx, raises

from cetos.emissions import (
    CO2_FACTORS,
    estimate_co2_emissions,
    estimate_co2_emissions_from_fuel_consumption,
)
from cetos.models import VesselData, VoyageLeg, VoyageProfile

DUMMY_VESSEL_DATA = VesselData(
    design_speed_kn=10,
    design_draft_m=7,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=1_000,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="offshore",
    size=None,
    double_ended=False,
    length_m=100,
    beam_m=20,
)

DUMMY_VOYAGE_PROFILE = VoyageProfile(
    time_anchored_h=10.0,
    time_at_berth_h=10.0,
    legs_manoeuvring=[
        VoyageLeg(10, 10, 7),
    ],
    legs_at_sea=[
        VoyageLeg(10, 10, 7),
        VoyageLeg(20, 10, 6),
    ],
)


def test_co2_factors_are_defined_for_all_fuel_types():
    assert "HFO" in CO2_FACTORS
    assert "MDO" in CO2_FACTORS
    assert "LNG" in CO2_FACTORS
    assert "MeOH" in CO2_FACTORS


def test_co2_factors_match_imo_mepc_308_73():
    assert CO2_FACTORS["HFO"] == approx(3.114)
    assert CO2_FACTORS["MDO"] == approx(3.206)
    assert CO2_FACTORS["LNG"] == approx(2.750)
    assert CO2_FACTORS["MeOH"] == approx(1.375)


def test_estimate_co2_emissions_from_fuel_consumption_simple():
    # 1000 kg of MDO should produce 3206 kg of CO2
    result = estimate_co2_emissions_from_fuel_consumption(1000.0, "MDO")
    assert result == approx(3206.0)


def test_estimate_co2_emissions_from_fuel_consumption_hfo():
    result = estimate_co2_emissions_from_fuel_consumption(1000.0, "HFO")
    assert result == approx(3114.0)


def test_estimate_co2_emissions_from_fuel_consumption_lng():
    result = estimate_co2_emissions_from_fuel_consumption(1000.0, "LNG")
    assert result == approx(2750.0)


def test_estimate_co2_emissions_from_fuel_consumption_methanol():
    result = estimate_co2_emissions_from_fuel_consumption(1000.0, "MeOH")
    assert result == approx(1375.0)


def test_estimate_co2_emissions_from_fuel_consumption_zero_fuel():
    result = estimate_co2_emissions_from_fuel_consumption(0.0, "HFO")
    assert result == approx(0.0)


def test_estimate_co2_emissions_from_fuel_consumption_invalid_fuel_type():
    with raises(ValueError):
        estimate_co2_emissions_from_fuel_consumption(1000.0, "diesel")


def test_estimate_co2_emissions_returns_total():
    result = estimate_co2_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert "total_kg_co2" in result
    assert result["total_kg_co2"] > 0


def test_estimate_co2_emissions_returns_breakdown():
    result = estimate_co2_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert "at_berth" in result
    assert "anchored" in result
    assert "manoeuvring" in result
    assert "at_sea" in result
    for key in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        assert "co2_kg" in result[key]


def test_estimate_co2_emissions_total_equals_sum_of_parts():
    result = estimate_co2_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    total_from_parts = sum(result[key]["co2_kg"] for key in ["at_berth", "anchored", "manoeuvring", "at_sea"])
    assert result["total_kg_co2"] == approx(total_from_parts)


def test_estimate_co2_emissions_includes_fuel_consumption():
    result = estimate_co2_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert "total_fuel_kg" in result
    assert result["total_fuel_kg"] > 0


def test_estimate_co2_emissions_co2_is_greater_than_fuel():
    # CO2 mass is always greater than fuel mass (conversion factors > 1)
    result = estimate_co2_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert result["total_kg_co2"] > result["total_fuel_kg"]


def test_estimate_co2_emissions_hfo_vessel():
    hfo_vessel = VesselData(
        design_speed_kn=15,
        design_draft_m=12,
        number_of_propulsion_engines=1,
        propulsion_engine_power_kw=8_000,
        propulsion_engine_type="SSD",
        propulsion_engine_age="after_2000",
        propulsion_engine_fuel_type="HFO",
        type="oil_tanker",
        size=50_000,
        double_ended=False,
        length_m=200,
        beam_m=30,
    )
    voyage = VoyageProfile(
        time_at_berth_h=24,
        legs_at_sea=[VoyageLeg(500, 14, 11)],
    )
    result = estimate_co2_emissions(hfo_vessel, voyage)
    assert result["total_kg_co2"] > 0
    # HFO factor is 3.114, so CO2 should be ~3.114x the fuel mass
    assert result["total_kg_co2"] == approx(result["total_fuel_kg"] * 3.114, rel=0.01)


def test_estimate_co2_emissions_lng_vessel():
    lng_vessel = VesselData(
        design_speed_kn=15,
        design_draft_m=10,
        number_of_propulsion_engines=2,
        propulsion_engine_power_kw=5_000,
        propulsion_engine_type="LNG-Otto-MS",
        propulsion_engine_age="after_2000",
        propulsion_engine_fuel_type="LNG",
        type="cruise",
        size=30_000,
        double_ended=False,
        length_m=180,
        beam_m=28,
    )
    voyage = VoyageProfile(
        time_at_berth_h=12,
        legs_at_sea=[VoyageLeg(200, 14, 9)],
    )
    result = estimate_co2_emissions(lng_vessel, voyage)
    assert result["total_kg_co2"] > 0
    # LNG factor is 2.750
    assert result["total_kg_co2"] == approx(result["total_fuel_kg"] * 2.750, rel=0.01)
