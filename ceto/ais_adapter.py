"""
Functions for estimating input to ceto using AIS data
"""
import math
import warnings
from typing import Tuple
from datetime import datetime

import numpy as np

from ceto.utils import ms_to_knots


def _map_to_imo_ship_type(
    type_of_ship_and_cargo_type: int,
) -> str:
    """Map 'type of ship and cargo type' from an AIS message 5 to map to a IMO ship type according to:
    10-19   -> unknown?         -> service-other
    20-29   -> WIG or SAR       -> service-other
    30                          -> miscellaneous-fishing
    31-32                       -> service-tug
    33-35   -> Military         -> service-other
    36-39                       -> yacht
    40-49   -> High-speed       -> ferry-pax
    50-59                       -> service-other
    60-69   -> passenger        -> ferry-ropax
    70-79                       -> general_cargo
    80-83                       -> oil_tanker
    84                          -> liquified_gas_tanker
    90-99                       -> service-other
    unknown                     -> service-other

    Sources:
     - https://help.marinetraffic.com/hc/en-us/articles/205579997-What-is-the-significance-of-the-AIS-Shiptype-number-

    Args:
        type_of_ship_and_cargo_type (int): According to AIS message 5 standard

    Returns:
        str: A IMO ship type (see README.md)
    """
    if type_of_ship_and_cargo_type in range(10, 20):
        return "service-other"
    elif type_of_ship_and_cargo_type in range(20, 30):
        return "service-other"
    elif type_of_ship_and_cargo_type == 30:
        return "miscellaneous-fishing"
    elif type_of_ship_and_cargo_type in range(31, 33):
        return "service-tug"
    elif type_of_ship_and_cargo_type in range(33, 36):
        return "service-other"
    elif type_of_ship_and_cargo_type in range(36, 40):
        return "yacht"
    elif type_of_ship_and_cargo_type in range(40, 50):
        return "ferry-pax"
    elif type_of_ship_and_cargo_type in range(50, 60):
        return "service-other"
    elif type_of_ship_and_cargo_type in range(60, 70):
        return "ferry-ropax"
    elif type_of_ship_and_cargo_type in range(70, 80):
        return "general_cargo"
    elif type_of_ship_and_cargo_type in range(80, 84):
        return "oil_tanker"
    elif type_of_ship_and_cargo_type == 84:
        return "liquified_gas_tanker"
    elif type_of_ship_and_cargo_type in range(85, 90):
        return "oil_tanker"
    elif type_of_ship_and_cargo_type in range(90, 100):
        return "service-other"

    # else
    warnings.warn(
        f"Type of ship and cargo type: {type_of_ship_and_cargo_type} cannot be"
        " mapped to a IMO ship type, will be treated as 'service-other'"
    )
    return "service-other"


def _validate_dimensions(
    dim_a: float, dim_b: float, dim_c: float, dim_d: float
) -> bool:
    length = dim_a + dim_b
    beam = dim_c + dim_d

    if not (5 <= length <= 450):
        return False

    if not (1.5 <= beam <= 70):
        return False

    if not (2 <= length / beam <= 8):
        return False

    return True


def _guesstimate_block_coefficient(imo_ship_type: str) -> float:
    """Guesstimate the block coefficient based on imo_ship_type

    Based on a mix of tabulated values from Basic Principles of Ship Propulsion (MAN)

    Sources:
     - Basic Principles of Ship Propulsion, MAN.
       https://www.man-es.com/docs/default-source/marine/tools/basic-principles-of-ship-propulsion_web_links.pdf?sfvrsn=12d1b862_10
     - Engineering estimates

    Args:
        imo_ship_type (str): The IMO ship type

    Raises:
        ValueError: If an invalid imo_ship_type was provided as input

    Returns:
        float: The estimated block coefficient [-]
    """
    if imo_ship_type == "oil_tanker":
        return 0.8
    elif imo_ship_type == "general_cargo":
        return 0.75
    elif imo_ship_type in ("ferry-ropax", "ferry-pax"):
        return 0.60
    elif imo_ship_type == "yacht":
        return 0.5
    elif imo_ship_type.startswith("service"):
        return 0.65
    elif imo_ship_type == "miscellaneous-fishing":
        return 0.45

    # else
    raise ValueError(
        f"The ship type '{imo_ship_type}' is currently not supported by this function."
    )


def _guesstimate_design_draft(ais_draft: float, beam: float) -> float:
    """Guesstimate the design draft

    If the ais draft falls within the expected T/B ratio, use it directly,
    otherwise estimate the design draft as B/3.25

    Args:
        ais_draft (float): Draft from ais message 5 [m]
        beam (float): Beam [m]

    Returns:
        float: Estimated design draft [m]
    """
    return (
        ais_draft
        if ais_draft > 0.0 and (2.25 <= beam / ais_draft <= 3.75)
        else beam / 3.25
    )


