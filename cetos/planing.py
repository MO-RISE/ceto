"""Planing-hull vessel methodology.

Implements the HSVA empirical brake-power formula for planing hulls from
Bertram & Mesbahi (2004), originally derived from graphs in Fritsch &
Bertram (2002), and published as Eqs. 3.65-3.66 in Bertram, V. (2012),
*Practical Ship Hydrodynamics* (2nd ed.), Butterworth-Heinemann, §3.4.1.

The HSVA formula yields the required brake power P_B [kW] directly as a
function of displacement mass D [kg], chine beam B_C [m] and speed V [kn]:

    P_B = 0.7354 * (D * V / 765.2 + B_C^2 * V^3 / 1051.1)             (3.65)
    B_C = 0.215 * D^0.275                                             (3.66)

Unit hazard: PSH (2nd ed.) §3.4.1 prints "D [t]" but the original Fritsch
& Bertram (2002) source has D in **kg**. The kg interpretation is the one
that reproduces realistic planing-yacht power demand (a ~50 t / 30 kn
yacht needs ~1700 kW, which Eq. 3.65 returns only when D is in kg); the
"t" reading underestimates by ~200x. This module uses kg.

Public surface mirrors ``cetos.imo`` so callers (notably
``cetos.energy_systems``) can swap methodology modules via the
``energy_module`` argument. Propulsion is computed via Eq. 3.65; auxiliary
loads (aux engines, steam boilers, at-berth / anchored hotel loads) are
delegated to ``cetos.imo`` so the vessel-type-keyed power tables stay
authoritative.

Scope: monohull planing vessels operating in the high-Froude regime. Eq. 3.65
was fitted to fast-monohull data and is valid in the semi-planing / planing
regime (Fn >= ~0.6). Vessels with a design Froude number below that
threshold are rejected with ``ValueError`` -- they should use ``cetos.imo``.
"""

import copy
import math

from cetos import imo
from cetos.models import VesselData, VoyageProfile
from cetos.utils import (
    calculate_fuel_volume,
    calculate_installed_propulsion_power,
    knots_to_ms,
)

# ---------------------------------------------------------------------------
# Module-level constants used by more than one function below.
# ---------------------------------------------------------------------------

# Seawater density [kg/m^3]. Used by estimate_change_in_draft to translate a
# load delta into a waterplane displacement.
_RHO_SW_KG_PER_M3 = 1025.0

# Minimum design Froude number for HSVA Eq. 3.65 validity. Below this the
# vessel is in displacement mode and the IMO admiralty formula applies. Used
# in both the validation predicate and its error message.
_FN_PLANING_MIN = 0.6

# Vessel types within scope. PSH §3.4.1 lists planing-hull examples as fast
# patrol boats, racing boats, search and rescue boats, and fast small
# passenger ferries -- which map onto these three VESSEL_TYPES entries.
# Other types (cargo, large ferries, fishing) have their own methodology.
# Used in both the validation predicate and its error message.
_PLANING_TYPES = frozenset({"yacht", "miscellaneous-other", "service-other"})


# ---------------------------------------------------------------------------
# Scope validation
# ---------------------------------------------------------------------------


