"""
Vessel weight functions
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
    verify_voyage_profile
)

DENSITY_SEAWATER = 1025  # kg/m3

# Sources
# https://www.statista.com/statistics/1312286/europe-green-hydrogen-production-and-import-costs-2030/
COST_ESTIMATES = {
    "marine_diesel_sek_per_liter": 25,
    "green_hydrogen_sek_per_kg": 40,
    "green_hydrogen_2030_sek_per_kg": 20,
    "fuel_cell_system_sek_per_kW": 6_000,
    "hydrogen_gas_tank_sek_per_stored_kg": 15_000,
    "electrical_engine_sek_per_kW": 2_000,
    "electricity_cost_sek_per_kWh": 0.3,
    "battery_cost_sek_per_kWh": 5_000,
}


def estimate_electrical_engine(power):
    """Estimate the key details of a marine electrical engine

    Arguments:
    ----------

        power: float
            Engine's rated power in kilowatts (kW).

    Returns:
    --------

        Dict(weight, volume, cost)
            Weight (kg), volume (m3), and cost (sek) of the engine.
    """

    # The range of values comes from the statistical analysis of
    # electrical engines.
    #try:
    #   verify_range("power", power, 50, 1500)
    power = math.ceil(power / 10) * 10
    details = {}
    details["volume"] = 0.0006 * power
    details["weight"] = 1.1183 * power
    details["power"] = power
    details["cost"] = COST_ESTIMATES["electrical_engine_sek_per_kW"] * power
    return details


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

    NOTE: The system does not include steam boilers.

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


def estimate_fuel_cell_system(power):
    """Estimate the key details of a fuell cell system

    The fuel cell system is considered to be the fuel cell and all the necessary
    support sub-systems (i.e. cooling).

    Assumes that the Fuel Cell is a PowerCellution 200kW.

    """
    details = {}
    power_electronics_weight = 24
    power_electronics_volume = 46
    if power < 30:
        details["volume"] = 0.210 + power_electronics_volume
        details["weight"] = 150 + power_electronics_weight
        details["power"] = 30
    elif power < 100:
        details["volume"] = 0.284 + power_electronics_volume
        details["weight"] = 212 + power_electronics_weight
        details["power"] = 100
    else:
        number_of_cells = math.ceil(power / 200)
        details["volume"] = number_of_cells * 1.44
        details["weight"] = number_of_cells * 1070
        details["power"] = 200 * number_of_cells

    details["cost"] = COST_ESTIMATES["fuel_cell_system_sek_per_kW"] * power
    return details


def estimate_vessel_battery_system(vessel_data, voyage_profile):
    """Estimate the key parameters of a battery propulsion system

    Sources:
    --------

        [1] Minnehan, J. J., & Pratt, J. W. (2017). Practical application limits of fuel cells
            and batteries for zero emission vessels (No. SAND-2017-12665). Sandia National Lab.(SNL-NM),
            Albuquerque, NM (United States).

    """

    energy = estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=False,
        limit_7_percent=False,
        delta_w=0.8,
    )

    # Batteries
    battery_capacity = energy["total_kWh"] / 0.8  # Depth of discharge of 80%
    mass_battery_system = (battery_capacity + 2.8172) / 0.075
    volume_battery_system = (battery_capacity + 5.0624) / 72.268

    # Electrical engine
    if vessel_data["double_ended"]:
        engine_power = energy["maximum_required_propulsion_power_kW"] / (
            vessel_data["number_of_propulsion_engines"] / 2
        )
    else:
        engine_power = (
            energy["maximum_required_propulsion_power_kW"]
            / vessel_data["number_of_propulsion_engines"]
        )
    el_engine = estimate_electrical_engine(engine_power)

    # Total weight and volume
    total_mass_battery_system = (
        mass_battery_system
        + el_engine["weight"] * vessel_data["number_of_propulsion_engines"]
    )
    total_volume_battery_system = (
        volume_battery_system
        + el_engine["volume"] * vessel_data["number_of_propulsion_engines"]
    )

    # Costs
    # electricity_cost = battery_capacity * COST_ESTIMATES["electricity_cost_sek_per_kWh"]
    # battery_system_cost = (
    #     mass_battery_system * COST_ESTIMATES["battery_cost_sek_per_kWh"]
    # )
    # components_cost = (
    #     battery_system_cost
    #     + el_engine["cost"] * vessel_data["number_of_propulsion_engines"]
    # )

    return {
        "total_weight_kg": total_mass_battery_system,
        "total_volume_m3": total_volume_battery_system,
        "details": {
            "battery_system": {
                "weight_kg": mass_battery_system,
                "volume_m3": volume_battery_system,
                "capacity_kWh": battery_capacity,
            },
            "electrical_engines": {
                "weight_per_engine_kg": el_engine["weight"],
                "volume_per_engine_m3": el_engine["volume"],
                "power_per_engine_kW": el_engine["power"],
                "number_of_engines": vessel_data["number_of_propulsion_engines"],
            },
        },
    }


def estimate_vessel_gas_hydrogen_system(
    vessel_data,
    voyage_profile,
    fuel_cell_efficiency=0.45,
):
    """Estimate the weight and volume of a gas hydrogen system

    Arguments:
    ----------

        vessel_data: Dict
            Dictionary containing the vessel data.

        voyage_profile: Dict
            Dictionary containing the voyage profile

        fuel_cell_efficiency (optional): float
            Efficiency of the fuel cell as a fraction.

    Returns:
    --------

        Dict('mass','volume)
            Mass (kg) and volume (m3) of the gas hydrogen system.


    Sources:
    --------

        [1] Minnehan, J. J., & Pratt, J. W. (2017). Practical application limits of fuel cells
            and batteries for zero emission vessels (No. SAND-2017-12665). Sandia National Lab.(SNL-NM),
            Albuquerque, NM (United States).

    """
    energy = estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=False,
        limit_7_percent=False,
        delta_w=0.8,
    )

    # Hydrogen
    energy_as_hydrogen = energy["total_kWh"] / fuel_cell_efficiency
    mass_hydrogen = energy_as_hydrogen * 3.6 / 119.96

    # Fuel cell
    fuel_cell_system = estimate_fuel_cell_system(
        energy["maximum_required_total_power_kW"]
    )

    # Electrical engine
    if vessel_data["double_ended"]:
        engine_power = energy["maximum_required_propulsion_power_kW"] / (
            vessel_data["number_of_propulsion_engines"] / 2
        )
    else:
        engine_power = (
            energy["maximum_required_propulsion_power_kW"]
            / vessel_data["number_of_propulsion_engines"]
        )
    el_engine = estimate_electrical_engine(engine_power)

    # Hydrogen stored as high pressure gas (350 bar / 500 psi)
    gravimetric_spec_gas_tank = (
        17.92  # empty tank mass / H2 stored mass (kg/kg) Table 2.3 in [1]
    )
    volumentric_spec_gas_tank = (
        93.7  # outer tank volume / H2 stored mass (L/kg) Table 2.3 in [1]
    )
    mass_gas_tank = mass_hydrogen * gravimetric_spec_gas_tank
    volume_gas_tank = mass_hydrogen * volumentric_spec_gas_tank * 0.001  # to m3

    # Total weight and volume
    total_mass_gas_system = (
        mass_hydrogen
        + mass_gas_tank
        + fuel_cell_system["weight"]
        + el_engine["weight"] * vessel_data["number_of_propulsion_engines"]
    )
    total_volume_gas_system = (
        volume_gas_tank
        + fuel_cell_system["volume"]
        + el_engine["volume"] * vessel_data["number_of_propulsion_engines"]
    )

    # # Costs
    # hydrogen_cost = COST_ESTIMATES["green_hydrogen_sek_per_kg"] * mass_hydrogen
    # hydrogen_cost_2030 = (
    #     COST_ESTIMATES["green_hydrogen_2030_sek_per_kg"] * mass_hydrogen
    # )
    # tank_cost = COST_ESTIMATES["hydrogen_gas_tank_sek_per_stored_kg"] * mass_hydrogen
    # components_cost = (
    #     fuel_cell_system["cost"]
    #     + tank_cost
    #     + el_engine["cost"] * vessel_data["number_of_propulsion_engines"]
    # )

    return {
        "total_weight_kg": total_mass_gas_system,
        "total_volume_m3": total_volume_gas_system,
        "details": {
            "fuel_cell_system": {
                "weight_kg": fuel_cell_system["weight"],
                "volume_m3": fuel_cell_system["volume"],
                "power_kW": fuel_cell_system["power"],
            },
            "electrical_engines": {
                "weight_per_engine_kg": el_engine["weight"],
                "volume_per_engine_m3": el_engine["volume"],
                "power_per_engine_kW": el_engine["power"],
                "number_of_engines": vessel_data["number_of_propulsion_engines"],
            },
            "gas_tanks": {
                "weight_kg": mass_gas_tank,
                "volume_m3": volume_gas_tank,
                "capacity_kg": mass_hydrogen,
            },
            "hydrogen": {
                "weight_kg": mass_hydrogen,
            },
        },
    }


def suggest_alternative_energy_systems(vessel_data, voyage_profile):
    
    verify_vessel_data(vessel_data)
    verify_voyage_profile(voyage_profile)
    
        
    gas = iterate_energy_system(
        vessel_data, voyage_profile, estimate_vessel_gas_hydrogen_system
    )

    battery = iterate_energy_system(
        vessel_data, voyage_profile, estimate_vessel_battery_system
    )

    return gas, battery


def iterate_energy_system(vessel_data, voyage_profile, estimate_weight_and_volume):
    """Iterate energy system to address changes in draft due to changes in weight"""
    ice = estimate_internal_combustion_system(vessel_data, voyage_profile)
    mass = ice["total_weight_kg"]
    iteration = 0
    voyage_profile_copy = voyage_profile.copy()
    while iteration < 100:
        new_system = estimate_weight_and_volume(vessel_data, voyage_profile_copy)

        change_draft = estimate_change_in_draft(
            vessel_data, new_system["total_weight_kg"] - mass
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
        mass = new_system["total_weight_kg"]
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
            Power output of the engine at 100% Maximum Continous Rating (MCR) in kilo Watts (kW).

        rpm: int
            Revolutions Per Minute of the engine at 100% MCR.


    Returns:
    --------

        float
            Engine weight in kilograms.

    References:
    -----------

    [1] Dev, A. K., & Saha, M. (2021). Weight Estimation of Marine Propulsion and Power
        Generation Machinery.

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
