from pytest import approx, raises

from cetos.cii import (
    CII_PARAMS,
    CII_RATING_BOUNDARIES,
    REDUCTION_FACTORS,
    calculate_attained_cii,
    calculate_cii_rating,
    calculate_required_cii,
    estimate_cii,
)
from cetos.models import VesselData, VoyageLeg, VoyageProfile

# Oil tanker: DWT 50,000, SSD, HFO
OIL_TANKER = VesselData(
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

TANKER_VOYAGE = VoyageProfile(
    time_at_berth_h=24,
    legs_at_sea=[VoyageLeg(500, 14, 11)],
)


# =============================================================================
# Reference line tests
# =============================================================================


def test_cii_params_defined_for_tanker():
    assert "tanker" in CII_PARAMS
    a, c = CII_PARAMS["tanker"]
    assert a == approx(5247)
    assert c == approx(0.610)


def test_cii_params_defined_for_bulk_carrier():
    assert "bulk_carrier" in CII_PARAMS
    a, c = CII_PARAMS["bulk_carrier"]
    assert a == approx(4745)
    assert c == approx(0.622)


def test_cii_params_defined_for_container():
    assert "container" in CII_PARAMS
    a, c = CII_PARAMS["container"]
    assert a == approx(1984)
    assert c == approx(0.489)


def test_cii_params_defined_for_cruise():
    assert "cruise_passenger" in CII_PARAMS


def test_reduction_factors_defined():
    assert REDUCTION_FACTORS[2023] == 5
    assert REDUCTION_FACTORS[2024] == 7
    assert REDUCTION_FACTORS[2025] == 9
    assert REDUCTION_FACTORS[2026] == 11


def test_rating_boundaries_defined_for_tanker():
    d = CII_RATING_BOUNDARIES["tanker"]
    assert len(d) == 4
    assert d[0] < d[1] < d[2] < d[3]
    # exp(d) values: A boundary < 1.0, D/E boundary > 1.0
    assert d[0] < 1.0
    assert d[3] > 1.0


# =============================================================================
# Calculation tests
# =============================================================================


def test_calculate_required_cii_tanker():
    # For a 50,000 DWT tanker: CII_ref = 5247 * 50000^(-0.610)
    cii_ref = 5247 * (50_000**-0.610)
    # 2023 reduction: Z=5%
    expected = cii_ref * (1 - 5 / 100)
    result = calculate_required_cii("tanker", 50_000, 2023)
    assert result == approx(expected, rel=0.01)


def test_calculate_required_cii_tightens_over_years():
    cii_2023 = calculate_required_cii("tanker", 50_000, 2023)
    cii_2026 = calculate_required_cii("tanker", 50_000, 2026)
    assert cii_2026 < cii_2023


def test_calculate_attained_cii():
    # 1000 tonnes CO2, 50000 DWT, 5000 nm
    # CII = (1000 * 1e6 g) / (50000 * 5000) = 4.0
    result = calculate_attained_cii(
        co2_emissions_kg=1_000_000, capacity=50_000, distance_nm=5_000
    )
    assert result == approx(4.0)


def test_calculate_attained_cii_zero_distance_raises():
    with raises(ValueError):
        calculate_attained_cii(co2_emissions_kg=1000, capacity=50000, distance_nm=0)


def test_calculate_cii_rating_a():
    # Give a very low attained CII — should be A
    required = calculate_required_cii("tanker", 50_000, 2023)
    exp_d1 = CII_RATING_BOUNDARIES["tanker"][0]  # 0.82
    very_low = required * exp_d1 * 0.5
    assert calculate_cii_rating(very_low, required, "tanker") == "A"


def test_calculate_cii_rating_e():
    # Give a very high attained CII — should be E
    required = calculate_required_cii("tanker", 50_000, 2023)
    very_high = required * 2.0
    assert calculate_cii_rating(very_high, required, "tanker") == "E"


def test_calculate_cii_rating_d_boundary():
    # The D/E boundary is at required * exp_d4 (1.28 for tanker)
    required = calculate_required_cii("tanker", 50_000, 2023)
    exp_d4 = CII_RATING_BOUNDARIES["tanker"][3]  # 1.28
    # Just below D/E boundary should be D
    assert calculate_cii_rating(required * exp_d4 * 0.99, required, "tanker") == "D"
    # Just above D/E boundary should be E
    assert calculate_cii_rating(required * exp_d4 * 1.01, required, "tanker") == "E"


# =============================================================================
# End-to-end estimate_cii tests
# =============================================================================


def test_estimate_cii_returns_rating():
    result = estimate_cii(OIL_TANKER, TANKER_VOYAGE, year=2023)
    assert "rating" in result
    assert result["rating"] in ["A", "B", "C", "D", "E"]


def test_estimate_cii_returns_attained_and_required():
    result = estimate_cii(OIL_TANKER, TANKER_VOYAGE, year=2023)
    assert "attained_cii" in result
    assert "required_cii" in result
    assert result["attained_cii"] > 0
    assert result["required_cii"] > 0


def test_estimate_cii_returns_co2_and_distance():
    result = estimate_cii(OIL_TANKER, TANKER_VOYAGE, year=2023)
    assert "total_co2_kg" in result
    assert "total_distance_nm" in result
    assert result["total_co2_kg"] > 0
    assert result["total_distance_nm"] == approx(500)


def test_estimate_cii_rating_worsens_over_years():
    # As required CII tightens, rating should worsen (or stay same)
    result_2023 = estimate_cii(OIL_TANKER, TANKER_VOYAGE, year=2023)
    result_2026 = estimate_cii(OIL_TANKER, TANKER_VOYAGE, year=2026)
    ratings = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
    assert ratings[result_2026["rating"]] >= ratings[result_2023["rating"]]
