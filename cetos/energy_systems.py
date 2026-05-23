"""
Energy Systems
"""

import copy
import math

from cetos.models import VesselData, VoyageLeg, VoyageProfile
from cetos.utils import calculate_fuel_volume, verify_range, verify_set

ELECTRICAL_ENGINE_VOLUMETRIC_POWER_DENSITY_KWPM3 = 1 / 0.0006
ELECTRICAL_ENGINE_GRAVIMETRIC_POWER_DENSITY_KWPKG = 1 / 1.1183
HYDROGEN_ENERGY_DENSITY_KWHPKG = 33.322  # 119.96 MJ / (3.6 MJ / kWh)

# Current estimates correspond to:
#   For fuel cell system: PowerCellution 100, see https://powercellgroup.com/
#   For battery packs: Corvus Orca Energy, https://corvusenergy.com/products/corvus-orca-ess
#   For hydrogen gas tank: Hexagon Purus, see row "O" in https://www.hannovermesse.de/apollo/hannover_messe_2021/obs/Binary/A1090299/HexagonPurus_Type4_datasheet_2021.pdf

REFERENCE_VALUES = {
    "reference_fuel_cell_volume_m3": 0.730 * 0.9 * 2.2,
    "reference_fuel_cell_weight_kg": 1070,
    "reference_fuel_cell_power_kw": 185,
    "reference_fuel_cell_efficiency_pct": 45,
    "reference_battery_pack_volume_m3": 0.600 * 0.430 * 0.163,
    "reference_battery_pack_weight_kg": 58,
    "reference_battery_pack_capacity_kwh": 5.65,
    "reference_battery_pack_depth_of_discharge_pct": 80,
    "reference_battery_pack_continuous_power_kw": 3 * 5.65,
    "reference_hydrogen_gas_tank_volume_m3": 1.033,
    "reference_hydrogen_gas_tank_capacity_kg": 18.4,
    "reference_hydrogen_gas_tank_weight_kg": 272,
}

FUEL_ENERGY_DENSITY_KWHPL = {
    "HFO": 33.4 * 3.6,
    "MDO": 36 * 3.6,
    "MeOH": 16 * 3.6,
    "LNG": 21.2 * 3.6,
}


def _verify_reference_values(reference_values):
    """Verify the reference values dict."""

    keys = [
        "reference_fuel_cell_volume_m3",
        "reference_fuel_cell_weight_kg",
        "reference_fuel_cell_power_kw",
        "reference_fuel_cell_efficiency_pct",
        "reference_battery_pack_volume_m3",
        "reference_battery_pack_weight_kg",
        "reference_battery_pack_capacity_kwh",
        "reference_battery_pack_depth_of_discharge_pct",
        "reference_battery_pack_continuous_power_kw",
        "reference_hydrogen_gas_tank_volume_m3",
        "reference_hydrogen_gas_tank_capacity_kg",
        "reference_hydrogen_gas_tank_weight_kg",
    ]
    missing = []
    for key in keys:
        if key not in reference_values:
            missing.append(key)

    if len(missing) != 0:
        raise Exception(f"Missing reference values: {missing}")


