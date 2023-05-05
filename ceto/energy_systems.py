"""
Energy Systems
"""
import math
from ceto.utils import verify_range, knots_to_ms
from ceto.imo import (
    estimate_auxiliary_power_demand,
    estimate_fuel_consumption,
    estimate_energy_consumption,
    calculate_fuel_volume,
    calculate_fuel_mass,
    verify_vessel_data,
    verify_voyage_profile,
)


# Sources
# https://www.statista.com/statistics/1312286/europe-green-hydrogen-production-and-import-costs-2030/
# COST_ESTIMATES = {
#     "marine_diesel_sek_per_liter": 25,
#     "green_hydrogen_sek_per_kg": 40,
#     "green_hydrogen_2030_sek_per_kg": 20,
#     "fuel_cell_system_sek_per_kW": 6_000,
#     "hydrogen_gas_tank_sek_per_stored_kg": 15_000,
#     "electrical_engine_sek_per_kW": 2_000,
#     "electricity_cost_sek_per_kWh": 0.3,
#     "battery_cost_sek_per_kWh": 5_000,
# }

# REFERENCE VALUES

DENSITY_SEAWATER = 1025  # kg/m3

# Current estimates correspond to:
#   For fuel cell system: PowerCellution 30 and 100, see https://powercellgroup.com/
#   For battery packs: Corvus Energy, see https://corvusenergy.com
#   For hydrogen gas tank: Table 2.3 in
#       Minnehan, J. J., & Pratt, J. W. (2017). Practical application limits of
#            fuel cells and batteries for zero emission vessels (No. SAND-2017-12665).
#            Sandia National Lab.(SNL-NM), Albuquerque, NM (United States)

REFERENCE_VALUES = {
    "electrical_engine_volumetric_power_density_kw_p_m3": 1 / 0.0006,
    "electrical_engine_gravimetric_power_density_kw_p_kg": 1 / 1.1183,
    "fuel_cell_system_volumetric_power_density_kw_p_m3": 139,
    "fuel_cell_system_gravimetric_power_density_kw_p_kg": 0.2,
    "fuel_cell_efficiency_per": 45,
    "battery_packs_volumetric_energy_density_kwh_p_m3": 88000,
    "battery_packs_gravimetric_energy_density_kwh_p_kg": 0.077,
    "battery_depth_of_discharge_per": 80,
    "hydrogen_gravimetric_energy_density_kwh_p_kg": 119.96 / 3.6,
    "hydrogen_gas_tank_container_weight_to_content_weight_ratio_kg_p_kg": 17.92,
    "hydrogen_gas_tank_container_volume_to_content_weight_ratio_l_p_kg": 93.7,
}

FUEL_ENERGY_DENSITY_KWH_P_L = {
    "HFO": 33.4 * 3.6,
    "MDO": 36 * 3.6,
    "MeOH": 16 * 3.6,
    "LNG": 21.2 * 3.6,
}


def _verify_reference_values(reference_values):
    keys = [
        "electrical_engine_volumetric_power_density_kw_p_m3",
        "electrical_engine_gravimetric_power_density_kw_p_kg",
        "fuel_cell_system_volumetric_power_density_kw_p_m3",
        "fuel_cell_system_gravimetric_power_density_kw_p_kg",
        "fuel_cell_efficiency_per",
        "battery_packs_volumetric_energy_density_kwh_p_m3",
        "battery_packs_gravimetric_energy_density_kwh_p_kg",
        "battery_depth_of_discharge_per",
        "hydrogen_gravimetric_energy_density_kwh_p_kg",
        "hydrogen_gas_tank_container_weight_to_content_weight_ratio_kg_p_kg",
        "hydrogen_gas_tank_container_volume_to_content_weight_ratio_l_p_kg",
    ]
    if not all([key in reference_values for key in keys]):
        raise Exception("Missing refrence values.")


def estimate_internal_combustion_engine(power):
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

    verify_range("power", power, 50, 2000)
    details = {}
    details["volume"] = 0.0353 * power**0.6409
    details["weight"] = 38.946 * power**0.5865
    return details


