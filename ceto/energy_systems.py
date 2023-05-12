"""
Energy Systems
"""
import math
from ceto.utils import verify_range, knots_to_ms
from ceto.imo import (
    estimate_energy_consumption,
    calculate_fuel_volume,
    verify_vessel_data,
    verify_voyage_profile,
    estimate_fuel_consumption_of_propulsion_engines,
)

DENSITY_SEAWATER = 1025  # kg/m3

ELECTRICAL_ENGINE_VOLUMETRIC_POWER_DENSITY_KWPM3 = 1 / 0.0006
ELECTRICAL_ENGINE_GRAVIMETRIC_POWER_DENSITY_KWPKG = 1 / 1.1183
HYDROGEN_ENERGY_DENSITY_KWHPKG = 33.322  # 119.96 MJ / (3.6 MJ / kWh)

# Current estimates correspond to:
#   For fuel cell system: PowerCellution 100, see https://powercellgroup.com/
#   For battery packs: Corvus Orca Energy, https://corvusenergy.com/products/energy-storage-solutions/corvus-orca-energy/
#   For hydrogen gas tank: Hexagon Purus, see row "O" in https://www.hannovermesse.de/apollo/hannover_messe_2021/obs/Binary/A1090299/HexagonPurus_Type4_datasheet_2021.pdf