def estimate_internal_combustion_engine(power_kw, engine_class=None):
    """Estimate the key details of an internal combustion engine

    Arguments:
    ----------

        power: float
            Engine's Maximum Continous Rating (MCR) power (kW).

        engine_class (optional): str
            One of "SSD", "MSD", "HSD", "outboard". When omitted (default), the
            legacy single-curve regression is used and ``power_kw`` must be in
            [50, 2000]. When provided, the weight is routed through
            ``estimate_combustion_main_engine_weight`` with an RPM band implied
            by the class (SSD <= 400, MSD ~750, HSD ~1500 rpm); the volume
            still uses the legacy power-law fit (volume data by class is a
            documented gap). The valid power range widens to [5, 6000] kW.
            "outboard" is reserved but not yet supported.

    Returns:
    --------

        Dict(weight, volume)
            Weight (kg) and volume (m3) of the engine.
    """

    if engine_class is None:
        verify_range("power", power_kw, 50, 2000)
        return {
            "volume_m3": 0.0353 * power_kw**0.6409,
            "weight_kg": 38.946 * power_kw**0.5865,
        }

    verify_set("engine_class", engine_class, ["SSD", "MSD", "HSD", "outboard"])
    verify_range("power", power_kw, 5, 6000)

    if engine_class == "outboard":
        raise NotImplementedError(
            "outboard engine sizing pending — see fishing.py / planing.py TODOs"
        )

    rpm_by_class = {"SSD": 300, "MSD": 750, "HSD": 1500}
    weight_kg = estimate_combustion_main_engine_weight(
        power_kw, rpm=rpm_by_class[engine_class]
    )
    # TODO: replace with class-specific volume regression once datasheet data
    # is collected. The legacy power-law fit is a stop-gap.
    volume_m3 = 0.0353 * power_kw**0.6409
    return {"volume_m3": volume_m3, "weight_kg": weight_kg}


def estimate_internal_combustion_system(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    energy_module,
):
    """Estimate the key details of an internal combustion system for a vessel
    and voyage profile

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance containing the vessel data.

        voyage_profile: VoyageProfile
            VoyageProfile instance containing the voyage profile.

        energy_module: module
            Methodology module exposing ``estimate_fuel_consumption_of_propulsion_engines``
            with the same signature as ``cetos.imo``. Pass ``cetos.imo``,
            ``cetos.planing``, or ``cetos.fishing``.

    Returns:
    --------

        Dict(weight, volume)
            Weight (kg) and volume (m3) of the internal combustion system.

    Notes:
    ------

        The system does not include steam boilers or auxiliary engines.

    """
    # Propulsion engines
    prop_engines = estimate_internal_combustion_engine(
        vessel_data.propulsion_engine_power_kw
    )
    prop_engines["weight_kg"] *= vessel_data.number_of_propulsion_engines
    prop_engines["volume_m3"] *= vessel_data.number_of_propulsion_engines

    # Gearboxes
    # Slow-Speed Diesel engines are assumed to not have a gearbox.
    # Gearboxes are assumed to have 1/5 of the weight and volumeof the engine.
    if vessel_data.propulsion_engine_type != "SSD":
        gearboxes_weight_kg = prop_engines["weight_kg"] / 5.0
        gearboxes_volume_m3 = prop_engines["volume_m3"] / 5.0
    else:
        gearboxes_weight_kg = 0.0
        gearboxes_volume_m3 = 0.0

    # Fuel
    fc_kg, _ = energy_module.estimate_fuel_consumption_of_propulsion_engines(
        vessel_data,
        voyage_profile,
        limit_7_percent=False,
        delta_w=0.8,
    )

    fc_m3 = calculate_fuel_volume(fc_kg, vessel_data.propulsion_engine_fuel_type)

    # Totals
    total_weight = prop_engines["weight_kg"] + gearboxes_weight_kg + fc_kg
    total_volume = prop_engines["volume_m3"] + gearboxes_volume_m3 + fc_m3

    return {
        "total_weight_kg": total_weight,
        "total_volume_m3": total_volume,
        "weight_breakdown": {
            "propulsion_engines": {
                "weight_per_engine_kg": prop_engines["weight_kg"]
                / vessel_data.number_of_propulsion_engines,
                "volume_per_engine_m3": prop_engines["volume_m3"]
                / vessel_data.number_of_propulsion_engines,
            },
            "gearboxes": {
                "weight_per_gearbox_kg": gearboxes_weight_kg
                / vessel_data.number_of_propulsion_engines,
                "volume_per_gearbox_m3": gearboxes_volume_m3
                / vessel_data.number_of_propulsion_engines,
            },
            "fuel": {"weight_kg": fc_kg, "volume_m3": fc_m3},
        },
    }