def estimate_change_in_draft(vessel_data, load_change):
    """Estimate the change in draft of a vessel due to a change in load.

    Arguments:
    ----------

        vessel_data
            Dict containing the vessel data.

        load_change
            Change in load (kg)

    Returns

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

        The system does not include steam boilers.

    """

    # Propulsion engines
    prop_engines = estimate_internal_combustion_engine(
        vessel_data["propulsion_engine_power"]
    )
    prop_engines["weight"] *= vessel_data["number_of_propulsion_engines"]
    prop_engines["volume"] *= vessel_data["number_of_propulsion_engines"]

    # Gearboxes
    # Slow-Speed Diesel engines are assumed to not have a gearbox.
    # Gearboxes are assumed to have 1/5 of the weight and volumeof the engine.
    if vessel_data["propulsion_engine_type"] != "SSD":
        gearboxes_weight = prop_engines["weight"] / 5.0
        gearboxes_volume = prop_engines["volume"] / 5.0
    else:
        gearboxes_weight = 0.0
        gearboxes_volume = 0.0

    # Auxiliary engines
    # Vessels are assumed to have two auxiliary engines, each capable of suppling
    # the entire auxiliary power demand.
    max_aux_engine_power = 0.0
    max_boiler_power = 0.0
    for operation_mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        aux_engine_power, boiler_power = estimate_auxiliary_power_demand(
            vessel_data, operation_mode
        )
        if aux_engine_power > max_aux_engine_power:
            max_aux_engine_power = aux_engine_power
        if boiler_power > max_boiler_power:
            max_boiler_power = boiler_power

    if max_aux_engine_power != 0.0:
        aux_engines = estimate_internal_combustion_engine(max_aux_engine_power)
        aux_engines["weight"] *= 2.0
        aux_engines["volume"] *= 2.0
    else:
        aux_engines = {"weight": 0.0, "volume": 0.0}

    # Fuel
    fuel_consumption = estimate_fuel_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=False,
        delta_w=0.8,
        limit_7_percent=False,
    )
    fuel_consumed_volume = calculate_fuel_volume(
        fuel_consumption["total_kg"], vessel_data["propulsion_engine_fuel_type"]
    )

    if "fuel_capacity" in vessel_data:
        fuel = vessel_data["fuel_capacity"] / 1_000  # liters to m3
        fuel_volume = calculate_fuel_mass(fuel)
    else:
        fuel = fuel_consumption["total_kg"]
        fuel_volume = fuel_consumed_volume

    # Totals
    total_weight = (
        prop_engines["weight"] + gearboxes_weight + aux_engines["weight"] + fuel
    )
    total_volume = (
        prop_engines["volume"] + gearboxes_volume + aux_engines["volume"] + fuel_volume
    )

    return {
        "total_weight_kg": total_weight,
        "total_volume_m3": total_volume,
        "fuel_consumption": fuel_consumption,
        "weight_breakdown": {
            "propulsion_engines": {
                "weight_per_engine_kg": prop_engines["weight"]
                / vessel_data["number_of_propulsion_engines"],
                "volume_per_engine_m3": prop_engines["volume"]
                / vessel_data["number_of_propulsion_engines"],
            },
            "gearboxes": {
                "weight_per_gearbox_kg": gearboxes_weight
                / vessel_data["number_of_propulsion_engines"],
                "volume_per_gearbox_m3": gearboxes_volume
                / vessel_data["number_of_propulsion_engines"],
            },
            "auxiliary_engines": {
                "weight_per_engine_kg": aux_engines["weight"] / 2,
                "volume_per_engine_m3": aux_engines["volume"] / 2,
            },
            "fuel": {"weight_kg": fuel, "volume_m3": fuel_volume},
        },
    }


