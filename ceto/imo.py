"""
[1] IMO. Fourth IMO GHG Study 2020. IMO.



"""
import math

# pylint: disable=too-many-locals


from ceto.utils import (
    verify_range,
    verify_set,
    verify_key_value_range,
    verify_key_value_set,
    verify_key_value_type,
)

VESSEL_TYPES = [
    "bulk_carrier",
    "chemical_tanker",
    "container",
    "general_cargo",
    "liquified_gas_tanker",
    "oil_tanker",
    "other_liquids_tanker",
    "ferry",
    "cruise",
    "ropax",
    "refrigerated_cargo",
    "roro",
    "vehicle",
    "yacht",
    "miscellaneous-fishing",
    "service-tug",
    "offshore",
    "service-other",
    "miscellaneous-other",
]

FUEL_TYPES = ["HFO", "MDO", "MeOH", "LNG"]

ENGINE_TYPES = [
    "SSD",
    "MSD",
    "HSD",
    "LNG-Otto-MS",
    "LBSI",
    "gas_turbine",
    "steam_turbine",
]

ENGINE_AGES = ["before_1983", "1984-2000", "after_2001"]


def calculate_fuel_volume(mass, fuel_type):
    """Calculate the fuel volume

    Arguments:
    -----------

        mass: float
            Mass of fuel (kg).

        fuel_type: string
            Type of fuel. Possible values:
                - HFO: Heavy Fuel Oil
                - MDO: Marine Diesel Oil
                - LNG: Liquid Natural Gas
                - MeOH: Methanol

    Returns:
    --------

        float
            Volume of the fuel (m3).

    Source:
        Table 10 in page 294 of [1].
    """
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    if fuel_type == "HFO":
        return mass / 1001
    elif fuel_type == "MDO":
        return mass / 895
    elif fuel_type == "LNG":
        return mass / 450
    else:
        return mass / 790


def calculate_fuel_mass(volume, fuel_type):
    """Calculate the fuel mass

    Arguments:
    -----------

        volume: float
            Volume of fuel (m3).

        fuel_type: string
            Type of fuel. Possible values:
                - HFO: Heavy Fuel Oil
                - MDO: Marine Diesel Oil
                - LNG: Liquid Natural Gas
                - MeOH: Methanol

    Returns:
    --------

        float
            Mass of the fuel (kg).

    Source:
        Table 10 in page 294 of [1].
    """
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    if fuel_type == "HFO":
        return volume * 1001
    elif fuel_type == "MDO":
        return volume * 895
    elif fuel_type == "LNG":
        return volume * 450
    else:
        return volume * 790


def estimate_specific_fuel_consumption(engine_load, engine_type, fuel_type, engine_age):
    """
    According to [1]

    NOTE: The duel fuel engine types LNG-Otto-SS and LNG-Diesel are not
    implemented.

    Arguments:
    ----------

            engine_load: float
                Engine load as a fraction between 0.0 and 1.0.

            engine_type: string
                Possible values:
                    - SSD: Slow-Speed Diesel (RPM <= 300)
                    - MSD: Medium-Speed Diesel (300 < RPM <= 900)
                    - HSD: High-Speed Diesel (RPM > 900)
                    - LNG-Otto-MS
                    - LBSI
                    - gas_turbine
                    - steam_turbine
                    - steam_boiler
                    - auxiliary_engine

            fuel_type: string
                Type of fuel used by the engine. Possible values:
                    - HFO: Heavy Fuel Oil
                    - MDO: Marine Diesel Oil
                    - MeOH: Methanol
                    - LNG: Liquid Natural Gas



            engine_age: string

    Returns:
    --------

        float
            Specific fuel consumption (kg/kWh)

    """

    # Baseline SFC in g/kWh (Table 19 in [1])
    sfc_baselines = {
        "SSD": {
            "HFO": {"before_1983": 205, "1984-2000": 185, "after_2001": 175},
            "MDO": {"before_1983": 190, "1984-2000": 175, "after_2001": 165},
            "MeOH": {"after_2001": 350},
        },
        "MSD": {
            "HFO": {"before_1983": 215, "1984-2000": 195, "after_2001": 185},
            "MDO": {"before_1983": 200, "1984-2000": 185, "after_2001": 175},
            "MeOH": {"after_2001": 370},
        },
        "HSD": {
            "HFO": {"before_1983": 225, "1984-2000": 205, "after_2001": 195},
            "MDO": {"before_1983": 210, "1984-2000": 190, "after_2001": 185},
        },
        "LNG-Otto-MS": {"LNG": {"1984-2000": 173, "after_2001": 156}},
        "LBSI": {"LNG": {"1984-2000": 156, "after_2001": 156}},
        "gas_turbine": {
            "HFO": {"before_1983": 305, "1984-2000": 305, "after_2001": 305},
            "MDO": {"before_1983": 300, "1984-2000": 300, "after_2001": 300},
            "LNG": {"after_2001": 203},
        },
        "steam_turbine": {
            "HFO": {"before_1983": 340, "1984-2000": 340, "after_2001": 340},
            "MDO": {"before_1983": 320, "1984-2000": 320, "after_2001": 320},
            "LNG": {"before_1983": 285, "1984-2000": 285, "after_2001": 285},
        },
        "steam_boiler": {
            "HFO": {"before_1983": 340, "1984-2000": 340, "after_2001": 340},
            "MDO": {"before_1983": 320, "1984-2000": 320, "after_2001": 320},
            "LNG": {"before_1983": 285, "1984-2000": 285, "after_2001": 285},
        },
        "auxiliary_engine": {
            "HFO": {"before_1983": 225, "1984-2000": 205, "after_2001": 195},
            "MDO": {"before_1983": 210, "1984-2000": 190, "after_2001": 185},
            "LNG": {"after_2001": 156},
        },
    }

    # Verify
    # engine_types = ENGINE_TYPES.extend(["steam_boiler", "auxiliary_engine"])
    # print(engine_types)
    # verify_set(
    #    "engine_type",
    #    engine_type,
    #    engine_types,
    # )
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    verify_set("engine_age", engine_age, ENGINE_AGES)
    verify_range("engine_load", engine_load, 0, 1.5)

    try:
        sfc_baseline = sfc_baselines[engine_type][fuel_type][engine_age]
    except KeyError as err:
        raise ValueError(
            f"No specific fuel consumption baseline found for {engine_type}, {fuel_type}, {engine_age}"
        ) from err

    # For gas turbines, steam turbines, auxiliary engines, and steam boilers the SFC
    # is assumed to be independent of the engine load.
    if engine_type in [
        "gas_turbine",
        "steam_turbine",
        "auxiliary_engine",
        "steam_boiler",
    ]:
        sfc = sfc_baseline / 1_000
    else:
        sfc = (
            sfc_baseline
            * (0.455 * engine_load**2 - 0.710 * engine_load + 1.280)
            / 1_000
        )

    return sfc