def estimate_vessel_battery_system(
    required_energy_kwh,
    required_power_kw,
    required_propulsion_power_kw,
    reference_battery_pack_volume_m3,
    reference_battery_pack_weight_kg,
    reference_battery_pack_capacity_kwh,
    reference_battery_pack_depth_of_discharge_pct,
    reference_battery_pack_continuous_power_kw,
    **kwargs,
):
    """Estimate the key details of a battery propulsion system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float
            Maximum total power demand (kW). The pack count must be large
            enough to deliver this continuously.

        required_propulsion_power_kw: float
            Maximum propulsion power demand (kW). Used to size the
            electrical engine/s.

        reference_battery_pack_volume_m3: float

        reference_battery_pack_weight_kg: float

        reference_battery_pack_capacity_kwh: float

        reference_battery_pack_depth_of_discharge_pct: float

        reference_battery_pack_continuous_power_kw: float
            Continuous discharge power (kW) per reference pack.

    Returns:
    --------

        Dict
            Dictionary containing the weight and volumes of the system
            and its components.

    """

    # Battery packs: sized by whichever constraint binds, energy or power.
    packs_for_energy = required_energy_kwh / (
        reference_battery_pack_capacity_kwh
        * reference_battery_pack_depth_of_discharge_pct
        / 100
    )
    packs_for_power = required_power_kw / reference_battery_pack_continuous_power_kw
    number_of_packs = max(packs_for_energy, packs_for_power)

    battery_packs_capacity_kwh = number_of_packs * reference_battery_pack_capacity_kwh
    battery_packs_weight_kg = number_of_packs * reference_battery_pack_weight_kg
    battery_packs_volume_m3 = number_of_packs * reference_battery_pack_volume_m3

    # Electrical engine/s
    electrical_engine_power_kw = math.ceil(required_propulsion_power_kw / 10) * 10
    electrical_engine_weight_kg = (
        electrical_engine_power_kw / ELECTRICAL_ENGINE_GRAVIMETRIC_POWER_DENSITY_KWPKG
    )
    electrical_engine_volume_m3 = (
        electrical_engine_power_kw / ELECTRICAL_ENGINE_VOLUMETRIC_POWER_DENSITY_KWPM3
    )

    # Total weight and volume
    system_weight = battery_packs_weight_kg + electrical_engine_weight_kg
    system_volume = battery_packs_volume_m3 + electrical_engine_volume_m3

    return {
        "total_weight_kg": system_weight,
        "total_volume_m3": system_volume,
        "details": {
            "battery_packs": {
                "weight_kg": battery_packs_weight_kg,
                "volume_m3": battery_packs_volume_m3,
                "capacity_kwh": battery_packs_capacity_kwh,
            },
            "electrical_engines": {
                "weight_kg": electrical_engine_weight_kg,
                "volume_m3": electrical_engine_volume_m3,
                "power_kw": electrical_engine_power_kw,
            },
        },
    }