def _validate_in_scope(vessel_data: VesselData) -> None:
    """Hard-reject vessels outside the HSVA planing-hull scope.

    Message shape matches cetos.fishing: ``cetos.planing (HSVA scope):
    <constraint>; got <observed>. <remedy>.``
    """
    if vessel_data.type not in _PLANING_TYPES:
        raise ValueError(
            "cetos.planing (HSVA scope): vessel type must be one of "
            f"{sorted(_PLANING_TYPES)}; got {vessel_data.type!r}. "
            "Use cetos.imo for displacement-mode vessels or cetos.fishing "
            "for fishing vessels."
        )
    if vessel_data.displacement_kg is None:
        raise ValueError(
            "cetos.planing (HSVA scope): vessel_data.displacement_kg is "
            "required (static displacement at design_draft_m); got None. "
            "Eq. 3.65 takes displacement mass as an input and has no "
            "internal hydrostatics fallback."
        )
    # Length-based Froude number Fn = V / sqrt(g * L_wl); L_wl ~= 0.98 * L_oa
    # matches cetos.imo's waterline-length approximation.
    l_wl = vessel_data.length_m * 0.98
    fn = knots_to_ms(vessel_data.design_speed_kn) / math.sqrt(9.81 * l_wl)
    if fn < _FN_PLANING_MIN:
        raise ValueError(
            "cetos.planing (HSVA scope): design Froude number must be "
            f">= {_FN_PLANING_MIN} for planing-hull regime; got Fn = {fn:.3f} "
            f"(V = {vessel_data.design_speed_kn} kn, L = "
            f"{vessel_data.length_m} m). Use cetos.imo for displacement-mode "
            "vessels."
        )


# ---------------------------------------------------------------------------
# HSVA Eqs. 3.65 and 3.66
# ---------------------------------------------------------------------------


def _leg_brake_power_kw(vessel_data: VesselData, leg) -> float:
    """Brake power P_B [kW] for one voyage leg via HSVA Eqs. 3.65-3.66.

    Eq. 3.66 chine-beam estimate (design-stage):
        B_C = 0.215 * D^0.275                                       (B_C [m], D [kg])

    Eq. 3.65 brake-power formula:
        P_B = 0.7354 * (D * V / 765.2 + B_C^2 * V^3 / 1051.1)       (V [kn], P_B [kW])

    The 0.7354 prefactor absorbs unit conversions and the overall propulsive
    + mechanical efficiency baked into the HSVA fit -- P_B is brake power at
    the engine flange, not calm-water resistance.

    Displacement is read directly from ``vessel_data.displacement_kg``;
    leg.draft_m is intentionally not consulted (planing-hull draft does not
    vary leg-to-leg in operational practice, and the iteration weight-
    feedback channel for planing is ``_apply_change_in_displacement``).
    """
    disp_kg = vessel_data.displacement_kg
    b_c = 0.215 * disp_kg**0.275  # Eq. 3.66
    return 0.7354 * (  # Eq. 3.65
        disp_kg * leg.speed_kn / 765.2 + b_c**2 * leg.speed_kn**3 / 1051.1
    )


def _validate_leg_drafts(
    vessel_data: VesselData, voyage_profile: VoyageProfile
) -> None:
    """Reject per-leg drafts that differ from design draft.

    Planing-hull draft does not vary leg-to-leg in operational practice,
    and ``_leg_brake_power_kw`` deliberately ignores leg.draft_m. Setting
    a non-design draft would silently no-op, so we make it loud instead.
    Load changes are routed through ``vessel_data.displacement_kg`` via
    ``_apply_change_in_displacement``.
    """
    legs = (
        voyage_profile.legs_manoeuvring
        + voyage_profile.legs_at_sea
        + voyage_profile.legs_fishing
    )
    for leg in legs:
        if not math.isclose(leg.draft_m, vessel_data.design_draft_m):
            raise ValueError(
                "cetos.planing (HSVA scope): every leg draft must equal "
                f"vessel_data.design_draft_m={vessel_data.design_draft_m}; "
                f"got leg.draft_m={leg.draft_m}. Planing-hull draft does "
                "not vary leg to leg; route load deltas through "
                "vessel_data.displacement_kg instead."
            )


def _apply_change_in_displacement(
    vessel_data: VesselData, voyage_profile: VoyageProfile, load_change
):
    """Apply a displacement change to the (vessel_data, voyage_profile) state.

    Planing-hull propulsion (Eq. 3.65) takes displacement mass as input, so
    a load delta lands directly on a copy of vessel_data with
    ``displacement_kg`` bumped by ``load_change``. voyage_profile is
    returned unchanged. Mass conservation: ΔDisplacement = Δload exactly,
    no hydrostatic translation through Cwp.

    Called only by ``cetos.energy_systems._iterate_energy_system`` as its
    per-module mass-feedback channel.
    """
    new_vessel = copy.copy(vessel_data)
    new_vessel.displacement_kg = vessel_data.displacement_kg + load_change
    return new_vessel, voyage_profile


