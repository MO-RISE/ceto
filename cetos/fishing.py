"""Fishing-vessel methodology — Vessel Energy Analysis Tool (VEAT).

Implements the metric reformulation of VEAT (Kemp 2018) from Appendix B of
Barman & Soerfeldt (2024), *A Method for Determining Feasibility of
Electrification of Small Fishing Vessels*. Public surface matches
``cetos.imo`` so callers (notably ``cetos.energy_systems``) can swap
methodology modules via the ``energy_module`` argument.

VEAT scope: displacement-hulled fishing vessels, 9-30 m LOA, design speed
<= 12 kn. Out-of-scope vessels are rejected with ``ValueError`` so callers
must explicitly select ``cetos.imo`` instead.

Subsystem activity by leg type (locked design decision, not configurable):
    propulsion    : manoeuvring + at_sea + fishing legs
    hydraulics    : fishing legs only                   (rho from gear lookup)
    DC            : manoeuvring + at_sea + fishing legs
    refrigeration : manoeuvring + at_sea + fishing legs (only if installed)

Time at anchor / berth contributes no engine load; small vessels rely on
shore power.
"""

import math

from cetos import utils
from cetos.models import VesselData, VoyageProfile

# ---------------------------------------------------------------------------
# Module-level constants used by more than one function below.
# Single-use coefficients (propulsion curve, engine alpha/beta, scope limits)
# are inlined into their function bodies with the equation reference as a
# comment, per project preference to minimise the API surface.
# ---------------------------------------------------------------------------

# Eq. B.3 hydraulic system efficiency (Table B.2 default). Used by both the
# hydraulic-energy helper and the peak-power calculation below.
_ETA_HYD = 0.96

# Eq. B.5 DC system (Table B.4 defaults). Used by both DC energy and DC peak.
_P_DC_KW = 0.3
_ETA_BATT = 0.8
_ETA_ALT = 0.6

# Refrigeration system power-source efficiency (Kemp 2018 Sec. 5, Table 12).
# Used by both refrigeration energy and refrigeration peak.
_ETA_REF = {"direct_drive": 1.0, "electric": 0.81, "hydraulic": 0.55}

# Per-gear deck-equipment power and within-fishing duty cycle.
# Source: Kemp 2018 Table 13 (deck_power_kw, duty_cycle rho). Keys map to the
# table row labels:
#   seine                          -> "Seine winch AND power block"
#   troll                          -> "Gurdies" (the troll-fishery deck load)
#   gill_net                       -> "Gill net drum"
#   gill_net_with_power_roller     -> "Gill net drum AND power roller"
#   longline_autoline              -> "Autoline haul system"
#   longline_sheave_or_drum        -> "Longline sheave OR drum"
#   longline_sheave_and_drum       -> "Longline sheave AND drum"
#   pot_large                      -> "Large pot hauler"
#   pot_small                      -> "Small pot hauler"
#   other                          -> "Other (cranes, etc)" (tender catch-all)
_GEAR_DECK = {
    "seine": (35.0, 0.20),
    "troll": (3.7, 1.00),
    "gill_net": (3.5, 0.15),
    "gill_net_with_power_roller": (5.2, 0.15),
    "longline_autoline": (7.4, 0.48),
    "longline_sheave_or_drum": (2.3, 0.48),
    "longline_sheave_and_drum": (2.8, 0.48),
    "pot_large": (8.0, 0.48),
    "pot_small": (4.0, 0.48),
    "other": (1.0, 1.00),
}


def _validate_vessel_in_scope(vessel_data):
    """Hard-reject vessels outside the VEAT validated band.

    All messages follow the shape
    ``cetos.fishing (VEAT scope): <constraint>; got <observed>. <remedy>.``
    so callers see a consistent prefix and always learn how to recover.
    """
    if vessel_data.type != "miscellaneous-fishing":
        raise ValueError(
            "cetos.fishing (VEAT scope): requires vessel type "
            f"'miscellaneous-fishing'; got {vessel_data.type!r}. "
            "Use cetos.imo for non-fishing vessels."
        )
    if not (9.0 <= vessel_data.length_m <= 30.0):
        raise ValueError(
            "cetos.fishing (VEAT scope): length_m must be between "
            f"9.0 and 30.0 m; got {vessel_data.length_m}. "
            "Outside the VEAT-validated band — use cetos.imo."
        )
    if vessel_data.design_speed_kn > 12.0:
        raise ValueError(
            "cetos.fishing (VEAT scope): design_speed_kn must be <= 12.0; "
            f"got {vessel_data.design_speed_kn}. "
            "Outside the VEAT-validated band — use cetos.imo."
        )
    if vessel_data.gear_type is None:
        raise ValueError(
            "cetos.fishing (VEAT scope): vessel_data.gear_type is required; "
            "got None. Set one of cetos.models.GEAR_TYPES."
        )