def estimate_vessel_gas_hydrogen_system(
    required_energy_kwh,
    required_power_kw,
    required_propulsion_power_kw,
    reference_fuel_cell_power_kw,
    reference_fuel_cell_weight_kg,
    reference_fuel_cell_volume_m3,
    reference_fuel_cell_efficiency_pct,
    reference_hydrogen_gas_tank_weight_kg,
    reference_hydrogen_gas_tank_volume_m3,
    reference_hydrogen_gas_tank_capacity_kg,
    **kwargs,
):
    """Estimate the weight and volume of a gas hydrogen system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float
            Maximum total power demand (kW). Used to size the fuel cell.

        required_propulsion_power_kw: float
            Maximum propulsion power demand (kW). Used to size the
            electrical engine/s.

        reference_fuel_cell_power_kw: float

        reference_fuel_cell_weight_kg: float

        reference_fuel_cell_volume_m3: float

        reference_fuel_cell_efficiency_pct: float

        reference_hydrogen_gas_tank_weight_kg: float

        reference_hydrogen_gas_tank_volume_kg: float

        reference_hydrogen_gas_tank_capacity_kg: float


    Returns:
    --------

        Dict
            Dictionary containing the weight and volumes of the system
            and its components.

    """

    # Hydrogen
    hydrogen_weight_kg = (
        required_energy_kwh / (reference_fuel_cell_efficiency_pct / 100)
    ) / HYDROGEN_ENERGY_DENSITY_KWHPKG

    # Fuel cell system
    fuel_cell_weight_kg = (
        required_power_kw * reference_fuel_cell_weight_kg / reference_fuel_cell_power_kw
    )
    fuel_cell_volume_m3 = (
        required_power_kw * reference_fuel_cell_volume_m3 / reference_fuel_cell_power_kw
    )

    # Electrical engine/s
    electrical_engine_power_kw = math.ceil(required_propulsion_power_kw / 10) * 10
    electrical_engine_weight_kg = (
        electrical_engine_power_kw / ELECTRICAL_ENGINE_GRAVIMETRIC_POWER_DENSITY_KWPKG
    )
    electrical_engine_volume_m3 = (
        electrical_engine_power_kw / ELECTRICAL_ENGINE_VOLUMETRIC_POWER_DENSITY_KWPM3
    )

    # Hydrogen gas tanks
    hydrogen_gas_tank_weight_kg = (
        hydrogen_weight_kg
        * reference_hydrogen_gas_tank_weight_kg
        / reference_hydrogen_gas_tank_capacity_kg
    )
    hydrogen_gas_tank_volume_m3 = (
        hydrogen_weight_kg
        * reference_hydrogen_gas_tank_volume_m3
        / reference_hydrogen_gas_tank_capacity_kg
    )

    # Total weight and volume
    system_weight = (
        hydrogen_weight_kg
        + hydrogen_gas_tank_weight_kg
        + fuel_cell_weight_kg
        + electrical_engine_weight_kg
    )
    system_volume = (
        hydrogen_gas_tank_volume_m3 + fuel_cell_volume_m3 + electrical_engine_volume_m3
    )

    return {
        "total_weight_kg": system_weight,
        "total_volume_m3": system_volume,
        "details": {
            "fuel_cell_system": {
                "weight_kg": fuel_cell_weight_kg,
                "volume_m3": fuel_cell_volume_m3,
                "power_kw": required_power_kw,
            },
            "electrical_engines": {
                "weight_kg": electrical_engine_weight_kg,
                "volume_m3": electrical_engine_volume_m3,
                "power_kw": electrical_engine_power_kw,
            },
            "gas_tanks": {
                "weight_kg": hydrogen_gas_tank_weight_kg,
                "volume_m3": hydrogen_gas_tank_volume_m3,
                "capacity_kg": hydrogen_weight_kg,
            },
            "hydrogen": {
                "weight_kg": hydrogen_weight_kg,
            },
        },
    }


def suggest_alternative_energy_systems(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    reference_values,
    energy_module,
):
    """Suggest alternative energy systems

    Arguments:
    ----------

        energy_module: module
            Methodology module supplying ``estimate_energy_consumption`` and
            ``estimate_fuel_consumption_of_propulsion_engines``. Pass
            ``cetos.imo``, ``cetos.planing``, or ``cetos.fishing``.
    """
    _verify_reference_values(reference_values)

    gas = _iterate_energy_system(
        vessel_data,
        voyage_profile,
        reference_values,
        estimate_vessel_gas_hydrogen_system,
        energy_module=energy_module,
    )

    battery = _iterate_energy_system(
        vessel_data,
        voyage_profile,
        reference_values,
        estimate_vessel_battery_system,
        energy_module=energy_module,
    )

    return gas, battery


def suggest_alternative_energy_systems_simple(
    average_fuel_consumption_lpnm,
    propulsion_engine_fuel_type,
    propulsion_power_kw,
    total_voyage_length_nm,
    reference_values,
):
    """Suggest alternative energy systems SIMPLE"""
    _verify_reference_values(reference_values)

    total_fc_l = average_fuel_consumption_lpnm * total_voyage_length_nm

    fuel_type = propulsion_engine_fuel_type
    required_energy_kwh = FUEL_ENERGY_DENSITY_KWHPL[fuel_type] * total_fc_l

    # No auxiliary load information available in this simplified API, so
    # propulsion power is reused as the total-power proxy for storage sizing.
    required_power_kw = propulsion_power_kw
    required_propulsion_power_kw = propulsion_power_kw

    battery = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **reference_values,
    )
    gas = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        required_propulsion_power_kw,
        **reference_values,
    )

    return gas, battery


