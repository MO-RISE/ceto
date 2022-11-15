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
)

DENSITY_SEAWATER = 1025  # kg/m3


def estimate_electrical_engine_weight_and_volume(power):
    """Estimate the weight of a marine electrical engine

    Arguments:
    ----------

        power: int
            Engine's rated power in kilowatts (kW).

    Returns:
    --------

        Tuple(weight, volume)
            Weight (kg) and volume (m3) of the engine.
    """

    verify_range("power", power, 50, 800)
    volume = 0.0006 * power
    weight = 1.1183 * power
    return weight, volume


def estimate_internal_combustion_engine_weight_and_volume(power):
    """Estimate the mass and volume of an internal combustion engine

    Arguments:
    ----------

        power: int
            Engine's Maximum Continous Rating (MCR) power (kW).


    Returns:
    --------

        Tuple(weight, volume)
            Weight (kg) and volume (m3) of the engine.
    """

    verify_range("power", power, 50, 2000)
    volume = 0.0353 * power**0.6409
    weight = 38.946 * power**0.5865

    return weight, volume


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
    l_wl = vessel_data["length"] / 0.97  # See Ch 1. p. 1 in [1]
    b_wl = vessel_data["beam"]

    # Approximation of design block coefficient (c_b)
    f_n = 0.5144 * knots_to_ms(vessel_data["design_speed"]) / math.sqrt(9.81 * l_wl)
    c_b = 0.7 + (1 / 8) * math.atan((23 - 100 * f_n) / 4)

    # Approximation of the waterplane area coefficient (c_wp)
    c_wp = (1 + 2 * c_b) / 3  # see Ch 1.6 p. 31 in [2]

    # Waterplane area (a_wp)
    a_wp = c_wp * l_wl * b_wl

    # Assuming a constant waterplane area
    draft_change = load_change / (a_wp * DENSITY_SEAWATER)

    return draft_change


def estimate_internal_combustion_system_weight_and_volume(vessel_data, voyage_profile):
    """Estimate the weight and volume of an internal combustion system for a vessel
    and voyage profile

    Returns:
    --------

        Dict()
            Mass (kg) and volume (m3) of the internal combustion system.

    NOTE: The system does not include steam boilers.

    """

    # Propulsion engines
    (
        prop_engines_weight,
        prop_engines_volume,
    ) = estimate_internal_combustion_engine_weight_and_volume(
        vessel_data["propulsion_engine_power"]
    )
    prop_engines_weight *= vessel_data["number_of_propulsion_engines"]
    prop_engines_volume *= vessel_data["number_of_propulsion_engines"]

    # Gearboxes
    # Slow-Speed Diesel engines are assumed to not have a gearbox.
    # Gearboxes are assumed to have 1/5 of the weight and mass of the engine.
    if vessel_data["propulsion_engine_type"] != "SSD":
        gearboxes_weight = prop_engines_weight / 5.0
        gearboxes_volume = prop_engines_volume / 5.0
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
    (
        aux_engines_weight,
        aux_engines_volume,
    ) = estimate_internal_combustion_engine_weight_and_volume(max_aux_engine_power)
    aux_engines_weight *= 2.0
    aux_engines_volume *= 2.0

    # Fuel
    fuel_weight, _ = estimate_fuel_consumption(
        vessel_data, voyage_profile, include_steam_boilers=False
    )
    fuel_volume = calculate_fuel_volume(
        fuel_weight, vessel_data["propulsion_engine_fuel_type"]
    )

    # Totals
    total_weight = (
        prop_engines_weight + gearboxes_weight + aux_engines_weight + fuel_weight
    )
    total_volume = (
        prop_engines_volume + gearboxes_volume + aux_engines_volume + fuel_volume
    )

    return {
        "mass": total_weight,
        "volume": total_volume,
        "breakdown": {
            "mass": {
                "propulsion_engines": prop_engines_weight + gearboxes_weight,
                "auxiliary_engines": aux_engines_weight,
                "fuel": fuel_weight,
            },
            "volume": {
                "propulsion_engines": prop_engines_volume + gearboxes_volume,
                "auxiliary_engines": aux_engines_volume,
                "fuel": fuel_volume,
            },
        },
    }