def _guesstimate_design_speed(length: float, imo_ship_type: str, speed: float) -> float:
    """Guesstimate the design speed

    Assuming the there is a linear correlation between block coefficient
    and design Froude number. If the inputted actual speed is higher than
    the estimated design speed, it is used directly.

    Sources:
     - Slide 5 of http://www.mar.ist.utl.pt/mventura/Projecto-Navios-I/EN/SD-1.3.1-Estimation%20Methods.pdf

    Args:
        length (float): Length of vessel [m]
        imo_ship_type (str): The IMO ship type
        speed (float): Speed of vessel [kn]

    Returns:
        float: Estimated design speed [kn]
    """
    g = 9.81
    block_coefficient = _guesstimate_block_coefficient(imo_ship_type)

    blocks = [0.45, 0.8]
    froude_numbers = [0.32, 0.145]

    froude_number = np.interp(block_coefficient, blocks, froude_numbers)

    design_speed = ms_to_knots(
        (froude_number * math.sqrt(g * length)) / block_coefficient
    )
    return speed if 0.5 * design_speed <= speed <= 1.5 * design_speed else design_speed


def _guesstimate_number_of_engines(imo_ship_type: str) -> int:
    """Guesstimate number of engines

    Self-explanatory and very simplistic approach...

    Args:
        imo_ship_type (str): The IMO ship type

    Returns:
        int: The estimated number of engines
    """
    return 2 if imo_ship_type in ("ferry-pax", "ferry-ropax") else 1


def _guesstimate_engine_MCR(
    imo_ship_type: str, dwt: float, design_speed: float
) -> float:
    """Guesstimate the engine MCR based on deadweight and design speed

    Sources:
     - Cepowski, Tomasz. (2019). Regression Formulas for The Estimation of
       Engine Total Power for Tankers, Container Ships and Bulk Carriers on
       The Basis of Cargo Capacity and Design Speed. Polish Maritime Research.
       26. 82-94. 10.2478/pomr-2019-0010.

    Args:
        imo_ship_type (str): The IMO ship type
        dwt (float): Deadweight tonnage [t]
        design_speed (float): Design speed [kn]

    Returns:
        float: Estimated engine MCR [kW]
    """
    # Very crude model to differentiate between some (...) ship types
    if "tanker" in imo_ship_type:
        # Coefficients for "All tanker types"
        coefficients = (2.66, 0.6, 0.6)
    else:
        # Coefficients for "All Bulk carrier types"
        coefficients = (4.297, 0.6, 0.4)

    def _regression(alpha: float, beta: float, gamma: float) -> float:
        return alpha * dwt**beta * design_speed**gamma

    return _regression(*coefficients)


def _guesstimate_engine_type(imo_ship_type: str) -> str:
    """Guesstimate engine type

    Crude differentiation based on assumptions,

    Args:
        imo_ship_type (str): The IMO ship type

    Returns:
        str: The estimated engine type
    """
    if imo_ship_type == "liquified_gas_tanker":
        return "LNG-Otto-MS"

    elif imo_ship_type in ("oil_tanker", "general_cargo"):
        return "SSD"

    elif imo_ship_type in ("ferry-pax", "ferry-ropax"):
        return "MSD"

    # else
    return "HSD"


def _guesstimate_engine_fuel_type(
    imo_ship_type: str, latitude: float, longitude: float
) -> str:
    """Guesstimate engine fuel type

    Self-explanatory and very simplistic...

    Args:
        imo_ship_type (str): The IMO ship type
        latitude (float): Latitude (deg)
        longitude (float): Longitude (deg)

    Returns:
        str: The estimated engine fuel type
    """
    if imo_ship_type == "liquified_gas_tanker":
        return "LNG"

    # else the coice of HFO vs MDO depends primarily on ECA areas
    # the whole Baltic Sea is an ECA area and thus HFO should not be used
    # TODO: Use latitude and longitude to match against ECA areas
    return "MDO"


def _guesstimate_vessel_size_as_deadweight_tonnage(
    imo_ship_type: str,
    length: float,
    beam: float,
    draft: float,
) -> float:
    """Guesstimate the Deadweight Tonnage

    Sources:
     - Barras, C.B. (2004), “Ship Design and Performance for Masters and
       Mates”, Elsevier Butterworth-Heinemann.

    Args:
        imo_ship_type (str): The IMO ship type
        length (float): Length of vessel [m]
        beam (float): Beam of vessel [m]
        draft (float): Design draft of vessel [m]

    Returns:
        float: Estimated Deadweight Tonnage [t]
    """

    block_coefficient = _guesstimate_block_coefficient(imo_ship_type)
    displacement = block_coefficient * length * beam * draft

    if imo_ship_type == "oil_tanker":
        return displacement * 0.83

    elif imo_ship_type == "liquified_gas_tanker":
        return displacement * 0.62

    elif imo_ship_type in ("ferry-pax", "ferry-ropax"):
        return displacement * 0.35

    # else

    return displacement * 0.7


