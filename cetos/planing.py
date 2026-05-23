"""Planing-hull vessel methodology.

Public surface mirrors ``cetos.imo`` so callers (notably
``cetos.energy_systems``) can swap methodology modules via the ``energy_module``
argument. Equations are TODO: the IMO displacement-mode admiralty formula used
by the delegated implementation is not valid in planing regime (Fn_grad > ~1).
Replacement candidates: Savitsky (1964/1976) or Crouch's empirical formula.
"""

from cetos import imo
from cetos.models import VesselData, VoyageProfile


def estimate_fuel_consumption_of_propulsion_engines(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    limit_7_percent=True,
    delta_w=None,
):
    # TODO: replace with planing-hull (Savitsky / Crouch) load model.
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
    # TODO: replace with planing-hull load model.
    return imo.estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )


def estimate_change_in_draft(vessel_data: VesselData, load_change):
    # TODO: the displacement-mode hydrostatic relation used by imo is not
    # valid in planing regime where part of the weight is supported by
    # hydrodynamic lift. At rest the static result is still buoyancy-driven,
    # but the merchant-ship Cb approximation gives the wrong waterplane area
    # for planing hulls (typical static Cb ~0.35-0.45, not ~0.5).
    return imo.estimate_change_in_draft(vessel_data, load_change)