def _engine_coeffs(rated_power_kw):
    """Return (alpha [l/hr], beta [l/kWh]) for engine of rated power R [kW].

    Eqs. B.7-B.8 with Table B.6 coefficients:
        alpha = 0.984    + 4.10e-3 * R     [l/hr]      (Eq. B.7)
        beta  = 0.303    - 1.066e-4 * R    [l/kWh]    (Eq. B.8)

    Unit hazard: Table B.6 labels c3's units as "l/hr-hp-kW" suggesting R in
    hp, but the worked verification examples B.9-B.12 plug Fredrika's
    R = 242 kW (Table 2.1) directly into both formulas. R is in kW for BOTH
    coefficients — the table label is misleading.
    """
    alpha = 0.984 + 0.0041 * rated_power_kw
    beta = 0.303 + (-1.066e-4) * rated_power_kw
    return alpha, beta


def _propulsion_power_kw(length_m, beam_m, speed_kn):
    """Delivered propulsion power [kW] from speed [kn] and hull dims [m].

    Eq. B.1 (metric reformulation of Kemp 2018 §4):
        P(s) = 0.0214 * L * sqrt(B) * exp(0.57 * s)    for s >= 3 kn
        P(s) = (s/3)^3 * P(3)                          for s <  3 kn
    The cubic ramp below 3 kn keeps P -> 0 as s -> 0 and matches at the knee.
    """
    base = 0.0214 * length_m * math.sqrt(beam_m)
    if speed_kn >= 3.0:
        return base * math.exp(0.57 * speed_kn)
    p_at_knee = base * math.exp(0.57 * 3.0)
    return (speed_kn / 3.0) ** 3 * p_at_knee


def _hydraulic_energy_kwh(gear_type, hours_fishing):
    """Eq. B.3 hydraulic energy. rho is the gear-specific within-fishing duty."""
    p_deck, rho = _GEAR_DECK[gear_type]
    return p_deck * rho * hours_fishing / _ETA_HYD


def _dc_energy_kwh(hours_on):
    """Eq. B.5 DC energy."""
    return _P_DC_KW * hours_on / (_ETA_BATT * _ETA_ALT)


def _refrigeration_energy_kwh(power_kw, system_type, hours_on):
    """Collapsed Eq. B.2: avg installed power * on-time / power-source efficiency.

    Duty cycles f_comp and f_circ are absorbed into the caller-supplied
    ``power_kw``; the only configurable thing is whether refrigeration is
    on during a given leg type (see module docstring).
    """
    return power_kw * hours_on / _ETA_REF[system_type]


def _leg_time_h(leg):
    return leg.distance_nm / leg.speed_kn


# ---------------------------------------------------------------------------
# Public API (mirrors cetos.imo for energy_systems dispatch)
# ---------------------------------------------------------------------------