MAX_VESSEL_SPEED_KN = 50
MIN_VESSEL_DRAFT = 0.1
MAX_VESSEL_DRAFT_M = 25
MIN_ENGINE_RPM = 50
MIN_ENGINE_POWER_KW = 5
MAX_ENGINE_RPM = 5_000
MAX_ENGINE_POWER_KW = 60_000


"""
vessel_type: string
            One fo the following vessel types:
                - 'bulk_carrier'
                - 'chemical_tanker'
                - 'container'
                - 'general_cargo'
                - 'liquified_gas_tanker'
                - 'oil_tanker'
                - 'other_liquids_tanker'
                - 'ferry'
                - 'cruise'
                - 'ropax'
                - 'refrigerated_cargo'
                - 'roro'
                - 'vehicle'
                - 'yacht'
                - 'miscellaneous-fishing'
                - 'service-tug'
                - 'offshore'
                - 'service-other'
                - 'miscellaneous-other'


        size: int
            Size of the vessel in the appropriate units for the vessel type.
                - 'bulk_carrier' -> DWT
                - 'chemical_tanker' -> DWT
                - 'container' -> TEU
                - 'general_cargo' -> DWT
                - 'liquified_gas_tanker' -> CBM
                - 'oil_tanker' -> DWT
                - 'other_liquids_tanker' -> DWT
                - 'ferry' -> GT
                - 'cruise' -> GT
                - 'ropax' -> GT
                - 'refrigerated_cargo' -> DWT
                - 'roro' -> DWT
                - 'vehicle' -> NC
                - 'yacht' -> GT
                - 'miscellaneous-fishing' -> GT
                - 'service-tug' -> GT
                - 'offshore' -> GT
                - 'service-other' -> GT
                - 'miscellaneous-other' -> GT
            where:
                - DWT: Deadweight Tonnage
                - TEU: Twenty-foot Equivalent Units
                - CBM: Cubic Metre
                - GT: Gross Tonnes
                - NC: Number of cars


"""


