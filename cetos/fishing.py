"""Fishing-vessel methodology.

Public surface mirrors ``cetos.imo`` so callers (notably
``cetos.energy_systems``) can swap methodology modules via the ``energy_module``
argument. Equations are TODO: ``voyage_profile.legs_fishing`` (defined in
``cetos.models`` but currently unused everywhere) is the natural integration
point for gear-drag-dominated propulsion load during fishing operations, plus
fishing-specific auxiliary loads (winches, RSW chillers, processing).
"""

from cetos import imo
from cetos.models import VesselData, VoyageProfile


def estimate_fuel_consumption_of_propulsion_engines(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    limit_7_percent=True,
    delta_w=None,
):
    # TODO: add per-gear load handling for voyage_profile.legs_fishing.
    return imo.estimate_fuel_consumption_of_propulsion_engines(
        vessel_data,
        voyage_profile,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )


def estimate_energy_consumption(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    # TODO: consume voyage_profile.legs_fishing; add fishing-mode aux loads.
    return imo.estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )


def estimate_change_in_draft(vessel_data: VesselData, load_change):
    # TODO: the merchant-ship block-coefficient approximation used by imo is
    # calibrated for cargo/tanker hull forms. Fishing-boat hulls (beamy, full-
    # bodied, often with high deadrise) have meaningfully different Cb/Cwp,
    # so the predicted draft change is biased even though the hydrostatics
    # itself is appropriate.
    return imo.estimate_change_in_draft(vessel_data, load_change)
