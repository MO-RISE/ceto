from pytest import approx

from cetos.lca import (
    BATTERY_MANUFACTURING_FACTORS,
    GRID_EMISSION_FACTORS,
    HYDROGEN_WTT_FACTORS,
    compare_propulsion_systems,
)
from cetos.models import VesselData, VoyageLeg, VoyageProfile

VESSEL = VesselData(
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

VOYAGE = VoyageProfile(
    time_anchored_h=2.0,
    time_at_berth_h=4.0,
    legs_manoeuvring=[VoyageLeg(2, 5, 7)],
    legs_at_sea=[VoyageLeg(50, 10, 7)],
)


def test_compare_returns_all_three_systems():
    result = compare_propulsion_systems(VESSEL, VOYAGE)
    assert "diesel" in result
    assert "battery" in result
    assert "hydrogen" in result
    assert "comparison" in result
    assert "parameters" in result


def test_diesel_has_positive_emissions():
    result = compare_propulsion_systems(VESSEL, VOYAGE)
    d = result["diesel"]
    assert d["operational_co2eq_per_voyage_kg"] > 0
    assert d["total_lifecycle_co2eq_kg"] > 0
    assert d["nox_lifetime_kg"] > 0
    assert d["sox_lifetime_kg"] > 0
    assert d["fuel_per_voyage_kg"] > 0


def test_battery_zero_local_pollutants():
    result = compare_propulsion_systems(VESSEL, VOYAGE)
    b = result["battery"]
    assert b["nox_lifetime_kg"] == 0.0
    assert b["sox_lifetime_kg"] == 0.0
    assert b["pm_lifetime_kg"] == 0.0


def test_hydrogen_zero_local_pollutants():
    result = compare_propulsion_systems(VESSEL, VOYAGE)
    h = result["hydrogen"]
    assert h["nox_lifetime_kg"] == 0.0
    assert h["sox_lifetime_kg"] == 0.0
    assert h["pm_lifetime_kg"] == 0.0


def test_battery_renewable_grid_very_low_operational():
    result = compare_propulsion_systems(VESSEL, VOYAGE, grid_source="renewable")
    b = result["battery"]
    assert b["operational_co2eq_per_voyage_kg"] == 0.0
    # But manufacturing emissions should still be positive
    assert b["manufacturing_co2eq_kg"] > 0


def test_green_hydrogen_lower_than_grey():
    grey = compare_propulsion_systems(VESSEL, VOYAGE, hydrogen_source="grey")
    green = compare_propulsion_systems(VESSEL, VOYAGE, hydrogen_source="green")
    assert (
        green["hydrogen"]["total_lifecycle_co2eq_kg"]
        < grey["hydrogen"]["total_lifecycle_co2eq_kg"]
    )


def test_comparison_diesel_is_100_pct():
    result = compare_propulsion_systems(VESSEL, VOYAGE)
    assert result["comparison"]["diesel_vs_baseline_pct"] == 100.0


def test_battery_with_renewable_beats_diesel():
    result = compare_propulsion_systems(
        VESSEL, VOYAGE, grid_source="renewable"
    )
    assert result["comparison"]["battery_vs_baseline_pct"] < 100.0


def test_green_h2_beats_diesel():
    result = compare_propulsion_systems(
        VESSEL, VOYAGE, hydrogen_source="green"
    )
    assert result["comparison"]["hydrogen_vs_baseline_pct"] < 100.0


def test_system_weights_are_positive():
    result = compare_propulsion_systems(VESSEL, VOYAGE)
    assert result["diesel"]["system_weight_kg"] > 0
    assert result["battery"]["system_weight_kg"] > 0
    assert result["hydrogen"]["system_weight_kg"] > 0


def test_parameters_stored_in_result():
    result = compare_propulsion_systems(
        VESSEL, VOYAGE,
        vessel_lifetime_years=20,
        voyages_per_year=200,
        grid_source="sweden",
        hydrogen_source="green",
        battery_type="LFP_china",
    )
    p = result["parameters"]
    assert p["vessel_lifetime_years"] == 20
    assert p["voyages_per_year"] == 200
    assert p["total_voyages"] == 4000
    assert p["grid_source"] == "sweden"
    assert p["hydrogen_source"] == "green"
    assert p["battery_type"] == "LFP_china"


def test_manufacturing_emissions_scale_with_lifetime():
    short = compare_propulsion_systems(VESSEL, VOYAGE, vessel_lifetime_years=5)
    long = compare_propulsion_systems(VESSEL, VOYAGE, vessel_lifetime_years=30)
    # Longer lifetime = more battery replacements
    assert (
        long["battery"]["manufacturing_co2eq_kg"]
        >= short["battery"]["manufacturing_co2eq_kg"]
    )


def test_sweden_grid_lower_than_germany():
    se = compare_propulsion_systems(VESSEL, VOYAGE, grid_source="sweden")
    de = compare_propulsion_systems(VESSEL, VOYAGE, grid_source="germany")
    assert (
        se["battery"]["operational_co2eq_lifetime_kg"]
        < de["battery"]["operational_co2eq_lifetime_kg"]
    )
