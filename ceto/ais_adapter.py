"""
Functions for estimating input to ceto using AIS data
"""
import math
import warnings
from typing import Tuple

from ceto.utils import ms_to_knots


def _map_type_of_ship_and_cargo_type_to_ceto_ship_type(
    type_of_ship_and_cargo_type: int,
) -> str:
    """Map 'type of ship and cargo type' from an AIS message 5 to map to a ceto shiptype according to:
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

    Args:
        type_of_ship_and_cargo_type (int): According to AIS message 5 standard

    Returns:
        str: A ceto ship type (see README.md)
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
        "Type of ship and cargo type: %d cannot be mapped to a CETO ship type, will be treated as 'service-other'",
        type_of_ship_and_cargo_type,
    )
    return "service-other"


def _validate_dims(dim_a: float, dim_b: float, dim_c: float, dim_d: float) -> bool:
    length = dim_a + dim_b
    beam = dim_c + dim_d

    if not (5 <= length <= 500):
        return False

    if not (1 <= beam <= 70):
        return False

    if not (2 <= length / beam <= 8):
        return False

    return True


def _guesstimate_block_coefficient(ceto_ship_type: str) -> float:
    if ceto_ship_type == "oil_tanker":
        return 0.85
    elif ceto_ship_type in ("general_cargo", "ferry-ropax"):
        return 0.75
    elif ceto_ship_type == "ferry-pax":
        return 0.55
    elif ceto_ship_type == "yacht":
        return 0.6
    elif ceto_ship_type.startswith("service"):
        return 0.65
    elif ceto_ship_type == "miscellaneous-fishing":
        return 0.45


def _guesstimate_design_draft(ais_draft: float, beam: float) -> float:
    return ais_draft if 2.25 <= ais_draft / beam <= 3.75 else beam / 3


def _guesstimate_design_speed(
    length: float, ceto_ship_type: str, speed: float
) -> float:
    g = 9.81
    block_coefficient = _guesstimate_block_coefficient(ceto_ship_type)
    design_speed = ms_to_knots((0.145 * math.sqrt(g * length)) / block_coefficient)
    return speed if speed > design_speed else design_speed


def _guesstimate_number_of_engines(ceto_ship_type: str) -> int:
    """Returns the guesstimated number of engines

    Args:
        ceto_ship_type (str): The ceto ship type

    Returns:
        int: The estimated number of engines
    """
    if ceto_ship_type in ("ferry-pax", "ferry-ropax"):
        return 2

    # else
    return 1


oil_tanker_sizes = [1985, 6777, 15129, 43763, 72901, 109259, 162348, 313396]
oil_tanker_power = [1274, 2846, 4631, 8625, 12102, 13831, 18796, 27685]

ferry_pax_sizes = [135, 1681]
ferry_pax_power = [1885, 6594]

ferry_ropax_sizes = [401, 3221]
ferry_ropax_power = [1508, 15491]

miscellaneous_fishing_power = 956
service_other_power = 3177


def _guesstimate_overall_engine_power(
    length: float, beam: float, draft: float, block_coefficient: float
) -> float:
    tanker_si
    pass


def _guesstimate_engine_type(ceto_ship_type: str) -> str:
    """Returns guesstimated engine type

    Args:
        ceto_ship_type (str): The ceto ship type

    Returns:
        str: The estimated engine type
    """
    if ceto_ship_type == "liquified_gas_tanker":
        return "LNG-Otto-MS"

    elif ceto_ship_type in ("oil_tanker", "general_cargo"):
        return "SSD"

    elif ceto_ship_type in ("ferry-pax", "ferry-ropax"):
        return "MSD"

    # else
    return "HSD"


def _guesstimate_engine_fuel_type(
    ceto_ship_type: str, latitude: float, longitude: float
) -> str:
    """Returns guesstimated engine fuel typ

    Args:
        ceto_ship_type (str): The ceto ship type
        latitude (float): Latitude (deg)
        longitude (float): Longitude (deg)

    Returns:
        str: The estimated engine fuel type
    """
    if ceto_ship_type == "liquified_gas_tanker":
        return "LNG"

    # else the coice of HFO vs MDO depends primarily on ECA areas
    # the whole Baltic Sea is an ECA area and thus HFO should not be used
    # TODO: Use latitude and longitude to match against ECA areas
    return "MDO"


def _guesstimate_vessel_size_as_GrossTonnage(ceto_ship_type: str) -> float:
    allowed_ceto_ship_types = (
        "ferry-pax",
        "ferry-ropax",
        "cruise",
        "yacht",
        "miscellaneous-fishing",
        "service-tug",
        "offshore",
        "service-other",
        "miscellaneous-other",
    )
    if ceto_ship_type not in allowed_ceto_ship_types:
        raise ValueError(
            "Cannot guesstimate vessel size as Gross Tonnage for %s, allowed types are %s",
            ceto_ship_type,
            allowed_ceto_ship_types,
        )


def _guesstimate_vessel_size_as_DeadWeightTonnage(
    ceto_ship_type: str,
    length: float,
    beam: float,
    draft: float,
) -> float:
    """Dead Weight Tonnage guesstimation using table provided by Barras(2004).

    Args:
        ceto_ship_type (str): The ceto ship type
        length (float): Length of vessel [m]
        beam (float): Beam of vessel [m]
        draft (float): Design draft of vessel [m]

    Raises:
        ValueError: if the provided ceto_ship_type is not suitable for DWT estimation

    Returns:
        float: The estimated DWT
    """
    allowed_ceto_ship_types = (
        "bulk_carrier",
        "chemical_tanker",
        "general_cargo",
        "oil_tanker",
        "other_liquids_tanker",
        "refrigerated_cargo",
        "roro",
    )
    if ceto_ship_type not in allowed_ceto_ship_types:
        raise ValueError(
            "Cannot guesstimate vessel size as Dead Weight Tonnage for %s, allowed types are %s",
            ceto_ship_type,
            allowed_ceto_ship_types,
        )

    block_coefficient = _guesstimate_block_coefficient(ceto_ship_type)
    displacement = block_coefficient * length * beam * draft

    if "tanker" in ceto_ship_type:
        return displacement * 0.83
    elif ceto_ship_type in ("bulk_carrier", "general_cargo", "refrigerated_cargo"):
        return displacement * 0.7

    # else ceto_ship_type == "roro":
    return displacement * 0.3


def _guesstimate_vessel_size_as_CubicMetres(ceto_ship_type: str) -> float:
    allowed_ceto_ship_types = ("liquified_gas_tanker",)
    if ceto_ship_type not in allowed_ceto_ship_types:
        raise ValueError(
            "Cannot guesstimate vessel size as Cubic Metres for %s, allowed types are %s",
            ceto_ship_type,
            allowed_ceto_ship_types,
        )


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
    # Validation
    if not _validate_dims(dim_a, dim_b, dim_c, dim_d):
        raise ValueError(
            "Dims (dim_a, dim_b, dim_c, dim_d) are not deemed reasonable. No estimations can be made."
        )

    # Ship type
    ceto_ship_type = _map_type_of_ship_and_cargo_type_to_ceto_ship_type(
        type_of_ship_and_cargo_type
    )

    # Main dimensions
    length, beam = dim_a + dim_b, dim_c, dim_d
    design_draft = _guesstimate_design_draft(draft, beam)
    design_speed = _guesstimate_design_speed(length, ceto_ship_type, speed)

    # Vessel size
    vessel_size = {
        "bulk_carrier": _guesstimate_vessel_size_as_DeadWeightTonnage,
        "oil_tanker": _guesstimate_vessel_size_as_DeadWeightTonnage,
    }[ceto_ship_type]()

    # Engine parameters
    number_of_engines = _guesstimate_number_of_engines(ceto_ship_type)
    engine_power = 1000  # TODO: Engine power
    engine_type = _guesstimate_engine_type(ceto_ship_type)
    engine_fuel_type = _guesstimate_engine_fuel_type(
        ceto_ship_type, latitude, longitude
    )

    # Vessel size

    # Assemble
    vessel_data = {
        # Fixed values that will not be inferred from AIS data but are reasonable static assumptions
        **{
            "double_ended": False,
            "propulsion_engine_age": "after_2000",
        },
        # Guesstimated values
        **{
            "type": ceto_ship_type,
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

    return {
        "design_speed": 10,  # kn
        "design_draft": 7,  # m
        "number_of_propulsion_engines": 1,
        "propulsion_engine_power": 1_000,
        "propulsion_engine_type": "MSD",
        "propulsion_engine_age": "after_2000",
        "propulsion_engine_fuel_type": "MDO",
        "type": "offshore",
        "size": None,
        "double_ended": False,
    }


EARTH_RADIUS = 6367.0 * 1000.0


def _rhumbline(
    latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float
) -> Tuple[float, float]:
    # Rhumbline distance from (x1,y1) -> (x2,y2) in WGS 84

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

    bb = math.arctan2(dlon, dPhi)
    if bb < 0:
        bb = 2 * math.pi + bb

    brng = bb
    dist = math.sqrt(dlat * dlat + q * q * dlon * dlon) * EARTH_RADIUS

    return brng, dist


def guesstimate_voyage_data(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
    draft_1: float,
    draft_2: float,
    speed_1: float,
    speed_2: float,
    time_1: float,
    time_2: float,
    design_speed: float,
) -> dict:
    _, distance = _rhumbline(latitude_1, longitude_1, latitude_2, longitude_2)
    distance /= 0.5144  # nm

    delta_time = time_2 - time_1  # hours

    avg_speed = 0.5 * (speed_1 + speed_2)  # knots

    if not (0.75 <= (distance / delta_time) / avg_speed <= 1.25):
        avg_speed = distance / delta_time

    avg_draft = 0.5 * (draft_1 + draft_2)

    default_output = {
        "time_anchored": 0.0,
        "time_at_berth": 0.0,
        "legs_manoeuvring": [],
        "legs_at_sea": [],
    }

    if avg_speed < 3.0:
        return {**default_output, **{"time_anchored": delta_time}}

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
