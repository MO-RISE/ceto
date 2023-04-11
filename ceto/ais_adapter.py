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

    if not (2 <= length / beam <= 10):
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


def _froude_number(length: float, speed: float) -> float:
    g = 9.81
    return speed / math.sqrt(g * length)


def _guesstimate_length(ceto_ship_type: str, speed: float) -> float:
    # TODO: Use ceto_ship_type and speed to make a more educated guess about the length (and the beam)
    return 75


def _guesstimate_length_over_beam_ratio(length: float) -> float:
    capped_length = max(30, min(130, length))
    return 4.0 + 0.025 * (capped_length - 30)


def _guesstimate_beam(length: float, ceto_ship_type: str) -> float:
    if "tanker" in ceto_ship_type:
        return length / 9 + 5.5
    elif ceto_ship_type == "general_cargo":
        return length / 9 + 6.75

    # else
    return length / _guesstimate_length_over_beam_ratio(length)


def _guesstimate_length_and_beam(
    dim_a: float,
    dim_b: float,
    dim_c: float,
    dim_d: float,
    ceto_ship_type: str,
    speed: float,
) -> Tuple[float, float]:
    if _validate_dims(dim_a, dim_b, dim_c, dim_d):
        return dim_a + dim_d, dim_c + dim_d

    warnings.warn(
        "Dimensions (dim_a, dim_b, dim_c, dim_d) are deemed unreasonable. Length and beam will be guesstimated."
    )

    length = _guesstimate_length(ceto_ship_type, speed)
    beam = _guesstimate_beam(length, ceto_ship_type)

    return length, beam


def _guesstimate_design_draft(ais_draft: float, beam: float) -> float:
    return ais_draft if 2.25 <= ais_draft / beam <= 3.75 else beam / 3


def _guesstimate_design_speed(
    length: float, ceto_ship_type: str, speed: float
) -> float:
    g = 9.81
    block_coefficient = _guesstimate_block_coefficient(ceto_ship_type)
    design_speed = ms_to_knots((0.145 * math.sqrt(g * length)) / block_coefficient)
    return speed if speed > design_speed else design_speed


def _guesstimate_number_of_engines(ceto_ship_type: str):
    if ceto_ship_type in ("ferry-pax", "ferry-ropax"):
        return 2

    # else
    return 1


def _guesstimate_engine_fuel_type(
    ceto_ship_type: str, latitude: float, longitude: float
) -> str:
    if ceto_ship_type == "liquified_gas_tanker":
        return "LNG"

    # else the coice of HFO vs MDO depends primarily on ECA areas
    # the whole Baltic Sea is an ECA area and thus HFO should not be used
    # TODO: Use latitude and longitude to match against ECA areas
    return "MDO"


def _guesstimate_vessel_size_as_GrossTonnage(ceto_ship_type: str) -> float:
    allowed_ceto_ship_types = (
        "bulk_carrier",
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


def _guesstimate_vessel_size_as_DeadWeightTonnage(ceto_ship_type: str) -> float:
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
    # Fixed values that will not be inferred from AIS data but are reasonable static assumptions
    vessel_data = {
        "double_ended": False,
        "propulsion_engine_age": "after_2000",
    }

    # Ship type
    ceto_ship_type = _map_type_of_ship_and_cargo_type_to_ceto_ship_type(
        type_of_ship_and_cargo_type
    )

    # Main dimensions
    length, beam = _guesstimate_length_and_beam(
        dim_a, dim_b, dim_c, dim_d, ceto_ship_type, speed
    )
    design_draft = _guesstimate_design_draft(draft, beam)
    design_speed = _guesstimate_design_speed(length, ceto_ship_type)

    # Engine parameters
    number_of_engines = _guesstimate_number_of_engines(ceto_ship_type)
    engine_power = 1000  # TODO: Engine power
    engine_type = "SSD"  # TODO: Type of engine
    engine_fuel_type = _guesstimate_engine_fuel_type(
        ceto_ship_type, latitude, longitude
    )

    # Vessel size

    # Assemble
    vessel_data = {
        **vessel_data,
        **{
            "type": ceto_ship_type,
            "length": length,
            "beam": beam,
            "design_draft": design_draft,
            "design_speed": design_speed,
            "number_of_propulsion_engines": number_of_engines,
            "propulsion_engine_power": engine_power,
            "propulsion_engine_type": engine_type,
            "propulsion_engine_fuel_type": engine_fuel_type,
        },
    }

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


def guesstimate_voyage_data(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
    draft: float,
) -> dict:
    return {
        "time_anchored": 10.0,  # time
        "time_at_berth": 10.0,  # time
        "legs_manoeuvring": [
            (10, 10, draft),  # distance (nm), speed (kn), draft (m)
        ],
        "legs_at_sea": [
            (10, 10, draft),
            (20, 10, draft),
        ],  # distance (nm), speed (kn), draft (m)
    }
