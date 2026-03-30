from pytest import approx, raises

from cetos.emissions import (
    CH4_FACTORS,
    CO2_FACTORS,
    GWP_CH4,
    GWP_N2O,
    LCV,
    N2O_FACTORS,
    WTT_FACTORS,
    estimate_co2_emissions,
    estimate_co2_emissions_from_fuel_consumption,
    estimate_ghg_emissions,
    estimate_well_to_wake_emissions,
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


# =============================================================================
# Phase 2: CH4, N2O, and CO2-equivalent (GHG) emissions
# =============================================================================


def test_gwp_values_match_ipcc_ar5():
    assert GWP_CH4 == 28
    assert GWP_N2O == 265


def test_ch4_factors_defined_for_engine_fuel_combinations():
    # Oil-fueled engines have negligible CH4
    assert CH4_FACTORS[("SSD", "HFO")] == approx(0.00005)
    assert CH4_FACTORS[("MSD", "MDO")] == approx(0.00005)
    assert CH4_FACTORS[("HSD", "MDO")] == approx(0.00005)
    # LNG engines have significant methane slip
    assert CH4_FACTORS[("LNG-Otto-MS", "LNG")] == approx(0.031)
    assert CH4_FACTORS[("LBSI", "LNG")] == approx(0.026)


def test_ch4_slip_is_much_higher_for_lng_otto():
    # LNG-Otto-MS has ~620x more CH4 slip than diesel engines
    assert CH4_FACTORS[("LNG-Otto-MS", "LNG")] > CH4_FACTORS[("MSD", "MDO")] * 100


def test_n2o_factors_defined():
    # Oil-fueled engines
    assert N2O_FACTORS[("SSD", "HFO")] == approx(0.00018)
    assert N2O_FACTORS[("MSD", "MDO")] == approx(0.00018)
    # LNG engines have slightly lower N2O
    assert N2O_FACTORS[("LNG-Otto-MS", "LNG")] == approx(0.00011)


def test_estimate_ghg_emissions_returns_all_gases():
    result = estimate_ghg_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert "total_kg_co2" in result
    assert "total_kg_ch4" in result
    assert "total_kg_n2o" in result
    assert "total_kg_co2eq" in result


def test_estimate_ghg_emissions_co2eq_includes_all_gases():
    result = estimate_ghg_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    expected_co2eq = (
        result["total_kg_co2"]
        + result["total_kg_ch4"] * GWP_CH4
        + result["total_kg_n2o"] * GWP_N2O
    )
    assert result["total_kg_co2eq"] == approx(expected_co2eq)


def test_estimate_ghg_emissions_co2eq_greater_than_co2_alone():
    result = estimate_ghg_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert result["total_kg_co2eq"] > result["total_kg_co2"]


def test_estimate_ghg_emissions_mdo_vessel_ch4_is_negligible():
    result = estimate_ghg_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    # For MDO/MSD, CH4 contribution should be tiny compared to CO2
    ch4_co2eq = result["total_kg_ch4"] * GWP_CH4
    assert ch4_co2eq < result["total_kg_co2"] * 0.01  # less than 1% of CO2


def test_estimate_ghg_emissions_lng_vessel_ch4_is_significant():
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
    result = estimate_ghg_emissions(lng_vessel, voyage)
    # For LNG-Otto-MS, CH4 slip is 3.1% — significant contribution
    ch4_co2eq = result["total_kg_ch4"] * GWP_CH4
    # CH4 contribution should be at least 10% of CO2 for LNG-Otto
    assert ch4_co2eq > result["total_kg_co2"] * 0.10


def test_estimate_ghg_emissions_breakdown_by_mode():
    result = estimate_ghg_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        assert "co2_kg" in result[mode]
        assert "ch4_kg" in result[mode]
        assert "n2o_kg" in result[mode]
        assert "co2eq_kg" in result[mode]


def test_estimate_ghg_emissions_total_equals_sum_of_modes():
    result = estimate_ghg_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    for gas in ["co2_kg", "ch4_kg", "n2o_kg", "co2eq_kg"]:
        total_from_modes = sum(
            result[mode][gas]
            for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]
        )
        total_key = f"total_kg_{gas.replace('_kg', '')}"
        assert result[total_key] == approx(total_from_modes)


