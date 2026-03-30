"""
Estimates of CO2 emissions from vessel fuel consumption.

Emission factors are based on IMO MEPC.308(73) — 2024 Guidelines on the method
of calculation of the attained Energy Efficiency Existing Ship Index (EEXI).
These are stoichiometric conversion factors (mass of CO2 produced per mass of
fuel burned) and do not change over time.
"""

from cetos.imo import estimate_fuel_consumption
from cetos.models import FUEL_TYPES, VesselData, VoyageProfile
from cetos.utils import verify_set

# CO2 emission factors (kg CO2 per kg fuel)
# Source: IMO MEPC.308(73), Table 1
CO2_FACTORS = {
    "HFO": 3.114,  # Heavy Fuel Oil
    "MDO": 3.206,  # Marine Diesel Oil
    "LNG": 2.750,  # Liquefied Natural Gas
    "MeOH": 1.375,  # Methanol
}


def estimate_co2_emissions_from_fuel_consumption(fuel_mass_kg, fuel_type):
    """Estimate CO2 emissions from a given mass of fuel.

    Arguments:
    ----------

        fuel_mass_kg: float
            Mass of fuel consumed (kg).

        fuel_type: string
            Type of fuel. Possible values: HFO, MDO, LNG, MeOH.

    Returns:
    --------

        float
            Mass of CO2 produced (kg).

    Source:
        IMO MEPC.308(73), Table 1.
    """
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    return fuel_mass_kg * CO2_FACTORS[fuel_type]


def estimate_co2_emissions(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate CO2 emissions for a vessel voyage.

    Calculates fuel consumption using the IMO Fourth GHG Study methodology,
    then applies the CO2 conversion factor for the vessel's fuel type.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile.

        include_steam_boilers (optional): boolean
            If True, the fuel consumption of the steam boilers is included.
            Defaults to True.

        limit_7_percent (optional): boolean
            If True, when the engine load is less than 7% the fuel consumption
            is neglected. Defaults to True.

        delta_w (optional): float
            Speed-power correction factor. See estimate_fuel_consumption for
            details. Defaults to None.

    Returns:
    --------

        Dict
            Total CO2 emissions (kg) and breakdown by operation mode, along
            with the underlying fuel consumption.

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.
        [2] IMO MEPC.308(73), Table 1 — CO2 emission factors.
    """
    fuel_type = vessel_data.propulsion_engine_fuel_type
    co2_factor = CO2_FACTORS[fuel_type]

    fc = estimate_fuel_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    result = {
        "total_kg_co2": fc["total_kg"] * co2_factor,
        "total_fuel_kg": fc["total_kg"],
        "fuel_type": fuel_type,
        "co2_factor": co2_factor,
    }

    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        result[mode] = {
            "co2_kg": fc[mode]["subtotal_kg"] * co2_factor,
            "fuel_kg": fc[mode]["subtotal_kg"],
        }

    return result
