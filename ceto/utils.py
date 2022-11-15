"""
Utilities
"""


def knots_to_ms(speed):
    """Transform speed in knots to m/s"""
    return speed * 1.94384


def ms_to_knots(speed):
    """Transform speed in ms to knots"""
    return speed / 1.94384


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