def estimate_liquid_hydrogen_system_weight_and_volume(
    vessel_data, voyage_profile, fuel_cell_efficiency=0.45
):
    """Estimate the weight and volume of a liquid hydrogen system

    Arguments:
    ----------

        fuel_cell_efficiency (optional): float
            Efficiency of the fuel cell as a fraction.

    Returns:
    --------

        Dict('mass','volume)
            Mass (kg) and volume (m3) of the liquid hydrogen system.


    Sources:
    --------

        [1] Minnehan, J. J., & Pratt, J. W. (2017). Practical application limits of fuel cells
            and batteries for zero emission vessels (No. SAND-2017-12665). Sandia National Lab.(SNL-NM),
            Albuquerque, NM (United States).

    """
    energy, maximum_power, _ = estimate_energy_consumption(
        vessel_data, voyage_profile, include_steam_boilers=False, limit_7_percent=False
    )

    # Hydrogen
    energy_as_hydrogen = energy / fuel_cell_efficiency
    mass_hydrogen = energy_as_hydrogen * 3.6 / 119.96

    # Fuel cell
    mass_fuel_cell_system = (maximum_power - 61.868) / 0.1237  # Eq. 2.7 in [1]
    volume_fuel_cell_system = (maximum_power - 73.331) / 55.944  # Eq. 2.9 in [1]

    # Hydrogen stored as cryogenic liquid (-252 C)
    gravimetric_spec_liquid_tank = (
        8.7  # empty tank mass / H2 stored mass (kg/kg) Table 2.3 in [1]
    )
    volumentric_spec_liquid_tank = (
        24.8  # outer tank volume / H2 stored mass (L/kg) Table 2.3 in [1]
    )
    mass_liquid_tank = mass_hydrogen * gravimetric_spec_liquid_tank
    volume_liquid_tank = mass_hydrogen * volumentric_spec_liquid_tank * 0.001  # to m3
    total_mass_liquid_system = mass_hydrogen + mass_liquid_tank + mass_fuel_cell_system
    total_volume_liquid_system = volume_liquid_tank + volume_fuel_cell_system

    return {
        "mass": total_mass_liquid_system,
        "volume": total_volume_liquid_system,
        "breakdown": {
            "fuel_cell_system": {
                "mass": mass_fuel_cell_system,
                "volume": volume_fuel_cell_system,
                "power": maximum_power,
            },
            "liquid_tank": {
                "mass": mass_liquid_tank,
                "volume": volume_liquid_tank,
            },
            "hydrogen": {"mass": mass_hydrogen},
        },
    }


def estimate_gas_hydrogen_system_weight_and_volume(
    vessel_data, voyage_profile, fuel_cell_efficiency=0.45
):
    """Estimate the weight and volume of a gas hydrogen system

    Arguments:
    ----------

        energy: float
            Required energy in kilo Watts hour (kWh).

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
    energy, maximum_power, _ = estimate_energy_consumption(
        vessel_data, voyage_profile, include_steam_boilers=False, limit_7_percent=False
    )

    # Hydrogen
    energy_as_hydrogen = energy / fuel_cell_efficiency
    mass_hydrogen = energy_as_hydrogen * 3.6 / 119.96

    # Fuel cell
    mass_fuel_cell_system = (maximum_power - 61.868) / 0.1237  # Eq. 2.7 in [1]
    volume_fuel_cell_system = (maximum_power - 73.331) / 55.944  # Eq. 2.9 in [1]

    # Hydrogen stored as high pressure gas (350 bar / 500 psi)
    gravimetric_spec_gas_tank = (
        17.92  # empty tank mass / H2 stored mass (kg/kg) Table 2.3 in [1]
    )
    volumentric_spec_gas_tank = (
        93.7  # outer tank volume / H2 stored mass (L/kg) Table 2.3 in [1]
    )
    mass_gas_tank = mass_hydrogen * gravimetric_spec_gas_tank
    volume_gas_tank = mass_hydrogen * volumentric_spec_gas_tank * 0.001  # to m3
    total_mass_gas_system = mass_hydrogen + mass_gas_tank + mass_fuel_cell_system
    total_volume_gas_system = volume_gas_tank + volume_fuel_cell_system

    return {
        "mass": total_mass_gas_system,
        "volume": total_volume_gas_system,
        "breakdown": {
            "fuel_cell_system": {
                "mass": mass_fuel_cell_system,
                "volume": volume_fuel_cell_system,
                "power": maximum_power,
            },
            "gas_tank": {
                "mass": mass_gas_tank,
                "volume": volume_gas_tank,
            },
            "hydrogen": {"mass": mass_hydrogen},
        },
    }


def suggest_alternative_energy_systems(
    vessel_data, voyage_profile, draft_change_limit=0.05
):
    gas = iterate_energy_system(
        vessel_data,
        voyage_profile,
        estimate_gas_hydrogen_system_weight_and_volume,
        draft_change_limit=draft_change_limit,
    )
    liquid = iterate_energy_system(
        vessel_data,
        voyage_profile,
        estimate_liquid_hydrogen_system_weight_and_volume,
        draft_change_limit=draft_change_limit,
    )

    return gas, liquid


def iterate_energy_system(
    vessel_data, voyage_profile, estimate_weight_and_volume, draft_change_limit=0.05
):
    """Iterate energy system to address changes in draft due to changes in weight"""
    ice = estimate_internal_combustion_system_weight_and_volume(
        vessel_data, voyage_profile
    )
    mass = ice["mass"]
    iteration = 0
    voyage_profile_copy = voyage_profile.copy()
    while iteration < 100:
        new_system = estimate_weight_and_volume(vessel_data, voyage_profile_copy)

        change_draft = estimate_change_in_draft(vessel_data, new_system["mass"] - mass)

        if abs(change_draft) < draft_change_limit:
            print(change_draft)
            break

        voyage_profile_copy["legs_manoeuvring"] = [
            (distance, speed, draft + change_draft)
            for distance, speed, draft in voyage_profile_copy["legs_manoeuvring"]
        ]
        voyage_profile_copy["legs_at_sea"] = [
            (distance, speed, draft + change_draft)
            for distance, speed, draft in voyage_profile_copy["legs_at_sea"]
        ]
        mass = new_system["mass"]
        iteration += 1

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