def _iterate_energy_system(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    reference_values,
    estimate_energy_system,
    energy_module,
    include_steam_boilers=False,
    limit_7_percent=False,
    delta_w=0.8,
):
    """Iterate energy system to address changes in draft due to changes in weight"""
    ice = estimate_internal_combustion_system(
        vessel_data, voyage_profile, energy_module=energy_module
    )
    weight = ice["total_weight_kg"]
    iteration = 0
    voyage_profile_copy = copy.copy(voyage_profile)
    # Deep copy the leg lists since we'll modify them
    voyage_profile_copy.legs_manoeuvring = list(voyage_profile.legs_manoeuvring)
    voyage_profile_copy.legs_at_sea = list(voyage_profile.legs_at_sea)
    voyage_profile_copy.legs_fishing = list(voyage_profile.legs_fishing)

    while iteration < 100:
        energy = energy_module.estimate_energy_consumption(
            vessel_data,
            voyage_profile_copy,
            include_steam_boilers=include_steam_boilers,
            limit_7_percent=limit_7_percent,
            delta_w=delta_w,
        )

        new_system = estimate_energy_system(
            energy["total_kwh"],
            energy["maximum_required_total_power_kw"],
            energy["maximum_required_propulsion_power_kw"],
            **reference_values,
        )

        change_draft = energy_module.estimate_change_in_draft(
            vessel_data, new_system["total_weight_kg"] - weight
        )

        if abs(change_draft) < vessel_data.design_draft_m * 0.01:
            break

        voyage_profile_copy.legs_manoeuvring = [
            VoyageLeg(leg.distance_nm, leg.speed_kn, leg.draft_m + change_draft)
            for leg in voyage_profile_copy.legs_manoeuvring
        ]
        voyage_profile_copy.legs_at_sea = [
            VoyageLeg(leg.distance_nm, leg.speed_kn, leg.draft_m + change_draft)
            for leg in voyage_profile_copy.legs_at_sea
        ]
        voyage_profile_copy.legs_fishing = [
            VoyageLeg(leg.distance_nm, leg.speed_kn, leg.draft_m + change_draft)
            for leg in voyage_profile_copy.legs_fishing
        ]
        weight = new_system["total_weight_kg"]
        iteration += 1

    new_system["change_in_draft_m"] = energy_module.estimate_change_in_draft(
        vessel_data, new_system["total_weight_kg"] - ice["total_weight_kg"]
    )
    return new_system


def estimate_combustion_main_engine_weight(power, rpm=None):
    """Estimate the weight of a main engine

    Arguments:
    ----------

        power: int
            Power output of the engine at 100% Maximum Continous Rating (MCR) in
            kilo Watts (kW).

        rpm: int
            Revolutions Per Minute of the engine at 100% MCR.


    Returns:
    --------

        float
            Engine weight in kilograms.

    References:
    -----------

    [1] Dev, A. K., & Saha, M. (2021). Weight Estimation of Marine Propulsion
        and Power Generation Machinery.

    """
    verify_range("power", power, 0, 90_000)

    if rpm is None:
        return 0.00753 * power**1.139 * 1_000

    verify_range("rpm", rpm, 0, 5_000)

    # Low-speed engine (fig. 68 in [1])
    if rpm <= 400:
        return 0.0206 * power**1.0432 * 1_000

    # Medium-speed engine (fig. 70 in [1])
    if 400 <= rpm < 1000:
        return 0.0061 * power**1.0905 * 1_000

    # High-speed engine (fig. 72 in [1])
    return 0.0032 * power**1.0938 * 1_000