def estimate_vessel_battery_system(
    required_energy_kwh,
    required_power_kw,
    number_of_propulsion_engines,
    double_ended,
    battery_packs_volumetric_energy_density_kwh_p_m3,
    battery_packs_gravimetric_energy_density_kwh_p_kg,
    battery_depth_of_discharge_per,
    electrical_engine_volumetric_power_density_kw_p_m3,
    electrical_engine_gravimetric_power_density_kw_p_kg,
    **kwargs,
):
    """Estimate the key details of a battery propulsion system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float

        battery_packs_volumetric_energy_density_kwh_p_m3: float

        battery_packs_gravimetric_energy_density_kwh_p_kg: float

        battery_depth_of_discharge_per: float

        electrical_engine_volumetric_power_density_kw_p_m3: float

        electrical_engine_gravimetric_power_density_kw_p_kg: float

        number_of_propulsion_engines: int

        double_ended: bool
            True if the vessel is double-ended, False otherwise.

    Returns:
    --------

        Dict
            Dictionary containing the weight and volumes of the system
            and its components.

    """

    # Battery packs
    battery_packs_capacity_kwh = required_energy_kwh / (
        battery_depth_of_discharge_per / 100
    )
    battery_packs_weight_kg = (
        battery_packs_capacity_kwh * battery_packs_gravimetric_energy_density_kwh_p_kg
    )
    battery_packs_volume_m3 = (
        battery_packs_capacity_kwh * battery_packs_volumetric_energy_density_kwh_p_m3
    )

    # Electrical engine/s
    if double_ended:
        electrical_engine_power_kw = required_power_kw / (
            number_of_propulsion_engines / 2
        )
    else:
        electrical_engine_power_kw = required_power_kw / number_of_propulsion_engines
    electrical_engine_power_kw = math.ceil(electrical_engine_power_kw / 10) * 10
    electrical_engine_weight_kg = (
        electrical_engine_power_kw / electrical_engine_gravimetric_power_density_kw_p_kg
    )
    electrical_engine_volume_m3 = (
        electrical_engine_power_kw / electrical_engine_volumetric_power_density_kw_p_m3
    )

    # Total weight and volume
    system_weight = (
        battery_packs_weight_kg
        + electrical_engine_weight_kg * number_of_propulsion_engines
    )
    system_volume = (
        battery_packs_volume_m3
        + electrical_engine_volume_m3 * number_of_propulsion_engines
    )

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
                "weight_per_engine_kg": electrical_engine_weight_kg,
                "volume_per_engine_m3": electrical_engine_volume_m3,
                "power_per_engine_kw": electrical_engine_power_kw,
                "number_of_engines": number_of_propulsion_engines,
            },
        },
    }