# =============================================================================
# Phase 3: Well-to-Tank and Well-to-Wake emissions
# =============================================================================


def test_lcv_values_defined_for_all_fuel_types():
    for ft in ["HFO", "MDO", "LNG", "MeOH"]:
        assert ft in LCV
        assert LCV[ft] > 0


def test_lcv_values_match_imo():
    assert LCV["HFO"] == approx(40.2)
    assert LCV["MDO"] == approx(42.7)
    assert LCV["LNG"] == approx(48.0)
    assert LCV["MeOH"] == approx(19.9)


def test_wtt_factors_defined_for_all_fuel_types():
    for ft in ["HFO", "MDO", "LNG", "MeOH"]:
        assert ft in WTT_FACTORS
        assert WTT_FACTORS[ft] > 0


def test_wtt_factors_match_fueleu_annex_ii():
    # gCO2eq/MJ from FuelEU Maritime Annex II (fossil defaults)
    assert WTT_FACTORS["HFO"] == approx(13.5)
    assert WTT_FACTORS["MDO"] == approx(14.4)
    assert WTT_FACTORS["LNG"] == approx(18.5)
    assert WTT_FACTORS["MeOH"] == approx(31.3)


def test_estimate_well_to_wake_returns_wtt_and_ttw():
    result = estimate_well_to_wake_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert "wtt_kg_co2eq" in result
    assert "ttw_kg_co2eq" in result
    assert "wtw_kg_co2eq" in result
    assert result["wtt_kg_co2eq"] > 0
    assert result["ttw_kg_co2eq"] > 0


def test_estimate_well_to_wake_wtw_equals_wtt_plus_ttw():
    result = estimate_well_to_wake_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert result["wtw_kg_co2eq"] == approx(
        result["wtt_kg_co2eq"] + result["ttw_kg_co2eq"]
    )


def test_estimate_well_to_wake_wtt_is_significant_fraction():
    result = estimate_well_to_wake_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    # WtT is typically 10-20% of total WtW for fossil fuels
    wtt_fraction = result["wtt_kg_co2eq"] / result["wtw_kg_co2eq"]
    assert 0.05 < wtt_fraction < 0.30


def test_estimate_well_to_wake_ghg_intensity():
    result = estimate_well_to_wake_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    # GHG intensity in gCO2eq/MJ is the FuelEU Maritime metric
    assert "ghg_intensity_gco2eq_per_mj" in result
    assert result["ghg_intensity_gco2eq_per_mj"] > 0


def test_estimate_well_to_wake_ghg_intensity_reasonable_range():
    # For MDO, WtW intensity should be roughly 90-100 gCO2eq/MJ
    result = estimate_well_to_wake_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    assert 80 < result["ghg_intensity_gco2eq_per_mj"] < 110


def test_estimate_well_to_wake_custom_wtt_factor():
    # Allow users to override WtT factor (for renewable fuels with certified values)
    result = estimate_well_to_wake_emissions(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE, wtt_override_gco2eq_per_mj=5.0
    )
    result_default = estimate_well_to_wake_emissions(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )
    # Override should produce lower WtT emissions
    assert result["wtt_kg_co2eq"] < result_default["wtt_kg_co2eq"]


def test_estimate_well_to_wake_breakdown_by_mode():
    result = estimate_well_to_wake_emissions(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)
    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        assert "wtt_co2eq_kg" in result[mode]
        assert "ttw_co2eq_kg" in result[mode]
        assert "wtw_co2eq_kg" in result[mode]