# ---------------------------------------------------------------------------
# Public API (mirrors cetos.imo / cetos.fishing)
# ---------------------------------------------------------------------------


def estimate_fuel_consumption_of_propulsion_engines(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    limit_7_percent: bool = True,
    delta_w=None,
):
    """Estimate fuel consumption of the propulsion engines for a planing hull.

    Per-leg flow: HSVA Eq. 3.65 gives required brake power P_B; load
    fraction is P_B / installed propulsion power (clipped to 1.0); SFC
    follows the IMO Fourth GHG Study 2020 via
    ``cetos.imo.estimate_specific_fuel_consumption``; leg fuel mass is
    P_B * SFC * t. Auxiliary-engine fuel is not included -- this function
    accounts only for the propulsion engines (mirroring ``cetos.imo``).

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance. Must have a design Froude number
            >= 0.6 (planing regime); otherwise a ``ValueError`` is raised.

        voyage_profile: VoyageProfile
            VoyageProfile instance. Only ``legs_at_sea`` and
            ``legs_manoeuvring`` contribute to propulsion fuel.

        limit_7_percent (optional): boolean
            If True, legs whose HSVA brake-power demand falls below 7% of
            installed propulsion power contribute zero fuel, matching the
            IMO low-load cut-off applied by ``cetos.imo``. Defaults to True.

        delta_w (optional): float
            Accepted for signature parity with ``cetos.imo`` but ignored;
            Eq. 3.65 has no MCR-derating knob -- weight changes flow in
            via leg draft (see ``estimate_change_in_draft``). Defaults
            to None.

    Returns:
    --------

        Tuple(float, float)
            Total fuel consumed (kg) and average fuel consumption (L/nm).

    Sources:
    --------

        [1] Bertram, V. (2012). Practical Ship Hydrodynamics (2nd ed.),
            Butterworth-Heinemann, §3.4.1, Eqs. 3.65-3.66.
        [2] Bertram, V. & Mesbahi, E. (2004). Estimating Resistance and
            Power of Fast Monohulls Employing Artificial Neural Nets.
        [3] IMO. Fourth IMO GHG Study 2020 (SFC tables via cetos.imo).
    """
    del delta_w
    _validate_in_scope(vessel_data)
    _validate_leg_drafts(vessel_data, voyage_profile)

    installed = calculate_installed_propulsion_power(vessel_data)
    total_fc_kg = 0.0
    total_distance_nm = 0.0

    for leg in voyage_profile.legs_at_sea + voyage_profile.legs_manoeuvring:
        p_b_kw = _leg_brake_power_kw(vessel_data, leg)
        load = min(p_b_kw / installed, 1.0) if installed > 0 else 0.0
        if load < 0.07 and limit_7_percent:
            sfc = 0.0
        else:
            sfc = imo.estimate_specific_fuel_consumption(
                load,
                vessel_data.propulsion_engine_type,
                vessel_data.propulsion_engine_fuel_type,
                vessel_data.propulsion_engine_age,
            )
        time_h = leg.distance_nm / leg.speed_kn
        # SFC is kg/kWh (see cetos.imo); fuel_kg = P_B * SFC * t.
        total_fc_kg += p_b_kw * sfc * time_h
        total_distance_nm += leg.distance_nm

    if total_distance_nm == 0:
        return total_fc_kg, 0.0
    avg_fc_lpnm = (
        calculate_fuel_volume(total_fc_kg, vessel_data.propulsion_engine_fuel_type)
        * 1_000
        / total_distance_nm
    )
    return total_fc_kg, avg_fc_lpnm


