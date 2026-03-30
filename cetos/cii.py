"""
Carbon Intensity Indicator (CII) calculation per IMO MARPOL Annex VI.

Calculates the attained CII for a vessel voyage, the required CII for the
vessel type, size, and year, and assigns a rating from A (best) to E (worst).

References:
    [1] IMO MEPC.339(76) — CII reference line parameters.
    [2] IMO MEPC.338(76) — Annual CII reduction factors.
    [3] IMO MEPC.354(78) — CII rating boundaries (dd vectors).
"""

import math

from cetos.emissions import CO2_FACTORS
from cetos.imo import estimate_fuel_consumption
from cetos.models import VesselData, VoyageProfile

# CII reference line parameters: CII_ref = a × capacity^(-c)
# Source: IMO MEPC.339(76), Table 1
CII_PARAMS = {
    "bulk_carrier": (4745, 0.622),
    "gas_carrier": (144050000, 2.071),
    "tanker": (5247, 0.610),
    "container": (1984, 0.489),
    "general_cargo": (31948, 0.792),
    "refrigerated_cargo": (4600, 0.557),
    "combination_carrier": (5119, 0.622),
    "lng_carrier": (9.827, 0.000),
    "vehicle_carrier": (5686, 0.714),
    "roro_cargo": (10952, 0.637),
    "roro_passenger": (7540, 0.587),
    "cruise_passenger": (930, 0.383),
}

# Annual reduction factors Z (%)
# Source: IMO MEPC.338(76)
REDUCTION_FACTORS = {
    2019: 0,
    2020: 1,
    2021: 2,
    2022: 3,
    2023: 5,
    2024: 7,
    2025: 9,
    2026: 11,
}

# Rating boundary vectors (d1, d2, d3, d4)
# Source: IMO MEPC.354(78)
# A: CII ≤ req × exp(d1), B: ≤ exp(d2), C: ≤ exp(d3), D: ≤ exp(d4), E: > exp(d4)
CII_RATING_BOUNDARIES = {
    "bulk_carrier": (-0.86, -0.69, -0.32, 0.00),
    "gas_carrier": (-0.78, -0.57, -0.28, 0.00),
    "tanker": (-0.85, -0.69, -0.32, 0.00),
    "container": (-0.84, -0.56, -0.27, 0.00),
    "general_cargo": (-0.80, -0.56, -0.27, 0.00),
    "refrigerated_cargo": (-0.78, -0.57, -0.20, 0.00),
    "combination_carrier": (-0.86, -0.69, -0.32, 0.00),
    "lng_carrier": (-0.78, -0.57, -0.28, 0.00),
    "vehicle_carrier": (-0.86, -0.69, -0.32, 0.00),
    "roro_cargo": (-0.78, -0.57, -0.28, 0.00),
    "roro_passenger": (-0.78, -0.57, -0.28, 0.00),
    "cruise_passenger": (-0.78, -0.57, -0.28, 0.00),
}

# Mapping from CETOS vessel types to CII categories
_CETOS_TO_CII = {
    "bulk_carrier": "bulk_carrier",
    "chemical_tanker": "tanker",
    "oil_tanker": "tanker",
    "other_liquids_tanker": "tanker",
    "container": "container",
    "general_cargo": "general_cargo",
    "refrigerated_cargo": "refrigerated_cargo",
    "liquified_gas_tanker": "gas_carrier",
    "roro": "roro_cargo",
    "vehicle": "vehicle_carrier",
    "ferry-ropax": "roro_passenger",
    "ferry-pax": "roro_passenger",
    "cruise": "cruise_passenger",
}

# Vessel types that use GT instead of DWT for capacity
_GT_CAPACITY_TYPES = {"roro_passenger", "cruise_passenger"}


def _get_cii_type(cetos_vessel_type):
    """Map CETOS vessel type to CII category."""
    if cetos_vessel_type not in _CETOS_TO_CII:
        raise ValueError(
            f"Vessel type '{cetos_vessel_type}' is not covered by CII regulations. "
            f"CII applies to: {list(_CETOS_TO_CII.keys())}"
        )
    return _CETOS_TO_CII[cetos_vessel_type]