def estimate_fuel_consumption_of_propulsion_engines(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate the fuel consumption of the main engine of a fishing vessel.

    Small fishing vessels typically have a single main engine that drives the
    propeller AND every auxiliary (hydraulic pump, alternator, optional
    refrigeration compressor). Per Table 4.6 in [2] the engine model
    F = alpha + beta * P is integrated over delivered shaft power including
    auxiliary loads — the idle (alpha * h) plus beta * E_aux contributions
    are attributed back to the main engine.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel. Must be of type
            'miscellaneous-fishing', 9-30 m LOA, design speed <= 12 kn, and
            have ``gear_type`` set.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile. Time at
            berth/anchor is ignored (shore power assumed).

        limit_7_percent (optional): boolean
            Accepted for signature parity with ``cetos.imo`` but ignored;
            VEAT uses a continuous fuel-consumption polynomial with no
            low-load cut-off. Defaults to True.

        delta_w (optional): float
            Accepted for signature parity with ``cetos.imo`` but ignored;
            VEAT does not apply a speed-power correction factor. Defaults
            to None.

    Returns:
    --------

        Tuple(float, float)
            Total fuel consumed (kg) over the voyage and average fuel
            consumption (L/nm).

    Sources:
    --------

        [1] Kemp, J. (2018). Vessel energy analysis tool (VEAT).
        [2] Barman, A., & Soerfeldt, E. (2024). A method for determining
            feasibility of electrification of small fishing vessels.
            Appendix B contains the metric reformulation used here
            (Eqs. B.1, B.3, B.5, B.7, B.8).
    """
    del limit_7_percent, delta_w
    _validate_vessel_in_scope(vessel_data)

    alpha, beta = _engine_coeffs(vessel_data.propulsion_engine_power_kw)
    total_litres = 0.0
    total_nm = 0.0

    for leg in (
        voyage_profile.legs_manoeuvring
        + voyage_profile.legs_at_sea
        + voyage_profile.legs_fishing
    ):
        h = _leg_time_h(leg)
        p_kw = _propulsion_power_kw(
            vessel_data.length_m, vessel_data.beam_m, leg.speed_kn
        )
        total_litres += (alpha + beta * p_kw) * h
        total_nm += leg.distance_nm

    # Auxiliary shaft energy delivered by the main engine; its marginal fuel
    # cost is beta * E_aux (idle alpha * h is already covered above).
    hours_fishing = sum(_leg_time_h(leg) for leg in voyage_profile.legs_fishing)
    hours_at_sea = sum(_leg_time_h(leg) for leg in voyage_profile.legs_at_sea)
    hours_manoeuvring = sum(
        _leg_time_h(leg) for leg in voyage_profile.legs_manoeuvring
    )
    hours_dc_on = hours_manoeuvring + hours_at_sea + hours_fishing
    aux_energy_kwh = _hydraulic_energy_kwh(
        vessel_data.gear_type, hours_fishing
    ) + _dc_energy_kwh(hours_dc_on)
    if vessel_data.refrigeration_power_kw is not None:
        aux_energy_kwh += _refrigeration_energy_kwh(
            vessel_data.refrigeration_power_kw,
            vessel_data.refrigeration_system_type,
            hours_dc_on,
        )
    total_litres += beta * aux_energy_kwh

    fuel_kg = utils.calculate_fuel_mass(
        total_litres / 1_000.0, vessel_data.propulsion_engine_fuel_type
    )
    avg_l_per_nm = total_litres / total_nm if total_nm else 0.0
    return fuel_kg, avg_l_per_nm


def estimate_energy_consumption(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate the energy consumption of a fishing vessel.

    Sums shaft energy and bounds peak power across the VEAT subsystems.
    Subsystem activity by leg type is fixed (not configurable):

        propulsion    : manoeuvring + at_sea + fishing
        hydraulics    : fishing only                    (rho from gear lookup)
        DC            : manoeuvring + at_sea + fishing
        refrigeration : manoeuvring + at_sea + fishing  (only if installed)

    The peak power figure is a bound: propulsion peak plus every auxiliary
    that can be simultaneously active during a fishing leg.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel. Must be of type
            'miscellaneous-fishing', 9-30 m LOA, design speed <= 12 kn, and
            have ``gear_type`` set.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile. Time at
            berth/anchor is ignored (shore power assumed).

        include_steam_boilers (optional): boolean
            Accepted for signature parity with ``cetos.imo`` but ignored;
            small fishing vessels are not modelled as having steam boilers.
            Defaults to True.

        limit_7_percent (optional): boolean
            Accepted for signature parity with ``cetos.imo`` but ignored;
            see ``estimate_fuel_consumption_of_propulsion_engines``.
            Defaults to True.

        delta_w (optional): float
            Accepted for signature parity with ``cetos.imo`` but ignored;
            see ``estimate_fuel_consumption_of_propulsion_engines``.
            Defaults to None.

    Returns:
    --------

        Dict
            Dictionary with total energy consumption (kWh), maximum required
            total power demand (kW), maximum required propulsion power (kW),
            and a per-subsystem breakdown (propulsion_kwh, hydraulic_kwh,
            dc_kwh, refrigeration_kwh) for diagnostics.

    Sources:
    --------

        [1] Kemp, J. (2018). Vessel energy analysis tool (VEAT).
            Table 12 (refrigeration efficiencies), Table 13 (per-gear deck
            power and duty cycle).
        [2] Barman, A., & Soerfeldt, E. (2024). A method for determining
            feasibility of electrification of small fishing vessels.
            Appendix B contains the metric reformulation used here
            (Eqs. B.1, B.2, B.3, B.5).
    """
    del include_steam_boilers, limit_7_percent, delta_w
    _validate_vessel_in_scope(vessel_data)

    propulsion_kwh = 0.0
    peak_propulsion_kw = 0.0
    for leg in (
        voyage_profile.legs_manoeuvring
        + voyage_profile.legs_at_sea
        + voyage_profile.legs_fishing
    ):
        h = _leg_time_h(leg)
        p_kw = _propulsion_power_kw(
            vessel_data.length_m, vessel_data.beam_m, leg.speed_kn
        )
        propulsion_kwh += p_kw * h
        peak_propulsion_kw = max(peak_propulsion_kw, p_kw)

    hours_fishing = sum(_leg_time_h(leg) for leg in voyage_profile.legs_fishing)
    hours_at_sea = sum(_leg_time_h(leg) for leg in voyage_profile.legs_at_sea)
    hours_manoeuvring = sum(
        _leg_time_h(leg) for leg in voyage_profile.legs_manoeuvring
    )
    hours_dc_on = hours_manoeuvring + hours_at_sea + hours_fishing

    hyd_kwh = _hydraulic_energy_kwh(vessel_data.gear_type, hours_fishing)
    dc_kwh = _dc_energy_kwh(hours_dc_on)

    p_deck, _ = _GEAR_DECK[vessel_data.gear_type]
    peak_hyd_kw = p_deck / _ETA_HYD  # hydraulics is intermittent (duty rho)
    # but draws full P_deck when running, so this is its peak contribution.
    peak_dc_kw = _P_DC_KW / (_ETA_BATT * _ETA_ALT)

    if vessel_data.refrigeration_power_kw is not None:
        ref_kwh = _refrigeration_energy_kwh(
            vessel_data.refrigeration_power_kw,
            vessel_data.refrigeration_system_type,
            hours_dc_on,
        )
        peak_ref_kw = (
            vessel_data.refrigeration_power_kw
            / _ETA_REF[vessel_data.refrigeration_system_type]
        )
    else:
        ref_kwh = 0.0
        peak_ref_kw = 0.0

    # Bounding peak: propulsion peak + every aux that can be simultaneously
    # active during a fishing leg.
    peak_total_kw = peak_propulsion_kw + peak_hyd_kw + peak_dc_kw + peak_ref_kw
    total_kwh = propulsion_kwh + hyd_kwh + dc_kwh + ref_kwh

    return {
        "total_kwh": total_kwh,
        "maximum_required_total_power_kw": peak_total_kw,
        "maximum_required_propulsion_power_kw": peak_propulsion_kw,
        "propulsion_kwh": propulsion_kwh,
        "hydraulic_kwh": hyd_kwh,
        "dc_kwh": dc_kwh,
        "refrigeration_kwh": ref_kwh,
    }


def estimate_change_in_draft(vessel_data: VesselData, load_change):
    """Estimate the change in draft of a fishing vessel due to a change in load.

    TODO: Returns 0.0 unconditionally. The merchant-ship block-coefficient
    approximation in ``cetos.imo.estimate_change_in_draft`` is calibrated for
    cargo/tanker hull forms; fishing-boat hulls (beamy, full-bodied, often
    with high deadrise) have meaningfully different Cb/Cwp, so the delegated
    estimate is biased. A fishing-specific hydrostatics model is needed.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        load_change: float
            Change in load (kg).

    Returns:
    --------

        float
            Change in draft (m). Currently always 0.0 pending a
            fishing-specific hydrostatics model.
    """
    del vessel_data, load_change
    return 0.0
