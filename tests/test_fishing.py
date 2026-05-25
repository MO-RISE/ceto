"""Behavioural tests for cetos.fishing (VEAT methodology).

Reference: Barman & Soerfeldt (2024), Appendix B.
"""

from dataclasses import replace

import pytest
from pytest import approx

from cetos import fishing, imo
from cetos.models import VoyageLeg, VoyageProfile
from fixtures import FERRY_PAX_VESSEL, FREDRIKA_DAY_VOYAGE, FREDRIKA_VESSEL

# ---------------------------------------------------------------------------
# Scope validation
# ---------------------------------------------------------------------------


def test_rejects_non_fishing_vessel():
    with pytest.raises(ValueError, match="miscellaneous-fishing"):
        fishing.estimate_energy_consumption(FERRY_PAX_VESSEL, FREDRIKA_DAY_VOYAGE)


def test_rejects_too_short_vessel():
    too_short = replace(FREDRIKA_VESSEL, length_m=8.0)
    with pytest.raises(ValueError, match="VEAT scope"):
        fishing.estimate_energy_consumption(too_short, FREDRIKA_DAY_VOYAGE)


def test_rejects_too_long_vessel():
    too_long = replace(FREDRIKA_VESSEL, length_m=35.0)
    with pytest.raises(ValueError, match="VEAT scope"):
        fishing.estimate_energy_consumption(too_long, FREDRIKA_DAY_VOYAGE)


def test_rejects_too_fast_vessel():
    too_fast = replace(FREDRIKA_VESSEL, design_speed_kn=15.0)
    with pytest.raises(ValueError, match="design_speed_kn"):
        fishing.estimate_energy_consumption(too_fast, FREDRIKA_DAY_VOYAGE)


def test_rejects_missing_gear_type():
    no_gear = replace(FREDRIKA_VESSEL, gear_type=None)
    with pytest.raises(ValueError, match="gear_type"):
        fishing.estimate_energy_consumption(no_gear, FREDRIKA_DAY_VOYAGE)


# ---------------------------------------------------------------------------
# Engine coefficient pinning (Appendix B, Eqs. B.9-B.12)
# ---------------------------------------------------------------------------


def test_engine_coeffs_match_fredrika_b9_b10():
    alpha, beta = fishing._engine_coeffs(242)
    assert alpha == approx(1.9762, abs=1e-4)
    assert beta == approx(0.2772, abs=1e-4)


def test_engine_coeffs_match_mira_b11_b12():
    alpha, beta = fishing._engine_coeffs(167)
    assert alpha == approx(1.6687, abs=1e-4)
    assert beta == approx(0.2852, abs=1e-4)


# ---------------------------------------------------------------------------
# Propulsion equation (Appendix B Eq. B.1, Figure B.1: L=12 m, B=4 m)
# ---------------------------------------------------------------------------


def test_propulsion_power_is_continuous_at_knee():
    # P(3) from the exponential branch must equal P(3) from the cubic branch.
    p_above = fishing._propulsion_power_kw(12.0, 4.0, 3.0)
    p_below = fishing._propulsion_power_kw(12.0, 4.0, 2.9999)
    assert p_below == approx(p_above, rel=1e-3)


def test_propulsion_power_grows_exponentially_above_knee():
    p_low = fishing._propulsion_power_kw(12.0, 4.0, 5.0)
    p_high = fishing._propulsion_power_kw(12.0, 4.0, 10.0)
    # exp(0.57 * 5) ratio
    import math

    assert p_high / p_low == approx(math.exp(0.57 * 5.0), rel=1e-6)


def test_propulsion_power_cubic_below_knee():
    # P(0) should be 0; P(s) should scale as s^3 below 3 kn.
    assert fishing._propulsion_power_kw(12.0, 4.0, 0.0) == 0.0
    p1 = fishing._propulsion_power_kw(12.0, 4.0, 1.0)
    p2 = fishing._propulsion_power_kw(12.0, 4.0, 2.0)
    assert p2 / p1 == approx(8.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Subsystem behaviour driven by leg type
# ---------------------------------------------------------------------------


def test_hydraulics_zero_when_no_fishing_legs():
    voyage = VoyageProfile(
        time_anchored_h=0.0,
        time_at_berth_h=0.0,
        legs_at_sea=[VoyageLeg(10.0, 8.0, 1.5)],
        legs_fishing=[],
    )
    out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, voyage)
    assert out["hydraulic_kwh"] == 0.0