def calculate_required_cii(cii_type, capacity, year):
    """Calculate the required CII for a vessel type, capacity, and year.

    Arguments:
    ----------

        cii_type: string
            CII vessel category (e.g., 'tanker', 'bulk_carrier').

        capacity: float
            DWT or GT depending on vessel type.

        year: int
            Calendar year for CII calculation.

    Returns:
    --------

        float
            Required CII (gCO2 / capacity·nm).
    """
    a, c = CII_PARAMS[cii_type]
    cii_ref = a * (capacity ** (-c))

    # Get reduction factor, default to latest if year not in table
    z = REDUCTION_FACTORS.get(year, REDUCTION_FACTORS[max(REDUCTION_FACTORS.keys())])

    return cii_ref * (1 - z / 100)


def calculate_attained_cii(co2_emissions_kg, capacity, distance_nm):
    """Calculate the attained CII from emissions, capacity, and distance.

    Arguments:
    ----------

        co2_emissions_kg: float
            Total CO2 emissions (kg).

        capacity: float
            DWT or GT.

        distance_nm: float
            Total distance sailed (nautical miles).

    Returns:
    --------

        float
            Attained CII (gCO2 / capacity·nm).
    """
    if distance_nm <= 0:
        raise ValueError("distance_nm must be positive")
    if capacity <= 0:
        raise ValueError("capacity must be positive")

    co2_grams = co2_emissions_kg * 1000.0
    return co2_grams / (capacity * distance_nm)


def calculate_cii_rating(attained_cii, required_cii, cii_type):
    """Calculate the CII rating (A-E) from attained and required CII.

    Arguments:
    ----------

        attained_cii: float
            Attained CII value.

        required_cii: float
            Required CII for the year.

        cii_type: string
            CII vessel category.

    Returns:
    --------

        string
            Rating: 'A', 'B', 'C', 'D', or 'E'.
    """
    d1, d2, d3, d4 = CII_RATING_BOUNDARIES[cii_type]

    if attained_cii <= required_cii * math.exp(d1):
        return "A"
    elif attained_cii <= required_cii * math.exp(d2):
        return "B"
    elif attained_cii <= required_cii * math.exp(d3):
        return "C"
    elif attained_cii <= required_cii * math.exp(d4):
        return "D"
    else:
        return "E"


def estimate_cii(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    year=2024,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate the CII rating for a vessel voyage.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile.

        year (optional): int
            Calendar year for CII calculation. Defaults to 2024.

        include_steam_boilers (optional): boolean
            Defaults to True.

        limit_7_percent (optional): boolean
            Defaults to True.

        delta_w (optional): float
            Speed-power correction factor. Defaults to None.

    Returns:
    --------

        Dict
            CII rating (A-E), attained and required CII values,
            CO2 emissions, distance, and capacity used.
    """
    cii_type = _get_cii_type(vessel_data.type)

    # Determine capacity (DWT or GT)
    if cii_type in _GT_CAPACITY_TYPES:
        capacity = vessel_data.size  # GT
    else:
        capacity = vessel_data.size  # DWT

    if capacity is None or capacity <= 0:
        raise ValueError(
            "Vessel size (DWT/GT) must be set for CII calculation."
        )

    # Calculate fuel consumption
    fc = estimate_fuel_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    # CO2 emissions
    fuel_type = vessel_data.propulsion_engine_fuel_type
    co2_kg = fc["total_kg"] * CO2_FACTORS[fuel_type]

    # Total distance (all legs)
    total_distance = sum(
        leg.distance_nm for leg in voyage_profile.legs_at_sea
    ) + sum(
        leg.distance_nm for leg in voyage_profile.legs_manoeuvring
    )

    if total_distance <= 0:
        raise ValueError("Voyage must have positive sailing distance for CII.")

    # Calculate CII
    attained = calculate_attained_cii(co2_kg, capacity, total_distance)
    required = calculate_required_cii(cii_type, capacity, year)
    rating = calculate_cii_rating(attained, required, cii_type)

    return {
        "rating": rating,
        "attained_cii": attained,
        "required_cii": required,
        "total_co2_kg": co2_kg,
        "total_fuel_kg": fc["total_kg"],
        "total_distance_nm": total_distance,
        "capacity": capacity,
        "cii_type": cii_type,
        "year": year,
    }