REFERENCE_VALUES = {
    "reference_fuel_cell_volume_m3": 0.730 * 0.9 * 2.2,
    "reference_fuel_cell_weight_kg": 1070,
    "reference_fuel_cell_power_kw": 185,
    "reference_fuel_cell_efficiency_pct": 45,
    "reference_battery_pack_volume_m3": 2.241 * 0.865 * 0.738,
    "reference_battery_pack_weight_kg": 1628,
    "reference_battery_pack_capacity_kwh": 124,
    "reference_battery_pack_depth_of_discharge_pct": 80,
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


def estimate_internal_combustion_engine(power_kw):
    """Estimate the key details of an internal combustion engine

    Arguments:
    ----------

        power: float
            Engine's Maximum Continous Rating (MCR) power (kW).


    Returns:
    --------

        Dict(weight, volume)
            Weight (kg) and volume (m3) of the engine.
    """

    verify_range("power", power_kw, 50, 2000)
    details = {}
    details["volume_m3"] = 0.0353 * power_kw**0.6409
    details["weight_kg"] = 38.946 * power_kw**0.5865
    return details


def _estimate_change_in_draft(vessel_data, load_change):
    """Estimate the change in draft of a vessel due to a change in load.

    Arguments:
    ----------

        vessel_data
            Dict containing the vessel data.

        load_change
            Change in load (kg)

    Returns:
    --------

        float
            Change in draft (m)

    Sources:
        [1] MAN Energy Solutions. (2018). Basic Principles of Ship Propulsion.
            Copenhagen: MAN Energy Solutions.
        [2] Schneekluth, H., & Bertram, V. (1998). Ship design for efficiency
            and economy (Vol. 218). Oxford: Butterworth-Heinemann.
    """

    # Approximations of length and breadth on waterline (l_wl, b_wl)
    l_wl = vessel_data["length"] * 0.98
    b_wl = vessel_data["beam"]

    # Approximation of design block coefficient (c_b)
    f_n = 0.5144 * knots_to_ms(vessel_data["design_speed"]) / math.sqrt(9.81 * l_wl)
    c_b = 0.7 + (1 / 8) * math.atan((23 - 100 * f_n) / 4)

    # Approximation of the waterplane area coefficient (c_wp)
    c_wp = (1 + 2 * c_b) / 3  # see Ch 1.6 p. 31 in [1]

    # Waterplane area (a_wp)
    a_wp = c_wp * l_wl * b_wl

    # Assuming a constant waterplane area
    draft_change = load_change / (a_wp * DENSITY_SEAWATER)

    return draft_change


def estimate_internal_combustion_system(vessel_data, voyage_profile):
    """Estimate the key details of an internal combustion system for a vessel
    and voyage profile

    Arguments:
    ----------

        vessel_data: Dict
            Dictionary containing the vessel data.

        voyage_profile: Dict
            Dictionary containing the voyage profile.

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
        vessel_data["propulsion_engine_power"]
    )
    prop_engines["weight_kg"] *= vessel_data["number_of_propulsion_engines"]
    prop_engines["volume_m3"] *= vessel_data["number_of_propulsion_engines"]

    # Gearboxes
    # Slow-Speed Diesel engines are assumed to not have a gearbox.
    # Gearboxes are assumed to have 1/5 of the weight and volumeof the engine.
    if vessel_data["propulsion_engine_type"] != "SSD":
        gearboxes_weight_kg = prop_engines["weight_kg"] / 5.0
        gearboxes_volume_m3 = prop_engines["volume_m3"] / 5.0
    else:
        gearboxes_weight_kg = 0.0
        gearboxes_volume_m3 = 0.0

    # Fuel
    fc_kg, _ = estimate_fuel_consumption_of_propulsion_engines(
        vessel_data,
        voyage_profile,
        limit_7_percent=False,
        delta_w=0.8,
    )

    fc_m3 = calculate_fuel_volume(fc_kg, vessel_data["propulsion_engine_fuel_type"])

    # Totals
    total_weight = prop_engines["weight_kg"] + gearboxes_weight_kg + fc_kg
    total_volume = prop_engines["volume_m3"] + gearboxes_volume_m3 + fc_m3

    return {
        "total_weight_kg": total_weight,
        "total_volume_m3": total_volume,
        "weight_breakdown": {
            "propulsion_engines": {
                "weight_per_engine_kg": prop_engines["weight_kg"]
                / vessel_data["number_of_propulsion_engines"],
                "volume_per_engine_m3": prop_engines["volume_m3"]
                / vessel_data["number_of_propulsion_engines"],
            },
            "gearboxes": {
                "weight_per_gearbox_kg": gearboxes_weight_kg
                / vessel_data["number_of_propulsion_engines"],
                "volume_per_gearbox_m3": gearboxes_volume_m3
                / vessel_data["number_of_propulsion_engines"],
            },
            "fuel": {"weight_kg": fc_kg, "volume_m3": fc_m3},
        },
    }


def estimate_vessel_battery_system(
    required_energy_kwh,
    required_power_kw,
    reference_battery_pack_volume_m3,
    reference_battery_pack_weight_kg,
    reference_battery_pack_capacity_kwh,
    reference_battery_pack_depth_of_discharge_pct,
    **kwargs,
):
    """Estimate the key details of a battery propulsion system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float

        reference_battery_pack_volume_m3: float

        reference_battery_pack_weight_kg: float

        reference_battery_pack_capacity_kwh: float

        reference_battery_pack_depth_of_discharge_pct: float

    Returns:
    --------

        Dict
            Dictionary containing the weight and volumes of the system
            and its components.

    """

    # Battery packs

    battery_packs_capacity_kwh = required_energy_kwh / (
        reference_battery_pack_depth_of_discharge_pct / 100
    )
    battery_packs_weight_kg = (
        battery_packs_capacity_kwh
        * reference_battery_pack_weight_kg
        / reference_battery_pack_capacity_kwh
    )
    battery_packs_volume_m3 = (
        battery_packs_capacity_kwh
        * reference_battery_pack_volume_m3
        / reference_battery_pack_capacity_kwh
    )

    # Electrical engine/s
    electrical_engine_power_kw = math.ceil(required_power_kw / 10) * 10
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
    electrical_engine_power_kw = math.ceil(required_power_kw / 10) * 10
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


def suggest_alternative_energy_systems(vessel_data, voyage_profile, reference_values):
    """Suggest alternative energy systems"""
    _verify_reference_values(reference_values)
    verify_vessel_data(vessel_data)
    verify_voyage_profile(voyage_profile)

    gas = _iterate_energy_system(
        vessel_data,
        voyage_profile,
        reference_values,
        estimate_vessel_gas_hydrogen_system,
    )

    battery = _iterate_energy_system(
        vessel_data, voyage_profile, reference_values, estimate_vessel_battery_system
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

    required_power_kw = propulsion_power_kw

    battery = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        **reference_values,
    )
    gas = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        **reference_values,
    )

    return gas, battery


def _iterate_energy_system(
    vessel_data,
    voyage_profile,
    reference_values,
    estimate_energy_system,
    include_steam_boilers=False,
    limit_7_percent=False,
    delta_w=0.8,
):
    """Iterate energy system to address changes in draft due to changes in weight"""
    ice = estimate_internal_combustion_system(vessel_data, voyage_profile)
    weight = ice["total_weight_kg"]
    iteration = 0
    voyage_profile_copy = voyage_profile.copy()
    while iteration < 100:
        energy = estimate_energy_consumption(
            vessel_data,
            voyage_profile_copy,
            include_steam_boilers=include_steam_boilers,
            limit_7_percent=limit_7_percent,
            delta_w=delta_w,
        )

        new_system = estimate_energy_system(
            energy["total_kwh"],
            energy["maximum_required_total_power_kw"],
            **reference_values,
        )

        change_draft = _estimate_change_in_draft(
            vessel_data, new_system["total_weight_kg"] - weight
        )

        if abs(change_draft) < vessel_data["design_draft"] * 0.01:
            break

        voyage_profile_copy["legs_manoeuvring"] = [
            (distance, speed, draft + change_draft)
            for distance, speed, draft in voyage_profile_copy["legs_manoeuvring"]
        ]
        voyage_profile_copy["legs_at_sea"] = [
            (distance, speed, draft + change_draft)
            for distance, speed, draft in voyage_profile_copy["legs_at_sea"]
        ]
        weight = new_system["total_weight_kg"]
        iteration += 1

    new_system["change_in_draft_m"] = _estimate_change_in_draft(
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