def estimate_vessel_gas_hydrogen_system(
    required_energy_kwh,
    required_power_kw,
    number_of_propulsion_engines,
    double_ended,
    fuel_cell_system_volumetric_power_density_kw_p_m3,
    fuel_cell_system_gravimetric_power_density_kw_p_kg,
    electrical_engine_volumetric_power_density_kw_p_m3,
    electrical_engine_gravimetric_power_density_kw_p_kg,
    fuel_cell_efficiency_per,
    hydrogen_gravimetric_energy_density_kwh_p_kg,
    hydrogen_gas_tank_container_weight_to_content_weight_ratio_kg_p_kg,
    hydrogen_gas_tank_container_volume_to_content_weight_ratio_l_p_kg,
    **kwargs,
):
    """Estimate the weight and volume of a gas hydrogen system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float

        fuel_cell_system_volumetric_power_density_kw_p_m3: float

        fuel_cell_system_gravimetric_power_density_kw_p_kg: float

        electrical_engine_volumetric_power_density_kw_p_m3: float

        electrical_engine_gravimetric_power_density_kw_p_kg: float

        fuel_cell_efficiency_per: float

        hydrogen_gravimetric_energy_density_kwh_p_kg: float

        number_of_propulsion_engines: int

        double_ended: bool
            True if the vessel is double-ended, False otherwise.

    Returns:
    --------

        Dict
            Dictionary containing the weight and volumes of the system
            and its components.

    """

    # Hydrogen
    hydrogen_weight_kg = (
        required_energy_kwh / (fuel_cell_efficiency_per / 100)
    ) / hydrogen_gravimetric_energy_density_kwh_p_kg

    # Fuel cell system
    fuel_cell_system_weight = (
        required_power_kw / fuel_cell_system_gravimetric_power_density_kw_p_kg
    )
    fuel_cell_system_volume = (
        required_power_kw / fuel_cell_system_volumetric_power_density_kw_p_m3
    )

    # Electrical engine/s
    if double_ended:
        electrical_engine_power_kw = required_power_kw / (
            number_of_propulsion_engines / 2
        )
    else:
        electrical_engine_power_kw = required_power_kw / number_of_propulsion_engines
    electrical_engine_power_kw = math.ceil(electrical_engine_power_kw / 10) * 10
    electrical_engine_weight_kg = (
        electrical_engine_power_kw / electrical_engine_gravimetric_power_density_kw_p_kg
    )
    electrical_engine_volume_m3 = (
        electrical_engine_power_kw / electrical_engine_volumetric_power_density_kw_p_m3
    )

    hydrogen_gas_tank_weight = (
        hydrogen_weight_kg
        * hydrogen_gas_tank_container_weight_to_content_weight_ratio_kg_p_kg
    )
    volume_gas_tank = (
        hydrogen_weight_kg
        * hydrogen_gas_tank_container_volume_to_content_weight_ratio_l_p_kg
        * 0.001
    )  # to m3

    # Total weight and volume
    system_weight = (
        hydrogen_weight_kg
        + hydrogen_gas_tank_weight
        + fuel_cell_system_weight
        + electrical_engine_weight_kg * number_of_propulsion_engines
    )
    system_volume = (
        volume_gas_tank
        + fuel_cell_system_volume
        + electrical_engine_volume_m3 * number_of_propulsion_engines
    )

    return {
        "total_weight_kg": system_weight,
        "total_volume_m3": system_volume,
        "details": {
            "fuel_cell_system": {
                "weight_kg": fuel_cell_system_weight,
                "volume_m3": fuel_cell_system_volume,
                "power_kw": required_power_kw,
            },
            "electrical_engines": {
                "weight_per_engine_kg": electrical_engine_weight_kg,
                "volume_per_engine_m3": electrical_engine_volume_m3,
                "power_per_engine_kw": electrical_engine_power_kw,
                "number_of_engines": number_of_propulsion_engines,
            },
            "gas_tanks": {
                "weight_kg": hydrogen_gas_tank_weight,
                "volume_m3": volume_gas_tank,
                "capacity_kg": hydrogen_weight_kg,
            },
            "hydrogen": {
                "weight_kg": hydrogen_weight_kg,
            },
        },
    }


def suggest_alternative_energy_systems(vessel_data, voyage_profile, reference_values):
    verify_vessel_data(vessel_data)
    verify_voyage_profile(voyage_profile)
    _verify_reference_values(reference_values)

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
    vessel_data_simple, total_voyage_length_nm, reference_values
):
    """Suggest alternative energy systems SIMPLE

    Arguements:
    -----------

        vessel_data_simple: dict
            {
                "average_fuel_consumption_lpnm": 10.0
                "propulsion_engine_fuel_type": "MDO",
                "number_of_propulsion_engines": 4,
                "propulsion_engine_power": 330,
                "double_ended": False
            }
    """

    total_fc_l = (
        vessel_data_simple["average_fuel_consumption_lpnm"] * total_voyage_length_nm
    )

    fuel_type = vessel_data_simple["propulsion_engine_fuel_type"]
    print(FUEL_ENERGY_DENSITY_KWH_P_L[fuel_type])
    print(total_fc_l)
    required_energy_kwh = FUEL_ENERGY_DENSITY_KWH_P_L[fuel_type] * total_fc_l

    required_power_kw = (
        vessel_data_simple["propulsion_engine_power"]
        + vessel_data_simple["number_of_propulsion_engines"]
    )
    if vessel_data_simple["double_ended"]:
        required_power_kw /= 2

    battery = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        vessel_data_simple["number_of_propulsion_engines"],
        vessel_data_simple["double_ended"],
        **reference_values,
    )
    gas = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        vessel_data_simple["number_of_propulsion_engines"],
        vessel_data_simple["double_ended"],
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
            vessel_data["number_of_propulsion_engines"],
            vessel_data["double_ended"],
            **reference_values,
        )

        change_draft = estimate_change_in_draft(
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

    new_system["change_in_draft_m"] = estimate_change_in_draft(
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
