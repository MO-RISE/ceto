"""Dispatch sanity tests for the methodology-module split.

While ``planing`` and ``fishing`` delegate to ``imo``, swapping the
``energy_module`` argument must produce identical results. Once real equations
land in those modules these equality assertions will fail loudly — that's the
intended signal to update this file.
"""

import pytest
from fixtures import FERRY_PAX_DAILY_VOYAGE, FERRY_PAX_VESSEL

from cetos import fishing, imo, planing
from cetos.energy_systems import (
    REFERENCE_VALUES,
    estimate_internal_combustion_system,
    suggest_alternative_energy_systems,
)


@pytest.mark.parametrize("energy_module", [imo, planing, fishing])
def test_internal_combustion_system_dispatch(energy_module):
    """ICE-system results must match the IMO baseline while placeholders delegate."""
    reference = estimate_internal_combustion_system(
        FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, energy_module=imo
    )
    result = estimate_internal_combustion_system(
        FERRY_PAX_VESSEL, FERRY_PAX_DAILY_VOYAGE, energy_module=energy_module
    )
    assert result == reference


@pytest.mark.parametrize("energy_module", [planing, fishing])
def test_suggest_alternative_energy_systems_dispatch(energy_module):
    """suggest_alternative_energy_systems must run with non-default modules."""
    gas, battery = suggest_alternative_energy_systems(
        FERRY_PAX_VESSEL,
        FERRY_PAX_DAILY_VOYAGE,
        REFERENCE_VALUES,
        energy_module=energy_module,
    )
    assert gas["total_weight_kg"] > 0
    assert battery["total_weight_kg"] > 0
