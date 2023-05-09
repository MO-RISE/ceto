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
    estimate_fuel_consumption_of_propulsion_engines,
)


DENSITY_SEAWATER = 1025  # kg/m3

# Current estimates correspond to:
#   For fuel cell system: PowerCellution 30 and 100, see https://powercellgroup.com/
#   For battery packs: Corvus Energy, see https://corvusenergy.com
#   For hydrogen gas tank: Table 2.3 in
#       Minnehan, J. J., & Pratt, J. W. (2017). Practical application limits of
#            fuel cells and batteries for zero emission vessels (No. SAND-2017-12665).
#            Sandia National Lab.(SNL-NM), Albuquerque, NM (United States)

# REFERENCE_VALUES = {
#     "electrical_engine_volumetric_power_density_kwpm3": 1 / 0.0006,
#     "electrical_engine_gravimetric_power_density_kwpkg": 1 / 1.1183,
#     "fuel_cell_system_volumetric_power_density_kwpm3": 139,
#     "fuel_cell_system_gravimetric_power_density_kwpkg": 0.2,
#     "fuel_cell_efficiency_pct": 45,
#     "battery_packs_volumetric_energy_density_kwhpm3": 88000,
#     "battery_packs_gravimetric_energy_density_kwhpkg": 0.077,
#     "battery_depth_of_discharge_pct": 80,
#     "hydrogen_gravimetric_energy_density_kwhpkg": 119.96 / 3.6,
#     "hydrogen_gas_tank_container_weight_to_content_weight_ratio_kgpkg": 17.92,
#     "hydrogen_gas_tank_container_volume_to_content_weight_ratio_lpkg": 93.7,
# }

ELECTRICAL_ENGINE_VOLUMETRIC_POWER_DENSITY_KWPM3 = 1 / 0.0006
ELECTRICAL_ENGINE_GRAVIMETRIC_POWER_DENSITY_KWPKG = 1 / 1.1183
HYDROGEN_ENERGY_DENSITY_KWHPKG = 33.322  # 119.96 MJ / (3.6 MJ / kWh)

REFERENCE_VALUES = {
    "fuel_cell_volume_m3": 0.730 * 0.9 * 2.2,
    "fuel_cell_weight_kg": 1070,
    "fuel_cell_power_kw": 185,
    "fuel_cell_efficiency_pct": 45,
    "battery_pack_volume_m3": 2.241 * 0.865 * 0.738,
    "battery_pack_weight_kg": 1628,
    "battery_pack_capacity_kwh": 124,
    "battery_pack_depth_of_discharge_pct": 80,
    "hydrogen_gas_tank_volume_m3": 159.0,
    "hydrogen_gas_tank_capacity_kg": 1.8,
}

FUEL_ENERGY_DENSITY_KWHPL = {
    "HFO": 33.4 * 3.6,
    "MDO": 36 * 3.6,
    "MeOH": 16 * 3.6,
    "LNG": 21.2 * 3.6,
}

REFERENCE_VALUES = {
    "fuel_cell_volume_m3": 0.730 * 0.9 * 2.2,
    "fuel_cell_weight_kg": 1070,
    "fuel_cell_power_kw": 185,
    "fuel_cell_efficiency_pct": 45,
    "battery_pack_volume_m3": 2.241 * 0.865 * 0.738,
    "battery_pack_weight_kg": 1628,
    "battery_pack_capacity_kwh": 124,
    "battery_pack_depth_of_discharge_pct": 80,
    "hydrogen_gas_tank_volume_m3": 159.0,
    "hydrogen_gas_tank_capacity_kg": 1.8,
}


def _verify_reference_values(reference_values):
    keys = [
        "fuel_cell_volume_m3",
        "fuel_cell_weight_kg",
        "fuel_cell_power_kw",
        "fuel_cell_efficiency_pct",
        "battery_pack_volume_m3",
        "battery_pack_weight_kg",
        "battery_pack_capacity_kwh",
        "battery_pack_depth_of_discharge_pct",
        "hydrogen_gas_tank_volume_m3",
        "hydrogen_gas_tank_capacity_kg",
    ]
    if not all([key in reference_values for key in keys]):
        raise Exception("Missing reference values.")


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


def estimate_internal_combustion_system(
    vessel_data, voyage_profile, include_auxiliary=True
):
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

    # Fuel
    fc_kg, _ = estimate_fuel_consumption_of_propulsion_engines(
        vessel_data,
        voyage_profile,
        limit_7_percent=False,
        delta_w=0.8,
    )

    fc_m3 = calculate_fuel_volume(fc_kg, vessel_data["propulsion_engine_fuel_type"])

    # Totals
    total_weight = prop_engines["weight"] + gearboxes_weight + fc_kg
    total_volume = prop_engines["volume"] + gearboxes_volume + fc_m3

    return {
        "total_weight_kg": total_weight,
        "total_volume_m3": total_volume,
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
            "fuel": {"weight_kg": fc_kg, "volume_m3": fc_m3},
        },
    }


