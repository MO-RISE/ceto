"""
Estimates of fuel and energy consumption for vessels. 
"""

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
    "ferry-pax",
    "cruise",
    "ferry-ropax",
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

ENGINE_AGES = ["before_1984", "1984-2000", "after_2000"]


MAX_VESSEL_SPEED_KN = 50
MIN_VESSEL_DRAFT = 0.1
MAX_VESSEL_DRAFT_M = 25
MIN_ENGINE_RPM = 50
MIN_ENGINE_POWER_KW = 5
MAX_ENGINE_RPM = 5_000
MAX_ENGINE_POWER_KW = 60_000


def verify_vessel_data(vessel_data):
    """Verify the contents of the 'vessel_data' dictionary"""

    try:
        verify_key_value_range("vessel_data", "length", vessel_data, 5.0, 450.0)

        verify_key_value_range("vessel_data", "beam", vessel_data, 1.5, 70.0)

        verify_key_value_range(
            "vessel_data", "design_speed", vessel_data, 1.0, MAX_VESSEL_SPEED_KN
        )
        verify_key_value_range(
            "vessel_data",
            "design_draft",
            vessel_data,
            MIN_VESSEL_DRAFT,
            MAX_VESSEL_DRAFT_M,
        )
        verify_key_value_set(
            "vessel_data", "number_of_propulsion_engines", vessel_data, [1, 2, 3, 4]
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

        verify_key_value_set("vessel_data", "double_ended", vessel_data, [True, False])

        if vessel_data["size"] is not None:
            verify_key_value_range("vessel_data", "size", vessel_data, 0, 500_000)

        # if vessel_data["size"] is not None:
        # else:
        #     none_vessel_types = [
        #         "yacht",
        #         "service-tug",
        #         "miscellaneous-fishing",
        #         "offshore",
        #         "service-other",
        #         "miscellaneous-other",
        #     ]
        #     if vessel_data["type"] not in none_vessel_types:
        #         raise ValueError(
        #             f"The value for the key 'size', in the variable 'vessel_data',
        #               can ONLYs be 'None' for the vessel types: {none_vessel_types}."
        #         )

    except KeyError as err:
        raise KeyError(f"'vessel_data' is missing a value for '{err}'.") from err


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
    if fuel_type == "MDO":
        return mass / 895
    if fuel_type == "LNG":
        return mass / 450
    return mass / 790


def calculate_fuel_mass(volume, fuel_type):
    """Calculate the fuel mass

    Arguments:
    -----------

        volume: float
            Volume of fuel (m3).

        fuel_type: string
            Type of fuel used by the engine. The possible types/values are:
                - 'HFO': Heavy Fuel Oil
                - 'MDO': Marine Diesel Oil
                - 'MeOH': Methanol
                - 'LNG': Liquid Natural Gas

    Returns:
    --------

        float
            Mass of the fuel (kg).

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO. (Table 10, page 294)

    """
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    if fuel_type == "HFO":
        return volume * 1001
    if fuel_type == "MDO":
        return volume * 895
    if fuel_type == "LNG":
        return volume * 450
    return volume * 790


def estimate_specific_fuel_consumption(engine_load, engine_type, fuel_type, engine_age):
    """Estimate the the specific fuel consumption of an engine

    NOTE: The duel fuel engine types LNG-Otto-SS and LNG-Diesel are not
    implemented.


    Arguments:
    ----------

        engine_load: float
            Engine load as a fraction between 0.0 and 1.0.

        engine_type: string
            Type of engine. The possible types/values are:
                - 'SSD': Slow-Speed Diesel. An oil engine with a speed equal or lower
                         than 300 RPM.
                - 'MSD': Medium-Speed Diesel. An oil engine with a speed ranging from
                         300 to 900 RPM.
                - 'HSD': High-Speed Diesel. An oil engine with a speed above 900 RPM.
                - 'LNG-Otto-MS': Four-stroke, medium-speed (300 > RPM > 900), dual-fuel
                                 engines (LNG and oils) that operate on the Otto cycle.
                - 'LBSI': LNG engines built by Rolls-Royce/Bergen.
                - 'gas_turbine': Gas turbine engine.
                - 'steam_turbine': Steam turbine engine. Includes oil-based fuels, LNG,
                                   and boil-off gas.

        fuel_type: string
            Type of fuel used by the engine. The possible types/values are:
                - 'HFO': Heavy Fuel Oil
                - 'MDO': Marine Diesel Oil
                - 'MeOH': Methanol
                - 'LNG': Liquid Natural Gas

        engine_age: string
            The age of the propulsion engine. The possible types/values are:
                - `'before_1984'`: All engines manufactured before 1984.
                - `'1984-2000'`: All engines manufactured between 1984 and 2000.
                - `'after_2000'`: All engines manufactured after 2000.

    Returns:
    --------

        float
            Specific fuel consumption (kg/kWh)

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.

    """

    # Baseline SFC in g/kWh (Table 19 in [1])
    sfc_baselines = {
        "SSD": {
            "HFO": {"before_1984": 205, "1984-2000": 185, "after_2000": 175},
            "MDO": {"before_1984": 190, "1984-2000": 175, "after_2000": 165},
            "MeOH": {"after_2000": 350},
        },
        "MSD": {
            "HFO": {"before_1984": 215, "1984-2000": 195, "after_2000": 185},
            "MDO": {"before_1984": 200, "1984-2000": 185, "after_2000": 175},
            "MeOH": {"after_2000": 370},
        },
        "HSD": {
            "HFO": {"before_1984": 225, "1984-2000": 205, "after_2000": 195},
            "MDO": {"before_1984": 210, "1984-2000": 190, "after_2000": 185},
        },
        "LNG-Otto-MS": {"LNG": {"1984-2000": 173, "after_2000": 156}},
        "LBSI": {"LNG": {"1984-2000": 156, "after_2000": 156}},
        "gas_turbine": {
            "HFO": {"before_1984": 305, "1984-2000": 305, "after_2000": 305},
            "MDO": {"before_1984": 300, "1984-2000": 300, "after_2000": 300},
            "LNG": {"after_2000": 203},
        },
        "steam_turbine": {
            "HFO": {"before_1984": 340, "1984-2000": 340, "after_2000": 340},
            "MDO": {"before_1984": 320, "1984-2000": 320, "after_2000": 320},
            "LNG": {"before_1984": 285, "1984-2000": 285, "after_2000": 285},
        },
        "steam_boiler": {
            "HFO": {"before_1984": 340, "1984-2000": 340, "after_2000": 340},
            "MDO": {"before_1984": 320, "1984-2000": 320, "after_2000": 320},
            "LNG": {"before_1984": 285, "1984-2000": 285, "after_2000": 285},
        },
        "auxiliary_engine": {
            "HFO": {"before_1984": 225, "1984-2000": 205, "after_2000": 195},
            "MDO": {"before_1984": 210, "1984-2000": 190, "after_2000": 185},
            "LNG": {"after_2000": 156},
        },
    }

    # Verify
    engine_types = ["steam_boiler", "auxiliary_engine"]
    engine_types.extend(ENGINE_TYPES)
    verify_set(
        "engine_type",
        engine_type,
        engine_types,
    )
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    verify_set("engine_age", engine_age, ENGINE_AGES)
    verify_range("engine_load", engine_load, 0, 1.0)

    try:
        sfc_baseline = sfc_baselines[engine_type][fuel_type][engine_age]
    except KeyError as err:
        raise ValueError(
            f"""No specific fuel consumption baseline found for {engine_type},
              {fuel_type}, {engine_age}"""
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


def estimate_auxiliary_power_demand(vessel_data, operation_mode):
    """
    Estimate the auxiliary power demand.

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

        Tuple( aux_engine_power, boiler_power) in kW.

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.

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
        "ferry-pax": [0, 300, 1_000, 2_000],
        "cruise": [0, 2_000, 10_000, 60_000, 100_000, 150_000],
        "ferry-ropax": [0, 2_000, 5_000, 10_000, 20_000],
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
        "ferry-pax": [
            [0, 0, 0, 0, 190, 190, 190, 190],
            [0, 0, 0, 0, 190, 190, 190, 190],
            [0, 0, 0, 0, 190, 190, 190, 190],
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
        "ferry-ropax": [
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
    installed_propulsion_power = calculate_installed_propulsion_power(vessel_data)

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

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.

    """
    # Verify arguments
    verify_range("speed", speed, 0, vessel_data["design_speed"] * 1.5)
    verify_range(
        "draft",
        draft,
        vessel_data["design_draft"] * 0.5,
        vessel_data["design_draft"] * 1.5,
    )
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
        "ferry-ropax",
        "ferry-pax",
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
    load = (
        delta_w
        * ((draft / design_draft) ** (2 / 3) * (speed / design_speed) ** 3)
        / (eta_f * eta_w)
    )

    # Load cannot exceed 100%
    return min(1.0, load)


def calculate_installed_propulsion_power(vessel_data):
    """Calculate the installed propulsion power of a vessel

    Arguments:
    ----------

        vessel_data: dict
            Dictionary describing the vessel.

    Returns:
    --------

        float
            Installed propulsion power (kW)
    """
    installed_propulsion_power = (
        vessel_data["number_of_propulsion_engines"]
        * vessel_data["propulsion_engine_power"]
    )
    if vessel_data["double_ended"]:
        installed_propulsion_power /= 2
    return installed_propulsion_power


def estimate_instantaneous_fuel_consumption_of_auxiliary_systems(
    vessel_data, operation_mode
):
    """Estimate the instantanous fuel consumption of the auxiliary systems:
    auxiliary engines and steam boilers.

    Assumption: The fuel type and age of the steam boilers and auxiliary engines
    is assumed to be the same as the one of the propulsion engine(s)

    Arguments:
    ----------

    vessel_data: dict
        Dictionary containing the vessel data.

    operation_mode: string
        One of the following operation modes:
            - 'at_berth'
            - 'anchored'
            - 'manoeuvring'
            - 'at_sea

    Returns:
    --------

        Tuple
            (Instantanous fuel consumption of the auxiliary engines (kg/h),
             Instantanous fuel consumption of the steam boilers (kg/h))


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

    ifc_aux_engine = aux_engine_power * aux_engine_sfc
    ifc_boiler = boiler_power * boiler_sfc

    return ifc_aux_engine, ifc_boiler


def estimate_propulsion_power_demand(vessel_data, speed, draft, delta_w):
    """Estimate the propulsion power demand

    Arguments:
    ----------

        vessel_data: dict
            Dictionary describing the vessel.

        speed: float
            Speed over ground (m/s).

        draft: float
            Dynamic draft (m).

        delta_w (optional): float
            Speed-power correction factor: percentage of the Maximum Continous Rating
            (MCR) of the installed propulsion power at which the design speed is reached
            in calm water. Defaults to the considerations in [1] to be equal to 0.75 for
            container ships over 14,500 TEU, 0.7 for cruise ships, and 1.0 for all other
            vessels (i.e. 75%, 70%, and 100% MCR, respectively). If given a value, the
            value will override these defaults. Defaults to None.

        Returns:
        --------

            float
                Instantanous power of the propulsion engines (kW).

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.

    """

    installed_propulsion_power = calculate_installed_propulsion_power(vessel_data)

    load = estimate_propulsion_engine_load(speed, draft, vessel_data, delta_w=delta_w)

    return installed_propulsion_power * load


def estimate_instantanous_fuel_consumption_of_propulsion_engines(
    vessel_data, speed, draft, limit_7_percent=True, delta_w=None
):
    """Estimate the instantanous fuel consumption of the propulsion engines

    Arguments:
    ----------

        vessel_data: dict
            Dictionary describing the vessel.

        speed: float
            Speed over ground (m/s).

        draft: float
            Dynamic draft (m).

        limit_7_percent (optional): boolean
            If True, when the engine load is less than 7% the fuel consumption is
            neglected (i.e. 0.0). Defaults to True.

        delta_w (optional): float
            Speed-power correction factor: percentage of the Maximum Continous Rating
            (MCR) of the installed propulsion power at which the design speed is reached
            in calm water. Defaults to the considerations in [1] to be equal to 0.75 for
            container ships over 14,500 TEU, 0.7 for cruise ships, and 1.0 for all other
            vessels (i.e. 75%, 70%, and 100% MCR, respectively). If given a value,
            the value will override these defaults. Defaults to None.

        Returns:
        --------

            float
                Instantanous fuel consumption (kg/h).

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.

    """

    installed_propulsion_power = calculate_installed_propulsion_power(vessel_data)

    fuel_type = vessel_data["propulsion_engine_fuel_type"]
    engine_age = vessel_data["propulsion_engine_age"]
    engine_type = vessel_data["propulsion_engine_type"]

    load = estimate_propulsion_engine_load(speed, draft, vessel_data, delta_w=delta_w)
    if load < 0.07 and limit_7_percent:
        sfc = 0.0
    else:
        sfc = estimate_specific_fuel_consumption(
            load, engine_type, fuel_type, engine_age
        )
    return installed_propulsion_power * load * sfc


def estimate_fuel_consumption_of_propulsion_engines(
    vessel_data, voyage_profile, limit_7_percent=True, delta_w=None
):
    """
    Arguments:
    ----------

        vessel_data: dict

        voyage_profile: dict

    Returns:
    --------
        (float, float)
            Fuel consumption (kg) and averege fuel consumption (L/nm).

    """
    total_fc_kg = 0.0
    total_distance_nm = 0.0
    legs = voyage_profile["legs_at_sea"] + voyage_profile["legs_manoeuvring"]
    for distance, speed, draft in legs:
        ifc = estimate_instantanous_fuel_consumption_of_propulsion_engines(
            vessel_data,
            speed,
            draft,
            limit_7_percent=limit_7_percent,
            delta_w=delta_w,
        )
        time_h = distance / speed
        total_distance_nm += distance
        total_fc_kg += ifc * time_h

    avg_fc_lpnm = (
        calculate_fuel_volume(total_fc_kg, vessel_data["propulsion_engine_fuel_type"])
        * 1_000
        / total_distance_nm
    )
    return total_fc_kg, avg_fc_lpnm


def estimate_fuel_consumption(
    vessel_data,
    voyage_profile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate the fuel consumption of a vessel

    Arguments:
    ----------

        vessel_data: dict
            Dictionary describing the vessel.

        voyage_profile: dict
            Dictionary describing the voyage profile.

        include_steam_boilers (optional): boolean
            If True, the fuel consumption of the steam boilers is included in the
            calculation. Defaults to True.

        limit_7_percent (optional): boolean
            If True, when the engine load is less than 7% the fuel consumption is
            neglected (i.e. 0.0). Defaults to True.

        delta_w (optional): float
            Speed-power correction factor: percentage of the Maximum Continous Rating
            (MCR) of the installed propulsion power at which the design speed is reached
            in calm water. Defaults to the considerations in [1] to be equal to 0.75 for
            container ships over 14,500 TEU, 0.7 for cruise ships, and 1.0 for all other
            vessels (i.e. 75%, 70%, and 100% MCR, respectively). If given a value,
            the value will override these defaults. Defaults to None.

    Returns:
    --------

        Dict
            Total fuel consumed (kg) and breakdown according to the voyage profile.

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.

    """

    def _estimate_sailing_fuel_consumption(legs, operation_mode):
        if len(legs) == 0:
            fc_ = {
                "subtotal_kg": 0.0,
                "auxiliary_engines_kg": 0.0,
                "propulsion_engines_kg": 0.0,
                "average_fuel_consumption_l_per_nm": 0.0,
            }
            if include_steam_boilers:
                fc_["steam_boilers_kg"] = 0.0
            return fc_

        total_time = sum([distance / speed for distance, speed, _ in legs])

        # FC of auxiliary systems
        (
            ifc_aux_engine,
            ifc_boiler,
        ) = estimate_instantaneous_fuel_consumption_of_auxiliary_systems(
            vessel_data, operation_mode
        )
        fc_aux_engine = ifc_aux_engine * total_time
        fc_boiler = ifc_boiler * total_time

        # FC of propulsion engines
        fc_prop = 0.0
        total_dist = 0.0
        for distance, speed, draft in legs:
            ifc_prop = estimate_instantanous_fuel_consumption_of_propulsion_engines(
                vessel_data,
                speed,
                draft,
                limit_7_percent=limit_7_percent,
                delta_w=delta_w,
            )
            time = distance / speed
            total_dist += distance
            fc_prop += ifc_prop * time

        if include_steam_boilers:
            fc_subtotal = fc_aux_engine + fc_boiler + fc_prop
            return {
                "subtotal_kg": fc_subtotal,
                "auxiliary_engines_kg": fc_aux_engine,
                "steam_boilers_kg": fc_boiler,
                "propulsion_engines_kg": fc_prop,
                "average_fuel_consumption_l_per_nm": calculate_fuel_volume(
                    fc_subtotal, vessel_data["propulsion_engine_fuel_type"]
                )
                * 1_000
                / total_dist,
            }

        fc_subtotal = fc_aux_engine + fc_prop
        return {
            "subtotal_kg": fc_subtotal,
            "auxiliary_engines_kg": fc_aux_engine,
            "propulsion_engines_kg": fc_prop,
            "average_fuel_consumption_l_per_nm": calculate_fuel_volume(
                fc_subtotal, vessel_data["propulsion_engine_fuel_type"]
            )
            * 1_000
            / total_dist,
        }

    # At berth
    ifc_aux, ifc_boiler = estimate_instantaneous_fuel_consumption_of_auxiliary_systems(
        vessel_data, "at_berth"
    )
    fc_aux_at_berth = ifc_aux * voyage_profile["time_at_berth"]
    fc_boiler_at_berth = ifc_boiler * voyage_profile["time_at_berth"]

    if include_steam_boilers:
        fc_at_berth = {
            "subtotal_kg": fc_aux_at_berth + fc_boiler_at_berth,
            "auxiliary_engines_kg": fc_aux_at_berth,
            "steam_boilers_kg": fc_boiler_at_berth,
        }
    else:
        fc_at_berth = {
            "subtotal_kg": fc_aux_at_berth,
            "auxiliary_engines_kg": fc_aux_at_berth,
        }

    # Anchored
    ifc_aux, ifc_boiler = estimate_instantaneous_fuel_consumption_of_auxiliary_systems(
        vessel_data, "anchored"
    )
    fc_aux_anchored = ifc_aux * voyage_profile["time_anchored"]
    fc_boiler_anchored = ifc_boiler * voyage_profile["time_anchored"]
    if include_steam_boilers:
        fc_anchored = {
            "subtotal_kg": fc_aux_anchored + fc_boiler_anchored,
            "auxiliary_engines_kg": fc_aux_anchored,
            "steam_boilers_kg": fc_boiler_anchored,
        }
    else:
        fc_anchored = {
            "subtotal_kg": fc_aux_anchored,
            "auxiliary_engines_kg": fc_aux_anchored,
        }

    # Manoeuvring
    fc_manoeuvring = _estimate_sailing_fuel_consumption(
        voyage_profile["legs_manoeuvring"], "manoeuvring"
    )

    # At sea
    fc_at_sea = _estimate_sailing_fuel_consumption(
        voyage_profile["legs_at_sea"], "at_sea"
    )

    return {
        "total_kg": fc_at_berth["subtotal_kg"]
        + fc_anchored["subtotal_kg"]
        + fc_manoeuvring["subtotal_kg"]
        + fc_at_sea["subtotal_kg"],
        "at_berth": fc_at_berth,
        "anchored": fc_anchored,
        "manoeuvring": fc_manoeuvring,
        "at_sea": fc_at_sea,
    }


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
    installed_propulsion_power = calculate_installed_propulsion_power(vessel_data)

    def _estimate_sailing_energy(legs, operation_mode):
        if len(legs) == 0:
            en_ = {
                "subtotal_kwh": 0.0,
                "auxiliary_engines_kwh": 0.0,
                "propulsion_engines_kwh": 0.0,
                "average_energy_consumption_kwh_per_nm": 0.0,
                "maximum_required_total_power_kw": 0.0,
                "maximum_required_propulsion_power_kw": 0.0,
            }
            if include_steam_boilers:
                en_["steam_boilers_kwh"] = 0.0
            return en_

        total_time = sum([distance / speed for distance, speed, _ in legs])
        (
            power_auxiliary_engines,
            power_steam_boilers,
        ) = estimate_auxiliary_power_demand(vessel_data, operation_mode)
        energy_auxiliary_engines = power_auxiliary_engines * total_time
        energy_steam_boilers = power_steam_boilers * total_time
        energy_prop = []
        power_prop = []
        load_prop = []
        total_dist = 0.0
        for distance, speed, draft in legs:
            total_dist += distance
            load = estimate_propulsion_engine_load(
                speed, draft, vessel_data, delta_w=delta_w
            )
            load_prop.append(load)
            if load < 0.07 and limit_7_percent:
                energy_prop.append(0.0)
                power_prop.append(0.0)
            else:
                time = distance / speed
                energy_prop.append(installed_propulsion_power * load * time)
                power_prop.append(installed_propulsion_power * load)

        if include_steam_boilers:
            energy_subtotal = (
                energy_auxiliary_engines + energy_steam_boilers + sum(energy_prop)
            )
            power_max = power_auxiliary_engines + power_steam_boilers + max(power_prop)
            return {
                "subtotal_kwh": energy_subtotal,
                "auxiliary_engines_kwh": energy_auxiliary_engines,
                "steam_boilers_kwh": energy_steam_boilers,
                "average_energy_consumption_kwh_per_nm": energy_subtotal / total_dist,
                "maximum_required_total_power_kw": power_max,
                "maxium_engine_load_percent": max(load_prop) * 100,
                "maximum_required_propulsion_power_kw": max(power_prop),
            }

        energy_subtotal = energy_auxiliary_engines + sum(energy_prop)
        power_max = power_auxiliary_engines + max(power_prop)
        return {
            "subtotal_kwh": energy_subtotal,
            "auxiliary_engines_kwh": energy_auxiliary_engines,
            "average_energy_consumption_kwh_per_nm": energy_subtotal / total_dist,
            "maximum_required_total_power_kw": power_max,
            "maxium_engine_load_percent": max(load_prop) * 100,
            "maximum_required_propulsion_power_kw": max(power_prop),
        }

    # At berth
    (
        power_auxiliary_engines_at_berth,
        power_steam_boilers_at_berth,
    ) = estimate_auxiliary_power_demand(vessel_data, "at_berth")
    energy_auxiliary_engines_at_berth = (
        power_auxiliary_engines_at_berth * voyage_profile["time_at_berth"]
    )
    energy_steam_boilers_at_berth = (
        power_steam_boilers_at_berth * voyage_profile["time_at_berth"]
    )
    if include_steam_boilers:
        energy_at_berth = {
            "subtotal_kwh": energy_auxiliary_engines_at_berth
            + energy_steam_boilers_at_berth,
            "auxiliary_engines_kwh": energy_auxiliary_engines_at_berth,
            "steam_boilers_kwh": energy_steam_boilers_at_berth,
            "maximum_required_total_power_kw": 0.0
            if voyage_profile["time_at_berth"] == 0
            else power_auxiliary_engines_at_berth + power_steam_boilers_at_berth,
        }
    else:
        energy_at_berth = {
            "subtotal_kwh": energy_auxiliary_engines_at_berth,
            "auxiliary_engines_kwh": energy_auxiliary_engines_at_berth,
            "maximum_required_total_power_kw": 0.0
            if voyage_profile["time_at_berth"] == 0
            else power_auxiliary_engines_at_berth,
        }

    # Anchored
    (
        power_auxiliary_engines_anchored,
        power_steam_boilers_anchored,
    ) = estimate_auxiliary_power_demand(vessel_data, "anchored")
    energy_auxiliary_engines_anchored = (
        power_auxiliary_engines_anchored * voyage_profile["time_anchored"]
    )
    energy_steam_boilers_anchored = (
        power_steam_boilers_anchored * voyage_profile["time_anchored"]
    )
    if include_steam_boilers:
        energy_anchored = {
            "subtotal_kwh": energy_auxiliary_engines_anchored
            + energy_steam_boilers_anchored,
            "auxiliary_engines_kwh": energy_auxiliary_engines_anchored,
            "steam_boilers_kwh": energy_steam_boilers_anchored,
            "maximum_required_total_power_kw": 0.0
            if voyage_profile["time_anchored"] == 0
            else power_auxiliary_engines_anchored + power_steam_boilers_anchored,
        }
    else:
        energy_anchored = {
            "subtotal_kwh": energy_auxiliary_engines_anchored,
            "auxiliary_engines_kwh": energy_auxiliary_engines_anchored,
            "maximum_required_total_power_kw": 0.0
            if voyage_profile["time_anchored"] == 0
            else power_auxiliary_engines_anchored,
        }

    # Manoeuvring
    energy_manoeuvring = _estimate_sailing_energy(
        voyage_profile["legs_manoeuvring"], "manoeuvring"
    )

    # At sea
    energy_at_sea = _estimate_sailing_energy(voyage_profile["legs_at_sea"], "at_sea")

    return {
        "total_kwh": energy_at_berth["subtotal_kwh"]
        + energy_anchored["subtotal_kwh"]
        + energy_manoeuvring["subtotal_kwh"]
        + energy_at_sea["subtotal_kwh"],
        "maximum_required_total_power_kw": max(
            [
                energy_at_berth["maximum_required_total_power_kw"],
                energy_anchored["maximum_required_total_power_kw"],
                energy_manoeuvring["maximum_required_total_power_kw"],
                energy_at_sea["maximum_required_total_power_kw"],
            ]
        ),
        "maximum_required_propulsion_power_kw": max(
            [
                energy_manoeuvring["maximum_required_propulsion_power_kw"],
                energy_at_sea["maximum_required_propulsion_power_kw"],
            ]
        ),
        "at_berth": energy_at_berth,
        "anchored": energy_anchored,
        "manoeuvring": energy_manoeuvring,
        "at_sea": energy_at_sea,
    }
