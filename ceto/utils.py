"""
Utilities
"""
import numpy as np
from geopy.distance import geodesic

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

def frechet_distance(P, Q):
    """
    Computes the Frechet distance between two trajectories P and Q.
    """
    n = len(P)
    m = len(Q)

    if n == 0 or m == 0:
        return np.inf

    ca = np.zeros((n, m))
    ca[0, 0] = geodesic(P[0], Q[0]).km

    for i in range(1, n):
        ca[i, 0] = max(ca[i-1, 0], geodesic(P[i], Q[0]).km)

    for j in range(1, m):
        ca[0, j] = max(ca[0, j-1], geodesic(P[0], Q[j]).km)

    for i in range(1, n):
        for j in range(1, m):
            ca[i, j] = max(
                min(ca[i-1, j], ca[i-1, j-1], ca[i, j-1]),
                geodesic(P[i], Q[j]).km
            )

    return ca[n-1, m-1]


def douglas_peucker(points, epsilon):
    """
    Simplifies a trajectory by reducing the number of points using the Douglas-Peucker algorithm.
    """
    dmax = 0
    index = 0

    for i in range(1, len(points)-1):
        d = frechet_distance([points[0], points[-1]], [points[0], points[i]])
        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        results1 = douglas_peucker(points[:index+1], epsilon)
        results2 = douglas_peucker(points[index:], epsilon)[1:]
        return np.vstack((results1, results2))
    else:
        return np.array([points[0], points[-1]])