def verify_vessel_data(vessel_data):
    """Verify the contents of the 'vessel_data' dictionary"""

    try:

        verify_key_value_range(
            "vessel_data", "design_speed", vessel_data, 0, MAX_VESSEL_SPEED_KN
        )
        verify_key_value_range(
            "vessel_data", "design_draft", vessel_data, 0, MAX_VESSEL_DRAFT_M
        )
        verify_key_value_set(
            "vessel_data", "number_of_propulsion_engines", vessel_data, [1, 2]
        )
        verify_key_value_range(
            "vessel_data",
            "propulsion_engine_power",
            vessel_data,
            MIN_ENGINE_POWER_KW,
            MAX_ENGINE_POWER_KW,
        )
        verify_key_value_set(
            "vessel_data", "propulsion_engine_type", vessel_data, ENGINE_TYPES
        )
        verify_key_value_set(
            "vessel_data", "propulsion_engine_age", vessel_data, ENGINE_AGES
        )
        verify_key_value_set(
            "vessel_data", "propulsion_engine_fuel_type", vessel_data, FUEL_TYPES
        )
        verify_key_value_set("vessel_data", "type", vessel_data, VESSEL_TYPES)

        if vessel_data["size"] is not None:
            verify_key_value_range("vessel_data", "size", vessel_data, 0, 500_000)
        else:
            none_vessel_types = [
                "yacht",
                "service-tug",
                "miscellaneous-fishing",
                "offshore",
                "service-other",
                "miscellaneous-other",
            ]
            if vessel_data["type"] not in none_vessel_types:
                raise ValueError(
                    f"The value for the key 'size', in the variable 'vessel_data', can ONLYs be 'None' for the vessel types: {none_vessel_types}."
                )

    except KeyError as err:
        raise KeyError(
            f"The variable 'vessel_data' is missing the {err} key-value pair."
        ) from err


def verify_voyage_profile(voyage_profile):
    """Verify the contents of a voyage_profile variable"""
    max_hours = 24 * 365  # One year's worth of hours
    try:
        verify_key_value_type("voyage_profile", "time_anchored", voyage_profile, float)
        verify_key_value_range(
            "voyage_profile", "time_anchored", voyage_profile, 0, max_hours
        )

        verify_key_value_type("voyage_profile", "time_at_berth", voyage_profile, float)
        verify_key_value_range(
            "voyage_profile", "time_at_berth", voyage_profile, 0, max_hours
        )

        verify_key_value_type(
            "voyage_profile", "legs_manoeuvring", voyage_profile, list
        )

        verify_key_value_type("voyage_profile", "legs_at_sea", voyage_profile, list)

    except KeyError as err:
        raise KeyError(
            f"The variable 'voyage_profile' is missing the {err} key-value pair."
        ) from err