def test_dc_active_during_manoeuvring_at_sea_and_fishing():
    voyage = VoyageProfile(
        time_anchored_h=0.0,
        time_at_berth_h=0.0,
        legs_manoeuvring=[VoyageLeg(5.0, 5.0, 1.5)],  # 1 h
        legs_at_sea=[VoyageLeg(8.0, 8.0, 1.5)],  # 1 h
        legs_fishing=[VoyageLeg(0.7, 0.7, 1.5)],  # 1 h
    )
    out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, voyage)
    # 0.3 kW * 3 h / (0.8 * 0.6)
    assert out["dc_kwh"] == approx(0.3 * 3.0 / (0.8 * 0.6), rel=1e-6)


def test_refrigeration_active_during_manoeuvring():
    with_ref = replace(
        FREDRIKA_VESSEL,
        refrigeration_power_kw=5.0,
        refrigeration_system_type="electric",
    )
    voyage = VoyageProfile(
        time_anchored_h=0.0,
        time_at_berth_h=0.0,
        legs_manoeuvring=[VoyageLeg(5.0, 5.0, 1.5)],  # 1 h
    )
    out = fishing.estimate_energy_consumption(with_ref, voyage)
    # 5 kW * 1 h / 0.81 (electric eta)
    assert out["refrigeration_kwh"] == approx(5.0 / 0.81, rel=1e-6)


def test_refrigeration_zero_when_not_installed():
    out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE)
    assert out["refrigeration_kwh"] == 0.0


def test_refrigeration_active_when_installed():
    with_ref = replace(
        FREDRIKA_VESSEL,
        refrigeration_power_kw=5.0,
        refrigeration_system_type="electric",
    )
    out = fishing.estimate_energy_consumption(with_ref, FREDRIKA_DAY_VOYAGE)
    h_on = (
        sum(
            leg.distance_nm / leg.speed_kn
            for leg in FREDRIKA_DAY_VOYAGE.legs_manoeuvring
        )
        + sum(leg.distance_nm / leg.speed_kn for leg in FREDRIKA_DAY_VOYAGE.legs_at_sea)
        + sum(
            leg.distance_nm / leg.speed_kn for leg in FREDRIKA_DAY_VOYAGE.legs_fishing
        )
    )
    assert out["refrigeration_kwh"] == approx(5.0 * h_on / 0.81, rel=1e-6)


def test_refrigeration_requires_system_type():
    # The VesselData validator should refuse a power-without-system-type combo.
    with pytest.raises(ValueError, match="refrigeration_system_type"):
        replace(
            FREDRIKA_VESSEL,
            refrigeration_power_kw=5.0,
            refrigeration_system_type=None,
        )


def test_gear_type_changes_hydraulic_energy():
    seine_vessel = replace(FREDRIKA_VESSEL, gear_type="seine")
    pot_out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE)
    seine_out = fishing.estimate_energy_consumption(seine_vessel, FREDRIKA_DAY_VOYAGE)
    # Seine deck power 35 kW * 0.20 vs pot_small 4 kW * 0.48
    assert seine_out["hydraulic_kwh"] > pot_out["hydraulic_kwh"]


# ---------------------------------------------------------------------------
# Return-shape compatibility with cetos.energy_systems
# ---------------------------------------------------------------------------


def test_energy_consumption_dict_has_required_keys():
    out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE)
    for key in (
        "total_kwh",
        "maximum_required_total_power_kw",
        "maximum_required_propulsion_power_kw",
    ):
        assert key in out


def test_fuel_consumption_returns_tuple():
    out = fishing.estimate_fuel_consumption_of_propulsion_engines(
        FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE
    )
    assert isinstance(out, tuple) and len(out) == 2
    fuel_kg, avg_l_per_nm = out
    assert fuel_kg > 0 and avg_l_per_nm > 0


def test_change_in_draft_delegates_to_imo():
    # Use a load_change small enough not to trigger any imo internal guards.
    assert fishing.estimate_change_in_draft(
        FREDRIKA_VESSEL, 100.0
    ) == imo.estimate_change_in_draft(FREDRIKA_VESSEL, 100.0)