def _guesstimate_vessel_size_as_gross_tonnage(imo_ship_type: str, dwt: float) -> float:
    """Guesstimate vessel size as Gross Tonnage

    Sources:
     - Table 5.1 in http://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn0309pdf/ks0309010.pdf

    Args:
        imo_ship_type (str): The IMO ship type
        dwt (float): Deadweight tonnage [t]

    Returns:
        float: Estimated Gross Tonnage [m3]
    """
    if imo_ship_type == "general_cargo":
        return 0.5285 * dwt
    if imo_ship_type == "oil_tanker":
        return 0.5354 * dwt
    if imo_ship_type == "liquified_gas_tanker":
        return 1.3702 * dwt
    if imo_ship_type == "ferry-ropax":
        return 1.7803 * dwt
    if imo_ship_type == "ferry-pax":
        return 8.9393 * dwt

    # else, we assume the vessel is not a cargo-carrying vessel
    return 2.0 * dwt


def _guesstimate_vessel_size_as_cubic_metres(imo_ship_type: str, dwt: float) -> float:
    """Guesstimate the vessel size as CBM (Cubic Metres)

    Sources:
     - None, fallback to 0.8 * Gross Tonnage

    Args:
        imo_ship_type (str): The IMO ship type
        dwt (float): Deadweight tonnage [t]

    Returns:
        float: Estimated size in CBM [m3]
    """
    return 0.8 * _guesstimate_vessel_size_as_gross_tonnage(imo_ship_type, dwt)


def guesstimate_vessel_data(
    type_of_ship_and_cargo_type: int,
    dim_a: float,
    dim_b: float,
    dim_c: float,
    dim_d: float,
    speed: float,
    draft: float,
    latitude: float,
    longitude: float,
) -> dict:
    """Guesstimate vessel_data input to ceto using parameters readily avilable in AIS data

    Args:
        type_of_ship_and_cargo_type (int): Type of ship and cargo
        dim_a (float): Dim a [m]
        dim_b (float): Dim b [m]
        dim_c (float): Dim c [m]
        dim_d (float): Dim d [m]
        speed (float): Current speed [kn]
        draft (float): Current draft [kn]
        latitude (float): Current position (latitude) [deg]
        longitude (float): Current position (longitude) [deg]

    Raises:
        ValueError: If validation of inputted parameters fail,
        which they do if they are not deemed resonable for further guesstimations.

    Returns:
        dict: Vessel data
    """
    # Validation
    if not _validate_dimensions(dim_a, dim_b, dim_c, dim_d):
        raise ValueError(
            "Dims (dim_a, dim_b, dim_c, dim_d) are not deemed reasonable. No estimations can be made."
        )

    # Ship type
    imo_ship_type = _map_to_imo_ship_type(type_of_ship_and_cargo_type)

    # Main dimensions
    length, beam = dim_a + dim_b, dim_c + dim_d
    design_draft = _guesstimate_design_draft(draft, beam)
    design_speed = _guesstimate_design_speed(length, imo_ship_type, speed)

    # Vessel size (DWT)
    vessel_size = _guesstimate_vessel_size_as_deadweight_tonnage(
        imo_ship_type, length, beam, design_draft
    )

    # Engine parameters
    number_of_engines = _guesstimate_number_of_engines(imo_ship_type)
    engine_power = _guesstimate_engine_MCR(imo_ship_type, vessel_size, design_speed)
    engine_type = _guesstimate_engine_type(imo_ship_type)
    engine_fuel_type = _guesstimate_engine_fuel_type(imo_ship_type, latitude, longitude)

    # Vessel size as GT
    if imo_ship_type in (
        "ferry-pax",
        "ferry-ropax",
        "cruise",
        "yacht",
        "miscellaneous-fishing",
        "service-tug",
        "offshore",
        "service-other",
        "miscellaneous-other",
    ):
        vessel_size = _guesstimate_vessel_size_as_gross_tonnage(
            imo_ship_type, vessel_size
        )
    elif imo_ship_type == "liquified_gas_tanker":
        vessel_size = _guesstimate_vessel_size_as_cubic_metres(
            imo_ship_type, vessel_size
        )

    # Assemble output dictionary
    vessel_data = {
        # Fixed values that will not be inferred from AIS data but are reasonable static assumptions
        **{
            "double_ended": False,
            "propulsion_engine_age": "after_2000",
        },
        # Guesstimated values
        **{
            "type": imo_ship_type,
            "length": length,
            "beam": beam,
            "size": vessel_size,
            "design_draft": design_draft,
            "design_speed": design_speed,
            "number_of_propulsion_engines": number_of_engines,
            "propulsion_engine_power": engine_power,
            "propulsion_engine_type": engine_type,
            "propulsion_engine_fuel_type": engine_fuel_type,
        },
    }

    return vessel_data