def estimate_auxiliary_power_demand(vessel_data, operation_mode):
    """
    Calculate auxiliary power demand according to IMO's 4th green house gas emission study.

    NOTE: Unsure about the appropriate size units for vessel of type 'vehicle'.

    Arguments:
    ----------

        vessel_data: dict
            Dictionary containing the vessel data.

        operation_mode: string
            One of the following operation modes:
                - 'at_berth'
                - 'anchored'
                - 'manoeuvring'
                - 'at_sea'

    Returns
    -------

        Tuple( ux_engine_power, boiler_power) in kW.

    """

    # Verify arguments
    verify_set(
        "operation_mode",
        operation_mode,
        ["at_berth", "anchored", "manoeuvring", "at_sea"],
    )

    verify_vessel_data(vessel_data)

    # Reproduction of Table 17 in page 68 of [1] as dictionaries
    vessel_sizes = {
        "bulk_carrier": [0, 10_000, 35_000, 60_000, 100_000, 200_000],
        "chemical_tanker": [0, 5_000, 10_000, 20_000, 40_000],
        "container": [0, 1_000, 2_000, 3_000, 5_000, 8_000, 12_000, 14_500, 20_000],
        "general_cargo": [0, 5_000, 10_000, 20_000],
        "liquified_gas_tanker": [0, 50_000, 100_000, 20_000],
        "oil_tanker": [0, 5_000, 10_000, 20_000, 60_00, 80_000, 120_000, 200_000],
        "other_liquids_tankers": [0, 1_000],
        "ferry": [0, 300, 1_000, 2_000],
        "cruise": [0, 2_000, 10_000, 60_000, 100_000, 150_000],
        "ropax": [0, 2_000, 5_000, 10_000, 20_000],
        "refrigerated_bulk": [0, 2_000, 6_000, 10_000],
        "roro": [0, 5_000, 10_000, 15_000],
        "vehicle": [0, 10_000, 20_000],
        "yacht": [0],
        "service-tug": [0],
        "miscellaneous-fishing": [0],
        "offshore": [0],
        "service-other": [0],
        "miscellaneous-other": [0],
    }

    auxiliary_power_outputs = {
        "bulk_carrier": [
            [70, 70, 60, 0, 110, 180, 500, 190],
            [70, 70, 60, 0, 110, 180, 500, 190],
            [130, 130, 120, 0, 150, 250, 680, 260],
            [260, 260, 240, 0, 240, 400, 1100, 410],
            [260, 260, 240, 0, 240, 400, 1100, 410],
            [260, 260, 240, 0, 240, 400, 1100, 410],
        ],
        "chemical_tanker": [
            [670, 160, 130, 0, 110, 170, 190, 200],
            [670, 160, 130, 0, 330, 490, 560, 580],
            [1_000, 240, 200, 0, 330, 490, 560, 580],
            [1_350, 320, 270, 0, 790, 550, 900, 660],
            [1_350, 320, 270, 0, 790, 550, 900, 660],
        ],
        "container": [
            [250, 250, 240, 0, 370, 450, 790, 410],
            [340, 340, 310, 0, 820, 910, 1_750, 900],
            [460, 450, 430, 0, 610, 910, 1_900, 920],
            [480, 480, 430, 0, 1_100, 1_350, 2_500, 1_400],
            [590, 580, 550, 0, 1_100, 1_400, 2_800, 1_450],
            [620, 620, 540, 0, 1_150, 1_600, 2_900, 1_800],
            [630, 630, 630, 0, 1_300, 1_800, 3_250, 2_050],
            [630, 630, 630, 0, 1_400, 1_950, 3_600, 2_300],
            [700, 700, 700, 0, 1_400, 1_950, 3_600, 2_300],
        ],
        "general_cargo": [
            [0, 0, 0, 0, 90, 50, 180, 60],
            [110, 110, 100, 0, 240, 130, 490, 180],
            [150, 150, 130, 0, 720, 370, 1_450, 520],
            [150, 150, 130, 0, 720, 370, 1_450, 520],
        ],
        "liquified_gas_tanker": [
            [1_000, 200, 200, 100, 240, 240, 360, 240],
            [1_000, 200, 200, 100, 1_700, 1_700, 2_600, 1_700],
            [1_500, 300, 300, 150, 2_500, 2_000, 2_300, 2_650],
            [3_000, 600, 600, 300, 6_750, 7_200, 7_200, 6_750],
        ],
        "oil_tanker": [
            [500, 100, 100, 0, 250, 250, 375, 250],
            [750, 150, 150, 0, 375, 375, 560, 375],
            [1_250, 250, 250, 0, 690, 500, 580, 490],
            [2_700, 270, 270, 270, 720, 520, 600, 510],
            [3_250, 360, 360, 280, 620, 490, 770, 560],
            [4_000, 400, 400, 280, 800, 640, 910, 690],
            [6_500, 500, 500, 300, 2_500, 770, 1_300, 860],
            [7_000, 600, 600, 300, 2_500, 770, 1_300, 860],
        ],
        "other_liquids_tankers": [
            [1_000, 200, 200, 100, 500, 500, 750, 500],
            [1_000, 200, 200, 100, 500, 500, 750, 500],
        ],
        "ferry": [
            [0, 0, 0, 0, 190, 190, 190],
            [0, 0, 0, 0, 190, 190, 190],
            [0, 0, 0, 0, 190, 190, 190],
            [0, 0, 0, 0, 520, 520, 520, 520],
        ],
        "cruise": [
            [1_100, 950, 980, 0, 450, 450, 580, 450],
            [1_100, 950, 980, 0, 450, 450, 580, 450],
            [1_100, 950, 980, 0, 3_500, 3_500, 5_500, 3_500],
            [1_100, 950, 980, 0, 11_500, 11_500, 14_900, 11_500],
            [1_100, 950, 980, 0, 11_500, 11_500, 14_900, 11_500],
            [1_100, 950, 980, 0, 11_500, 11_500, 14_900, 11_500],
        ],
        "ropax": [
            [260, 250, 170, 0, 105, 105, 105, 105],
            [260, 250, 170, 0, 330, 330, 330, 330],
            [260, 250, 170, 0, 670, 670, 670, 670],
            [390, 380, 260, 0, 1_100, 1_100, 1_100, 1_000],
            [390, 380, 260, 0, 1_950, 1_950, 1_950, 1_950],
        ],
        "refrigerated_bulk": [
            [270, 270, 270, 0, 520, 570, 560, 570],
            [270, 270, 270, 0, 1_100, 1_200, 1_150, 1_200],
            [270, 270, 270, 0, 1_500, 1_650, 1_600, 1_650],
            [270, 270, 270, 0, 2_850, 3_100, 3_000, 3_100],
        ],
        "roro": [
            [260, 250, 170, 0, 750, 430, 1_300, 430],
            [260, 250, 170, 0, 1_100, 680, 2_100, 680],
            [390, 380, 260, 0, 1_200, 950, 2_700, 950],
            [390, 380, 260, 0, 1_200, 950, 2_700, 950],
        ],
        "vehicle": [
            [310, 300, 250, 0, 800, 500, 1_100, 500],
            [310, 300, 250, 0, 850, 550, 1_400, 510],
            [310, 300, 250, 0, 850, 550, 1_400, 510],
        ],
        "yacht": [[0, 0, 0, 0, 130, 130, 130, 130]],
        "service-tug": [[0, 0, 0, 0, 100, 80, 210, 80]],
        "miscellaneous-fishing": [[0, 0, 0, 0, 200, 200, 200, 200]],
        "offshore": [[0, 0, 0, 0, 320, 320, 320, 320]],
        "service-other": [[0, 0, 0, 0, 220, 220, 220, 220]],
        "miscellaneous-other": [[110, 110, 90, 0, 150, 150, 430, 410]],
    }

    column_indexes = {
        "at_berth": (0, 4),
        "anchored": (1, 5),
        "manoeuvring": (2, 6),
        "at_sea": (3, 7),
    }

    size = 0 if vessel_data["size"] is None else vessel_data["size"]
    vessel_type = vessel_data["type"]
    installed_propulsion_power = (
        vessel_data["number_of_propulsion_engines"]
        * vessel_data["propulsion_engine_power"]
    )

    # Determine indexes for vessel type and operation mode
    boiler_index, engine_index = column_indexes[operation_mode]
    row_index = (
        sum([size >= vessel_size for vessel_size in vessel_sizes[vessel_type]]) - 1
    )

    # Calculate auxiliary power
    if installed_propulsion_power < 150:
        aux_engine_power = 0
        boiler_power = 0
    elif 150 <= installed_propulsion_power < 500:
        aux_engine_power = 0.05 * installed_propulsion_power
        boiler_power = auxiliary_power_outputs[vessel_type][row_index][boiler_index]
    else:
        boiler_power = auxiliary_power_outputs[vessel_type][row_index][boiler_index]
        aux_engine_power = auxiliary_power_outputs[vessel_type][row_index][engine_index]

    return aux_engine_power, boiler_power


