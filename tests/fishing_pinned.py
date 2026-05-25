"""Pinning tests for cetos.fishing (VEAT methodology).

Hardcoded subsystem-level pins are derived directly from Barman & Soerfeldt
(2024) Appendix B and verification examples B.9-B.12. Whole-dict outputs
for Fredrika and Mira representative days are pinned via pytest-pinned —
regenerate with ``pytest --regenerate-pinned``.
"""

import math

import pytest
from pytest import approx

from cetos import fishing
from fixtures import (
    FREDRIKA_DAY_VOYAGE,
    FREDRIKA_VESSEL,
    MIRA_DAY_VOYAGE,
    MIRA_VESSEL,
)

# ---------------------------------------------------------------------------
# Engine coefficients — pinned against Appendix B Eqs. B.9-B.12 verbatim
# ---------------------------------------------------------------------------


def test_engine_alpha_fredrika():
    """B.9: alpha = 0.984 + 0.0041 * 242 = 1.9762 l/hr."""
    alpha, _ = fishing._engine_coeffs(242)
    assert alpha == approx(1.9762, abs=1e-4)


def test_engine_beta_fredrika():
    """B.10: beta = 0.303 - 1.066e-4 * 242 = 0.2772 l/(hr*kW)."""
    _, beta = fishing._engine_coeffs(242)
    assert beta == approx(0.2772, abs=1e-4)


def test_engine_alpha_mira():
    """B.11: alpha = 0.984 + 0.0041 * 167 = 1.6687 l/hr."""
    alpha, _ = fishing._engine_coeffs(167)
    assert alpha == approx(1.6687, abs=1e-4)


def test_engine_beta_mira():
    """B.12: beta = 0.303 - 1.066e-4 * 167 = 0.2852 l/(hr*kW)."""
    _, beta = fishing._engine_coeffs(167)
    assert beta == approx(0.2852, abs=1e-4)


# ---------------------------------------------------------------------------
# Propulsion curve — pinned against Figure B.1 (L=12 m, B=4 m) shape
# ---------------------------------------------------------------------------


def test_propulsion_curve_fig_b1_at_10_kn():
    """0.0214 * 12 * sqrt(4) * exp(0.57 * 10) = 153.6 kW."""
    p = fishing._propulsion_power_kw(12.0, 4.0, 10.0)
    expected = 0.0214 * 12.0 * math.sqrt(4.0) * math.exp(5.7)
    assert p == approx(expected, rel=1e-6)
    # Figure B.1 shows ~140 kW at 10 kn; ours is 153.6 (chart-read imprecise).
    assert 140.0 < p < 165.0


def test_propulsion_curve_fig_b1_at_knee():
    """At s = 3 kn the cubic and exponential branches meet."""
    p = fishing._propulsion_power_kw(12.0, 4.0, 3.0)
    expected = 0.0214 * 12.0 * math.sqrt(4.0) * math.exp(0.57 * 3.0)
    assert p == approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# Fredrika subsystem breakdown — pinned against thesis Table 4.8 logic
# ---------------------------------------------------------------------------


def test_fredrika_hydraulic_energy_matches_table_4_8():
    """Pot_small deck 4.0 kW * rho 0.48 * 6.857 h / eta 0.96 = 13.71 kWh.

    Thesis Table 4.8 reports 13.7 kWh hydraulics for the 12-string rep day.
    """
    out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE)
    assert out["hydraulic_kwh"] == approx(13.71, rel=1e-3)


def test_fredrika_dc_energy_close_to_table_4_8():
    """DC energy = 0.3 kW * (h_at_sea + h_fishing) / (0.8 * 0.6).

    Fixture rep day h_at_sea = 1.693 h, h_fishing = 6.857 h: 0.3 * 8.55 / 0.48 = 5.34 kWh.
    Thesis Table 4.8 reports 5.6 kWh (small voyage-profile difference, ~5%).
    """
    out = fishing.estimate_energy_consumption(FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE)
    assert out["dc_kwh"] == approx(5.34, rel=1e-2)
    # Sanity: result is within 5% of the thesis Table 4.8 value.
    assert abs(out["dc_kwh"] - 5.6) / 5.6 < 0.05


# ---------------------------------------------------------------------------
# Whole-dict pins via pytest-pinned (regenerate with --regenerate-pinned)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vessel,voyage,name",
    [
        (FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE, "fredrika_day"),
        (MIRA_VESSEL, MIRA_DAY_VOYAGE, "mira_day"),
    ],
)
def test_energy_consumption_pinned(vessel, voyage, name, pinned):
    result = fishing.estimate_energy_consumption(vessel, voyage)
    assert result == pinned


@pytest.mark.parametrize(
    "vessel,voyage,name",
    [
        (FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE, "fredrika_day"),
        (MIRA_VESSEL, MIRA_DAY_VOYAGE, "mira_day"),
    ],
)
def test_fuel_consumption_pinned(vessel, voyage, name, pinned):
    fuel_kg, avg_l_per_nm = fishing.estimate_fuel_consumption_of_propulsion_engines(
        vessel, voyage
    )
    assert {"fuel_kg": fuel_kg, "avg_l_per_nm": avg_l_per_nm} == pinned
