"""Dispatch sanity tests for the methodology-module split.

``planing`` still delegates to ``imo`` and so must match the IMO baseline on a
ferry fixture; once planing lands its own equations these equality assertions
will fail loudly. ``fishing`` is now a real VEAT implementation that rejects
non-fishing vessels and must be exercised against a fishing fixture instead.
"""

import pytest
from fixtures import (
    FERRY_PAX_DAILY_VOYAGE,
    FERRY_PAX_VESSEL,
    FREDRIKA_DAY_VOYAGE,
    FREDRIKA_VESSEL,
)

from cetos import fishing, imo, planing
from cetos.energy_systems import (
    REFERENCE_VALUES,
    estimate_internal_combustion_system,
    suggest_alternative_energy_systems,
)


@pytest.mark.parametrize("energy_module", [imo, planing])
def test_internal_combustion_system_dispatch_matches_imo(energy_module):
    """planing still delegates to imo on a ferry fixture; results must match."""
    reference = estimate_internal_combustion_system(
        FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, energy_module=imo
    )
    result = estimate_internal_combustion_system(
        FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, energy_module=energy_module
    )
    assert result == reference


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


@pytest.mark.parametrize("energy_module", [planing])
def test_suggest_alternative_energy_systems_dispatch_ferry(energy_module):
    """planing still works on the ferry fixture (delegates to imo)."""
    gas, battery = suggest_alternative_energy_systems(
        FERRY_PAX_VESSEL,
        FERRY_PAX_DAILY_VOYAGE,
        REFERENCE_VALUES,
        energy_module=energy_module,
    )
    assert gas["total_weight_kg"] > 0
    assert battery["total_weight_kg"] > 0


def test_suggest_alternative_energy_systems_dispatch_fishing():
    """fishing module routes through suggest_alternative_energy_systems on Fredrika."""
    gas, battery = suggest_alternative_energy_systems(
        FREDRIKA_VESSEL,
        FREDRIKA_DAY_VOYAGE,
        REFERENCE_VALUES,
        energy_module=fishing,
    )
    assert gas["total_weight_kg"] > 0
    assert battery["total_weight_kg"] > 0
