"""Dispatch sanity tests for the methodology-module split.

Each methodology module (``imo``, ``planing``, ``fishing``) is exercised
against a fixture in its own scope and must reject vessels that fall outside
that scope when routed through ``cetos.energy_systems``.
"""

import pytest
from fixtures import (
    FERRY_PAX_DAILY_VOYAGE,
    FERRY_PAX_VESSEL,
    FREDRIKA_DAY_VOYAGE,
    FREDRIKA_VESSEL,
    YACHT_DAY_VOYAGE,
    YACHT_VESSEL,
)

from cetos import fishing, imo, planing
from cetos.energy_systems import (
    REFERENCE_VALUES,
    estimate_internal_combustion_system,
    suggest_alternative_energy_systems,
)


def test_fishing_rejects_non_fishing_vessel_via_dispatch():
    """fishing's hard-reject behaviour must propagate through energy_systems."""
    with pytest.raises(ValueError, match="miscellaneous-fishing"):
        estimate_internal_combustion_system(
            FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, energy_module=fishing
        )


def test_fishing_runs_for_fishing_vessel_via_dispatch():
    """fishing on a Fredrika fixture must produce positive ICE-system weight."""
    result = estimate_internal_combustion_system(
        FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE, energy_module=fishing
    )
    assert result["total_weight_kg"] > 0


def test_planing_rejects_displacement_mode_vessel_via_dispatch():
    """planing's Fn>=0.6 scope check must propagate through energy_systems."""
    with pytest.raises(ValueError, match="HSVA scope"):
        estimate_internal_combustion_system(
            FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, energy_module=planing
        )


def test_planing_rejects_user_leg_draft_off_design():
    """Per-leg drafts other than design_draft_m must be rejected; load
    deltas belong on vessel_data.displacement_kg via
    ``_apply_change_in_displacement``, not on leg drafts."""
    from cetos.models import VoyageLeg, VoyageProfile

    bad_voyage = VoyageProfile(
        time_anchored_h=0.0,
        time_at_berth_h=0.0,
        legs_at_sea=[VoyageLeg(50.0, 30.0, YACHT_VESSEL.design_draft_m + 0.3)],
    )
    with pytest.raises(ValueError, match="every leg draft must equal"):
        planing.estimate_fuel_consumption_of_propulsion_engines(
            YACHT_VESSEL, bad_voyage
        )


def test_planing_apply_change_in_displacement_bumps_displacement():
    """planing's mass-feedback channel must add load_change to displacement_kg
    on a copy, leaving the input vessel_data untouched and voyage_profile
    flowing through unchanged."""
    new_vessel, new_voyage = planing._apply_change_in_displacement(
        YACHT_VESSEL, YACHT_DAY_VOYAGE, 1_000.0
    )
    assert new_vessel.displacement_kg == YACHT_VESSEL.displacement_kg + 1_000.0
    assert YACHT_VESSEL.displacement_kg == 50_000.0  # input unchanged
    assert new_voyage is YACHT_DAY_VOYAGE


def test_planing_runs_for_planing_vessel_via_dispatch():
    """planing on a yacht fixture must produce positive ICE-system weight and
    must diverge from imo on the same fixture (otherwise the HSVA brake-power
    formula was not actually used)."""
    planing_result = estimate_internal_combustion_system(
        YACHT_VESSEL, YACHT_DAY_VOYAGE, energy_module=planing
    )
    imo_result = estimate_internal_combustion_system(
        YACHT_VESSEL, YACHT_DAY_VOYAGE, energy_module=imo
    )
    assert planing_result["total_weight_kg"] > 0
    assert planing_result["total_weight_kg"] != imo_result["total_weight_kg"]


@pytest.mark.parametrize(
    "energy_module,vessel,voyage",
    [
        (imo, FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE),
        (planing, YACHT_VESSEL, YACHT_DAY_VOYAGE),
        (fishing, FREDRIKA_VESSEL, FREDRIKA_DAY_VOYAGE),
    ],
)
def test_suggest_alternative_energy_systems_dispatch(energy_module, vessel, voyage):
    """Each module routes through suggest_alternative_energy_systems on an
    in-scope fixture and yields positive gas- and battery-system weights."""
    gas, battery = suggest_alternative_energy_systems(
        vessel, voyage, REFERENCE_VALUES, energy_module=energy_module
    )
    assert gas["total_weight_kg"] > 0
    assert battery["total_weight_kg"] > 0
