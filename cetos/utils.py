"""
Utilities
"""

# Mirrors cetos.models.FUEL_TYPES; inlined to avoid a utils -> models import cycle.
_FUEL_TYPES = ["HFO", "MDO", "MeOH", "LNG"]


def knots_to_ms(speed):
    """Transform speed in knots to m/s"""
    return speed * 1852 / 3600


def ms_to_knots(speed):
    """Transform speed in ms to knots"""
    return speed * 3600 / 1852


def verify_range(name, value, lower_limit, upper_limit):
    """Verify that an argument has a value within a specified range."""
    if value < lower_limit or value > upper_limit:
        raise ValueError(
            f"The value of {value} for the argument '{name}' is not within the \
                 range [{lower_limit},{upper_limit}]."
        )


def verify_set(name, value, set_):
    """Verify that an argument has a value within a specified set."""
    if value not in set_:
        raise ValueError(
            f"The value of '{value}' for the argument '{name}' is not in the set {set_}."
        )


def verify_key_value_type(dict_name, key, dict_, type_):
    """Verify that the value of a key is the correct type"""
    if not isinstance(dict_[key], type_):
        type_print = str(type_).split("'")[1]
        raise ValueError(
            f"The value The value '{dict_[key]}' for the key '{key}', in the variable '{dict_name}', should be of type '{type_print}'"
        )


def verify_key_value_range(dict_name, key, dict_, lower_limit, upper_limit):
    """Verify that a key has a value within a specified range."""
    if dict_[key] < lower_limit or dict_[key] > upper_limit:
        raise ValueError(
            f"The value '{dict_[key]}' for the key '{key}', in the variable '{dict_name}', is not within the \
                 range [{lower_limit},{upper_limit}]."
        )


def verify_key_value_set(dict_name, key, dict_, set_):
    """Verify that a key has a value within a specified set."""
    if dict_[key] not in set_:
        raise ValueError(
            f"The value '{dict_[key]}' for the key '{key}', in the variable '{dict_name}', is not not in the set {set_}."
        )


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
        Table 10 in page 294 of IMO Fourth IMO GHG Study 2020.
    """
    verify_set("fuel_type", fuel_type, _FUEL_TYPES)
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
    verify_set("fuel_type", fuel_type, _FUEL_TYPES)
    if fuel_type == "HFO":
        return volume * 1001
    if fuel_type == "MDO":
        return volume * 895
    if fuel_type == "LNG":
        return volume * 450
    return volume * 790


def calculate_installed_propulsion_power(vessel_data):
    """Calculate the installed propulsion power of a vessel

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

    Returns:
    --------

        float
            Installed propulsion power (kW)
    """
    installed_propulsion_power = (
        vessel_data.number_of_propulsion_engines
        * vessel_data.propulsion_engine_power_kw
    )
    if vessel_data.double_ended:
        installed_propulsion_power /= 2
    return installed_propulsion_power