def estimate_propulsion_engine_load(speed, draft, vessel_data, delta_w=None):
    """Estimate the propulsion engine load of a vessel

    Uses the IMO's 4th GHG study methodology.

    Arguments:
    ----------

        speed: float
            Current speed of vessel (kn).

        draft: float
            Current draft of the vessel (m).

        vessel_data: dict
            Dictionary containing the vessel data.

        delta_w (optional): float
            Speed-power correction factor: percentage of the Maximum Continous Rating (MCR) of the
            installed propulsion power at which the design speed is reached in calm water. Defaults
            to the considerations in [1] to be equal to 0.75 for container ships over 14,500 TEU,
            0.7 for cruise ships, and 1.0 for all other vessels (i.e. 75%, 70%, and 100% MCR,
            respectively). If given a value, the value will override these defaults.

    Returns:
    --------

        float
            Engine load as a value between 0.0 and 1.0

    """
    # Verify arguments
    verify_range("speed", speed, 0, MAX_VESSEL_SPEED_KN)
    verify_range("draft", draft, MIN_VESSEL_DRAFT, MAX_VESSEL_DRAFT_M)
    verify_vessel_data(vessel_data)
    if delta_w is not None:
        verify_range("delta_w", delta_w, 0, 1)

    # Weather correction factor (eta_w)
    vessels_with_10_000_dwt_as_threshold_for_w_c = [
        "bulk_carrier",
        "chemical_carrier",
        "general_cargo",
        "oil_tanker",
    ]
    vessels_with_w_c_fixed_at_867 = [
        "yacht",
        "vehicle",
        "refrigerated_bulk",
        "other_liquid_tankers",
    ]
    vessels_with_w_c_fixed_at_909 = [
        "service-tug",
        "miscellaneous-fishing",
        "offshore",
        "service-other",
        "miscellaneous-other",
        "ropax",
        "ferry",
    ]

    size = vessel_data["size"]
    vessel_type = vessel_data["type"]
    design_draft = vessel_data["design_draft"]
    design_speed = vessel_data["design_speed"]

    if vessel_type in vessels_with_10_000_dwt_as_threshold_for_w_c:
        eta_w = 0.909 if size < 10_000 else 0.867
    elif vessel_type in vessels_with_w_c_fixed_at_867:
        eta_w = 0.867
    elif vessel_type in vessels_with_w_c_fixed_at_909:
        eta_w = 0.909
    elif vessel_type == "container":
        eta_w = 0.900 if size < 1000 else 0.867
    elif vessel_type == "cruise":
        eta_w = 0.909 if size < 2000 else 0.867
    elif vessel_type == "roro":
        eta_w = 0.909 if size < 5000 else 0.867
    else:
        raise ValueError("Bug in the function.")

    # Fouling correction factor (eta_f)
    eta_f = 0.917

    # Speed power correction factor delta_w
    if delta_w is None:
        if vessel_type == "container" and size > 14_500:
            delta_w = 0.75
        elif vessel_type == "cruise":
            delta_w = 0.7
        else:
            delta_w = 1

    # Engine load: a part of equation 8 in page 64 of [1]
    return (
        delta_w
        * ((draft / design_draft) ** (2 / 3) * (speed / design_speed) ** 3)
        / (eta_f * eta_w)
    )