def estimate_vessel_battery_system(
    required_energy_kwh,
    required_power_kw,
    number_of_propulsion_engines,
    double_ended,
    battery_packs_volumetric_energy_density_kwhpm3,
    battery_packs_gravimetric_energy_density_kwhpkg,
    battery_depth_of_discharge_pct,
    electrical_engine_volumetric_power_density_kwpm3,
    electrical_engine_gravimetric_power_density_kwpkg,
    **kwargs,
):
    """Estimate the key details of a battery propulsion system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float

        battery_packs_volumetric_energy_density_kwhpm3: float

        battery_packs_gravimetric_energy_density_kwhpkg: float

        battery_depth_of_discharge_pct: float

        electrical_engine_volumetric_power_density_kwpm3: float

        electrical_engine_gravimetric_power_density_kwpkg: float

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
        battery_depth_of_discharge_pct / 100
    )
    battery_packs_weight_kg = (
        battery_packs_capacity_kwh * battery_packs_gravimetric_energy_density_kwhpkg
    )
    battery_packs_volume_m3 = (
        battery_packs_capacity_kwh * battery_packs_volumetric_energy_density_kwhpm3
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
        electrical_engine_power_kw / electrical_engine_gravimetric_power_density_kwpkg
    )
    electrical_engine_volume_m3 = (
        electrical_engine_power_kw / electrical_engine_volumetric_power_density_kwpm3
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
                "weight_pct_engine_kg": electrical_engine_weight_kg,
                "volume_pct_engine_m3": electrical_engine_volume_m3,
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
    fuel_cell_system_volumetric_power_density_kwpm3,
    fuel_cell_system_gravimetric_power_density_kwpkg,
    electrical_engine_volumetric_power_density_kwpm3,
    electrical_engine_gravimetric_power_density_kwpkg,
    fuel_cell_efficiency_pct,
    hydrogen_gravimetric_energy_density_kwhpkg,
    hydrogen_gas_tank_container_weight_to_content_weight_ratio_kgpkg,
    hydrogen_gas_tank_container_volume_to_content_weight_ratio_lpkg,
    **kwargs,
):
    """Estimate the weight and volume of a gas hydrogen system

    Arguments:
    ----------

        required_energy_kwh: float

        required_power_kw: float

        fuel_cell_system_volumetric_power_density_kwpm3: float

        fuel_cell_system_gravimetric_power_density_kwpkg: float

        electrical_engine_volumetric_power_density_kwpm3: float

        electrical_engine_gravimetric_power_density_kwpkg: float

        fuel_cell_efficiency_pct: float

        hydrogen_gravimetric_energy_density_kwhpkg: float

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
        required_energy_kwh / (fuel_cell_efficiency_pct / 100)
    ) / hydrogen_gravimetric_energy_density_kwhpkg

    # Fuel cell system
    fuel_cell_system_weight = (
        required_power_kw / fuel_cell_system_gravimetric_power_density_kwpkg
    )
    fuel_cell_system_volume = (
        required_power_kw / fuel_cell_system_volumetric_power_density_kwpm3
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
        electrical_engine_power_kw / electrical_engine_gravimetric_power_density_kwpkg
    )
    electrical_engine_volume_m3 = (
        electrical_engine_power_kw / electrical_engine_volumetric_power_density_kwpm3
    )

    hydrogen_gas_tank_weight = (
        hydrogen_weight_kg
        * hydrogen_gas_tank_container_weight_to_content_weight_ratio_kgpkg
    )
    volume_gas_tank = (
        hydrogen_weight_kg
        * hydrogen_gas_tank_container_volume_to_content_weight_ratio_lpkg
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
                "weight_pct_engine_kg": electrical_engine_weight_kg,
                "volume_pct_engine_m3": electrical_engine_volume_m3,
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
    # verify_vessel_data(vessel_data)
    # verify_voyage_profile(voyage_profile)
    _verify_
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
    average_fuel_consumption_lpnm,
    propulsion_engine_fuel_type,
    number_of_propulsion_engines,
    propulsion_engine_power_kw,
    double_ended,
    total_voyage_length_nm,
    reference_values,
):
    """Suggest alternative energy systems SIMPLE

    Arguements:
    -----------

        vessel_data_simple: dict
            {
                "average_fuel_consumption_lpnm": 10.0
                "propulsion_engine_fuel_type": "MDO",
                "number_of_propulsion_engines": 4,
                "propulsion_engine_power_kw": 330,
                "double_ended": False
            }
    """

    total_fc_l = average_fuel_consumption_lpnm * total_voyage_length_nm

    fuel_type = propulsion_engine_fuel_type
    required_energy_kwh = FUEL_ENERGY_DENSITY_KWHPL[fuel_type] * total_fc_l

    required_power_kw = propulsion_engine_power_kw + number_of_propulsion_engines
    if double_ended:
        required_power_kw /= 2

    battery = estimate_vessel_battery_system(
        required_energy_kwh,
        required_power_kw,
        number_of_propulsion_engines,
        double_ended,
        **reference_values,
    )
    gas = estimate_vessel_gas_hydrogen_system(
        required_energy_kwh,
        required_power_kw,
        number_of_propulsion_engines,
        double_ended,
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