EARTH_RADIUS = 6367.0 * 1000.0


def _rhumbline(
    latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float
) -> Tuple[float, float]:
    """Rhumbline distance from (latitude_1, longitude_1) -> (latitude_2, longitude_2)

    See section about "Rhumb lines" on http://www.movable-type.co.uk/scripts/latlong.html

    Args:
        latitude_1 (float): [deg]
        longitude_1 (float): [deg]
        latitude_2 (float): [deg]
        longitude_2 (float): [deg]

    Returns:
        Tuple[float, float]: (Bearing [deg], Rhumbline distance [m])
    """

    _lat1 = math.radians(latitude_1)
    _lat2 = math.radians(latitude_2)
    dlon = math.radians(longitude_2 - longitude_1)
    dlat = math.radians(latitude_2 - latitude_1)

    dPhi = math.log(
        math.tan((_lat2 / 2) + (math.pi / 4)) / math.tan((_lat1 / 2) + (math.pi / 4))
    )
    q = dlat / dPhi if dPhi else math.cos(_lat1)  # E-W line gives dPhi = 0

    # if dLon over 180deg take shorter rhumb across anti-meridian:
    if abs(dlon) > math.pi:
        dlon = -(2 * math.pi - dlon) if dlon > 0 else (2 * math.pi + dlon)

    bb = math.atan2(dlon, dPhi)
    if bb < 0:
        bb = 2 * math.pi + bb

    brng = bb
    dist = math.sqrt(dlat * dlat + q * q * dlon * dlon) * EARTH_RADIUS

    return math.degrees(brng), dist


def guesstimate_voyage_data(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
    draft_1: float,
    draft_2: float,
    speed_1: float,
    speed_2: float,
    time_1: datetime,
    time_2: datetime,
    design_speed: float,
    design_draft: float,
) -> dict:
    """Guesstimate voyage data input to ceto from parameters readily available in AIS messages

    Args:
        latitude_1 (float): Latitude at WP1 [deg]
        longitude_1 (float): Longtude at WP1 [deg]
        latitude_2 (float): Latitude at WP2 [deg]
        longitude_2 (float): Longitude at WP2 [deg]
        draft_1 (float): Draft at WP1 [m]
        draft_2 (float): Draft at WP2 [m]
        speed_1 (float): Speed at WP1 [kn]
        speed_2 (float): Speed at WP2 [kn]
        time_1 (datetime): Time at WP1 [h]
        time_2 (datetime): Time at WP2 [h]
        design_speed (float): Design speed of vessel [kn]
        design_draft (float): Design draft of vessel [m]

    Returns:
        dict: _description_
    """
    _, distance = _rhumbline(latitude_1, longitude_1, latitude_2, longitude_2)
    distance /= 1852  # To nautical miles (nm)

    delta_time = (time_2 - time_1).total_seconds() / 3600  # hours

    if delta_time == 0.0:
        raise ValueError(f"Timestamps ({time_1}, {time_2}) cant be equal!")

    # Figure out a reasonable speed to use for this leg
    avg_speed = 0.5 * (speed_1 + speed_2)  # knots (nm/h)
    if avg_speed > 0.0 and not (0.75 <= (distance / delta_time) / avg_speed <= 1.25):
        avg_speed = distance / delta_time

    # Figure out a reasonable draft to use for this leg
    avg_draft = 0.5 * (draft_1 + draft_2)
    avg_draft = (
        avg_draft
        if 0.25 * design_draft <= avg_draft <= 1.5 * design_draft
        else design_draft
    )

    default_output = {
        "time_anchored": 0.0,
        "time_at_berth": 0.0,
        "legs_manoeuvring": [],
        "legs_at_sea": [],
    }

    # Less than 3 knots -> at anchor or in port
    if avg_speed < 3.0:
        return {**default_output, **{"time_anchored": delta_time}}

    # Between 3 knots and half the design speed -> manoeuvring
    elif 3.0 <= avg_speed <= design_speed / 2:
        return {
            **default_output,
            **{"legs_manoeuvring": [(distance, avg_speed, avg_draft)]},
        }

    # else we are at sea
    return {
        **default_output,
        **{"legs_at_sea": [(distance, avg_speed, avg_draft)]},
    }