def estimate_energy_consumption(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers: bool = True,
    limit_7_percent: bool = True,
    delta_w=None,
):
    """Estimate the total energy consumption of a planing-hull vessel.

    Propulsion energy per leg is P_B * t with P_B from HSVA Eq. 3.65 (no
    SFC, since this is the shaft-energy demand rather than fuel). Auxiliary
    and steam-boiler loads are delegated to ``cetos.imo`` so the
    vessel-type-keyed power tables remain the single source of truth.

    Arguments:
    ----------

        vessel_data: VesselData

        voyage_profile: VoyageProfile

        include_steam_boilers (optional): boolean
            If True, the steam-boiler energy and peak power are included
            in the totals. Defaults to True.

        limit_7_percent (optional): boolean
            If True, legs whose HSVA brake-power demand falls below 7% of
            installed propulsion power contribute zero propulsion energy,
            matching the low-load cut-off used for fuel. Defaults to True.

        delta_w (optional): float
            Accepted for signature parity with ``cetos.imo`` but ignored;
            see ``estimate_fuel_consumption_of_propulsion_engines``.
            Defaults to None.

    Returns:
    --------

        Dict
            Dictionary with total energy consumption (kWh), maximum
            required total power demand (kW), and maximum required
            propulsion power (kW).
    """
    del delta_w
    _validate_in_scope(vessel_data)
    _validate_leg_drafts(vessel_data, voyage_profile)
    installed = calculate_installed_propulsion_power(vessel_data)

    def _sailing(legs, mode):
        if not legs:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        total_h = sum(leg.distance_nm / leg.speed_kn for leg in legs)
        p_aux, p_boiler = imo.estimate_auxiliary_power_demand(vessel_data, mode)
        prop_kwh = 0.0
        peak_prop = 0.0
        for leg in legs:
            p_b = _leg_brake_power_kw(vessel_data, leg)
            load = min(p_b / installed, 1.0) if installed > 0 else 0.0
            if load < 0.07 and limit_7_percent:
                continue
            prop_kwh += p_b * (leg.distance_nm / leg.speed_kn)
            peak_prop = max(peak_prop, p_b)
        return (
            prop_kwh,
            p_aux * total_h,
            p_boiler * total_h,
            peak_prop,
            p_aux,
            p_boiler,
        )

    def _stationary(hours, mode):
        if hours == 0:
            return 0.0, 0.0, 0.0, 0.0
        p_aux, p_boiler = imo.estimate_auxiliary_power_demand(vessel_data, mode)
        return p_aux * hours, p_boiler * hours, p_aux, p_boiler

    modes = []
    for legs, mode in (
        (voyage_profile.legs_manoeuvring, "manoeuvring"),
        (voyage_profile.legs_at_sea, "at_sea"),
    ):
        prop_kwh, aux_kwh, boiler_kwh, peak_prop, peak_aux, peak_boiler = _sailing(
            legs, mode
        )
        modes.append((prop_kwh, aux_kwh, boiler_kwh, peak_prop, peak_aux, peak_boiler))
    for hours, mode in (
        (voyage_profile.time_at_berth_h, "at_berth"),
        (voyage_profile.time_anchored_h, "anchored"),
    ):
        aux_kwh, boiler_kwh, peak_aux, peak_boiler = _stationary(hours, mode)
        modes.append((0.0, aux_kwh, boiler_kwh, 0.0, peak_aux, peak_boiler))

    total_kwh = 0.0
    peak_total_kw = 0.0
    peak_prop_kw = 0.0
    for prop_kwh, aux_kwh, boiler_kwh, peak_prop, peak_aux, peak_boiler in modes:
        total_kwh += prop_kwh + aux_kwh + (boiler_kwh if include_steam_boilers else 0.0)
        mode_peak = (
            peak_prop + peak_aux + (peak_boiler if include_steam_boilers else 0.0)
        )
        peak_total_kw = max(peak_total_kw, mode_peak)
        peak_prop_kw = max(peak_prop_kw, peak_prop)

    return {
        "total_kwh": total_kwh,
        "maximum_required_total_power_kw": peak_total_kw,
        "maximum_required_propulsion_power_kw": peak_prop_kw,
    }