def estimate_fuel_consumption_of_auxiliary_systems(vessel_data, operation_mode, time):
    """Estimate the fuel consumption of the auxiliary systems:
    auxiliary engines and steam boilers

    Assumption: The fuel type and age of the steam boilers and auxiliary engines
    is assumed to be the same as the one of the propulsion engine(s).


    Returns:
    --------

        Dict
            Fuel consumption of the auxiliary systems (kg).

    """

    fuel_type = vessel_data["propulsion_engine_fuel_type"]
    engine_age = vessel_data["propulsion_engine_age"]

    aux_engine_power, boiler_power = estimate_auxiliary_power_demand(
        vessel_data, operation_mode
    )
    aux_engine_sfc = estimate_specific_fuel_consumption(
        1.0, "auxiliary_engine", fuel_type, engine_age
    )
    boiler_sfc = estimate_specific_fuel_consumption(
        1.0, "steam_boiler", fuel_type, engine_age
    )

    fc_aux_engine = aux_engine_power * aux_engine_sfc * time
    fc_boiler = boiler_power * boiler_sfc * time

    return {
        "auxiliary_engine": fc_aux_engine,
        "steam_boiler": fc_boiler,
    }


def estimate_fuel_consumption(
    vessel_data,
    voyage_profile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate the fuel consumption of a vessel

    Returns:
    --------

        Tuple(total_fuel, fuel_breakdown)
            Total fuel consumed (kg) and breakdown according to the voyage profile.
    """
    installed_propulsion_power = (
        vessel_data["number_of_propulsion_engines"]
        * vessel_data["propulsion_engine_power"]
    )

    fuel_type = vessel_data["propulsion_engine_fuel_type"]
    engine_age = vessel_data["propulsion_engine_age"]
    engine_type = vessel_data["propulsion_engine_type"]

    # At berth
    fc_aux_at_berth = estimate_fuel_consumption_of_auxiliary_systems(
        vessel_data, "at_berth", voyage_profile["time_at_berth"]
    )

    # Anchored
    fc_aux_anchored = estimate_fuel_consumption_of_auxiliary_systems(
        vessel_data, "anchored", voyage_profile["time_anchored"]
    )

    # Manoeuvring
    total_time_manoeuvring = sum(
        [distance / speed for distance, speed, _ in voyage_profile["legs_manoeuvring"]]
    )
    fc_aux_manoeuvring = estimate_fuel_consumption_of_auxiliary_systems(
        vessel_data, "manoeuvring", total_time_manoeuvring
    )

    fc_prop_manoeuvring = 0
    dist_manoeuvring = 0.0
    for distance, speed, draft in voyage_profile["legs_manoeuvring"]:
        load = estimate_propulsion_engine_load(
            speed, draft, vessel_data, delta_w=delta_w
        )
        dist_manoeuvring += distance
        if load < 0.07 and limit_7_percent:
            continue
        sfc = estimate_specific_fuel_consumption(
            load, engine_type, fuel_type, engine_age
        )
        time = distance / speed
        fc_prop_manoeuvring += installed_propulsion_power * load * sfc * time

    # At sea
    total_time_at_sea = sum(
        [distance / speed for distance, speed, _ in voyage_profile["legs_at_sea"]]
    )
    fc_aux_at_sea = estimate_fuel_consumption_of_auxiliary_systems(
        vessel_data, "at_sea", total_time_at_sea
    )

    fc_prop_at_sea = 0.0
    dist_at_sea = 0.0
    for distance, speed, draft in voyage_profile["legs_at_sea"]:

        load = estimate_propulsion_engine_load(
            speed, draft, vessel_data, delta_w=delta_w
        )
        dist_at_sea += distance
        if load < 0.07 and limit_7_percent:
            continue
        sfc = estimate_specific_fuel_consumption(
            load, engine_type, fuel_type, engine_age
        )
        time = distance / speed
        fc_prop_at_sea += installed_propulsion_power * load * sfc * time

    fc_at_berth = fc_aux_at_berth["auxiliary_engine"]
    fc_anchored = fc_aux_anchored["auxiliary_engine"]
    fc_manoeuvring = fc_aux_manoeuvring["auxiliary_engine"] + fc_prop_manoeuvring
    fc_at_sea = fc_aux_at_sea["auxiliary_engine"] + fc_prop_at_sea

    print(fc_manoeuvring)
    print(dist_manoeuvring)
    avg_fc_manoeuvring = (
        calculate_fuel_volume(
            fc_manoeuvring, vessel_data["propulsion_engine_fuel_type"]
        )
        * 1_000
        / dist_manoeuvring
    )
    avg_fc_at_sea = (
        calculate_fuel_volume(fc_at_sea, vessel_data["propulsion_engine_fuel_type"])
        * 1_000
        / dist_at_sea
    )

    fc_ = {
        "total_kg": fc_at_berth + fc_anchored + fc_manoeuvring + fc_at_sea,
        "at_berth": {
            "sub_total_kg": fc_at_berth,
            "auxiliary_engine": fc_aux_at_berth["auxiliary_engine"],
        },
        "anchored": {
            "sub_total_kg": fc_anchored,
            "auxiliary_engine": fc_aux_anchored["auxiliary_engine"],
        },
        "manoeuvring": {
            "sub_total_kg": fc_manoeuvring,
            "auxiliary_engine": fc_aux_manoeuvring["auxiliary_engine"],
            "propulsion_engine": fc_prop_manoeuvring,
            "average_fuel_consumption_l_per_nm": avg_fc_manoeuvring,
        },
        "at_sea": {
            "sub_total_kg": fc_at_sea,
            "auxiliary_engine_kg": fc_aux_at_sea["auxiliary_engine"],
            "propulsion_engine_kg": fc_prop_at_sea,
            "average_fuel_consumption_l_per_nm": avg_fc_at_sea,
        },
    }

    if include_steam_boilers:

        fc_at_berth += fc_aux_at_berth["steam_boiler"]
        fc_anchored += fc_aux_anchored["steam_boiler"]
        fc_manoeuvring += fc_aux_manoeuvring["steam_boiler"]
        fc_at_sea += fc_aux_at_sea["steam_boiler"]

        avg_fc_manoeuvring = (
            calculate_fuel_volume(
                fc_manoeuvring, vessel_data["propulsion_engine_fuel_type"]
            )
            * 1_000
            / dist_manoeuvring
        )
        avg_fc_at_sea = (
            calculate_fuel_volume(fc_at_sea, vessel_data["propulsion_engine_fuel_type"])
            * 1_000
            / dist_at_sea
        )

        fc_["total_kg"] = fc_at_berth + fc_anchored + fc_manoeuvring + fc_at_sea
        fc_["at_berth"]["steam_boiler"] = fc_aux_at_berth["steam_boiler"]
        fc_["at_berth"]["sub_total_kg"] = fc_at_berth
        fc_["anchored"]["steam_boiler"] = fc_aux_anchored["steam_boiler"]
        fc_["anchered"]["sub_total_kg"] = fc_anchored
        fc_["manoeuvring"]["steam_boiler"] = fc_aux_manoeuvring["steam_boiler"]
        fc_["manoeuvring"]["sub_total_kg"] = fc_manoeuvring
        fc_["manoeuvring"]["average_fuel_consumption_l_per_nm"] = avg_fc_manoeuvring
        fc_["at_sea"]["steam_boiler"] = fc_aux_at_sea["steam_boiler"]
        fc_["at_sea"]["sub_total_kg"] = fc_at_sea
        fc_["at_sea"]["average_fuel_consumption_l_per_nm"] = avg_fc_at_sea

    return fc_


def estimate_energy_consumption(
    vessel_data,
    voyage_profile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate the energy consumption of a vessel

    Returns:
    --------

        Tuple(
            total_energy_consumption,
            maximum_power_demand,
            energy_and_power_consumption_breakdown,
        )
            Total energy consumption (kWh), maximum power demand (kW), and energy and power
            consumption breakdown according to the voyage profile.

    """
    installed_propulsion_power = (
        vessel_data["number_of_propulsion_engines"]
        * vessel_data["propulsion_engine_power"]
    )

    # At berth
    (
        aux_engine_power_at_berth,
        aux_boiler_power_at_berth,
    ) = estimate_auxiliary_power_demand(vessel_data, "at_berth")
    aux_engine_energy_at_berth = (
        aux_engine_power_at_berth * voyage_profile["time_at_berth"]
    )
    aux_boiler_energy_at_berth = (
        aux_boiler_power_at_berth * voyage_profile["time_at_berth"]
    )

    # Anchored
    (
        aux_engine_power_anchored,
        aux_boiler_power_anchored,
    ) = estimate_auxiliary_power_demand(vessel_data, "anchored")
    aux_engine_energy_anchored = (
        aux_engine_power_anchored * voyage_profile["time_anchored"]
    )
    aux_boiler_energy_anchored = (
        aux_boiler_power_anchored * voyage_profile["time_anchored"]
    )

    # Manoeuvring
    total_time_manoeuvring = sum(
        [distance / speed for distance, speed, _ in voyage_profile["legs_manoeuvring"]]
    )
    (
        aux_engine_power_manoeuvring,
        aux_boiler_power_manoeuvring,
    ) = estimate_auxiliary_power_demand(vessel_data, "manoeuvring")
    aux_engine_energy_manoeuvring = (
        aux_engine_power_manoeuvring * total_time_manoeuvring
    )
    aux_boiler_energy_manoeuvring = (
        aux_boiler_power_manoeuvring * total_time_manoeuvring
    )

    propulsion_energy_manoeuvring = []
    propulsion_power_manoeuvring = []
    for distance, speed, draft in voyage_profile["legs_manoeuvring"]:
        load = estimate_propulsion_engine_load(
            speed, draft, vessel_data, delta_w=delta_w
        )
        if load < 0.07 and limit_7_percent:
            propulsion_energy_manoeuvring.append(0.0)
            propulsion_power_manoeuvring.append(0.0)
        else:
            time = distance / speed
            propulsion_energy_manoeuvring.append(
                installed_propulsion_power * load * time
            )
            propulsion_power_manoeuvring.append(installed_propulsion_power * load)

    # At sea
    total_time_at_sea = sum(
        [distance / speed for distance, speed, _ in voyage_profile["legs_at_sea"]]
    )
    aux_engine_power_at_sea, aux_boiler_power_at_sea = estimate_auxiliary_power_demand(
        vessel_data, "at_sea"
    )
    aux_engine_energy_at_sea = aux_engine_power_at_sea * total_time_at_sea
    aux_boiler_energy_at_sea = aux_boiler_power_at_sea * total_time_at_sea

    propulsion_energy_at_sea = []
    propulsion_power_at_sea = []
    for distance, speed, draft in voyage_profile["legs_at_sea"]:
        load = estimate_propulsion_engine_load(
            speed, draft, vessel_data, delta_w=delta_w
        )
        if load < 0.07 and limit_7_percent:
            propulsion_energy_at_sea.append(0.0)
            propulsion_power_at_sea.append(0.0)
        else:
            time = distance / speed
            propulsion_energy_at_sea.append(installed_propulsion_power * load * time)
            propulsion_power_at_sea.append(installed_propulsion_power * load)

    total_energy_consumption = (
        aux_engine_energy_at_berth
        + aux_engine_energy_anchored
        + aux_engine_energy_manoeuvring
        + sum(propulsion_energy_manoeuvring)
        + aux_engine_energy_at_sea
        + sum(propulsion_energy_at_sea)
    )

    energy_and_power_consumption_breakdown = {
        "at_berth": {
            "auxiliary_engine": {
                "energy": aux_engine_energy_at_berth,
                "power": aux_engine_power_at_berth,
            }
        },
        "anchored": {
            "auxiliary_engine": {
                "energy": aux_engine_energy_anchored,
                "power": aux_engine_power_anchored,
            }
        },
        "manoeuvring": {
            "auxiliary_engine": {
                "energy": aux_engine_energy_manoeuvring,
                "power": aux_engine_power_manoeuvring,
            },
            "propulsion_engine": {
                "energy": propulsion_energy_manoeuvring,
                "power": propulsion_power_manoeuvring,
            },
        },
        "at_sea": {
            "auxiliary_engine": {
                "energy": aux_engine_energy_at_sea,
                "power": aux_engine_power_at_sea,
            },
            "propulsion_engine": {
                "energy": propulsion_energy_at_sea,
                "power": propulsion_power_at_sea,
            },
        },
    }

    maximum_power_demand = max(
        [
            aux_engine_power_at_berth,
            aux_engine_power_anchored,
            aux_engine_power_manoeuvring + max(propulsion_power_manoeuvring),
            aux_engine_power_at_sea + max(propulsion_power_at_sea),
        ]
    )

    if include_steam_boilers:
        total_energy_consumption += (
            aux_boiler_energy_at_berth
            + aux_boiler_energy_anchored
            + aux_boiler_energy_manoeuvring
            + aux_boiler_energy_at_sea
        )

        energy_and_power_consumption_breakdown["at_berth"]["steam_boiler"] = {
            "energy": aux_boiler_energy_at_berth,
            "power": aux_boiler_energy_at_berth,
        }
        energy_and_power_consumption_breakdown["anchored"]["steam_boiler"] = {
            "energy": aux_boiler_energy_anchored,
            "power": aux_boiler_energy_anchored,
        }
        energy_and_power_consumption_breakdown["manoeuvring"]["steam_boiler"] = {
            "energy": aux_boiler_energy_manoeuvring,
            "power": aux_boiler_energy_manoeuvring,
        }
        energy_and_power_consumption_breakdown["at_sea"]["steam_boiler"] = {
            "energy": aux_boiler_energy_at_sea,
            "power": aux_boiler_energy_at_sea,
        }

        maximum_power_demand = max(
            [
                aux_engine_power_at_berth + aux_boiler_power_at_berth,
                aux_engine_power_anchored + aux_boiler_power_anchored,
                aux_engine_power_manoeuvring
                + aux_boiler_power_manoeuvring
                + max(propulsion_power_manoeuvring),
                aux_engine_power_at_sea
                + aux_boiler_power_at_sea
                + max(propulsion_power_at_sea),
            ]
        )

    return (
        total_energy_consumption,
        maximum_power_demand,
        energy_and_power_consumption_breakdown,
    )
