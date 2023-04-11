from typing import List, Tuple
from geopy.distance import geodesic
import numpy as np

import math 

R = 6371000 # Earth's radius in meters

def haversine(coord1, coord2):
    """
    Calculate the great-circle distance between two points on the Earth using the haversine formula.

    Parameters:
    coord1 (tuple): A tuple containing the latitude and longitude of the first point (in decimal degrees)
    coord2 (tuple): A tuple containing the latitude and longitude of the second point (in decimal degrees)

    Returns:
    float: The great-circle distance between the two points in kilometers
    """

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (math.sin(dlat / 2) ** 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def bearing(coord1, coord2):
    """
    Calculate the initial bearing from one point to another on the Earth's surface.

    Parameters:
    coord1 (tuple): A tuple containing the latitude and longitude of the first point (in decimal degrees)
    coord2 (tuple): A tuple containing the latitude and longitude of the second point (in decimal degrees)

    Returns:
    float: The initial bearing from the first point to the second point in degrees (0-360)
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

    initial_bearing_rad = math.atan2(y, x)
   
    # Convert radians to degrees and normalize the result to the range [0, 360)
    initial_bearing_deg = (math.degrees(initial_bearing_rad) + 360) % 360

    return initial_bearing_deg

def cross_track_distance(coord1, coord2, coord3):
    """
    Calculate the cross-track distance between a point and a path on the surface of the Earth.

    Parameters:
    coord1 (tuple): A tuple containing the latitude and longitude of the starting point of the path (in decimal degrees)
    coord2 (tuple): A tuple containing the latitude and longitude of the ending point of the path (in decimal degrees)
    coord3 (tuple): A tuple containing the latitude and longitude of the point to calculate cross-track distance for (in decimal degrees)

    Returns:
    float: The cross-track distance between the point and the path in kilometers
    """

    d13 = haversine(coord1, coord3) / R
    bearing13 = math.radians(bearing(coord1, coord2))
    bearing12 = math.radians(bearing(coord1, coord3))

    return math.asin(math.sin(d13) * math.sin(bearing13 - bearing12)) * R

def douglas_peucker_old(points, epsilon):
    """
    Simplify a trajectory using the Douglas-Peucker algorithm with cross-track distance.

    Parameters:
    points (list): A list of tuples containing the latitude and longitude of the points in the trajectory (in decimal degrees)
    epsilon (float): The tolerance value used to determine if a point should be kept in the simplified trajectory (in meters)

    Returns:
    list: A list of tuples containing the simplified trajectory points
    """
    def find_furthest_point_index(points, start, end):
        max_dist = -1
        max_index = -1

        for i in range(start + 1, end):
            dist = abs(cross_track_distance(points[start], points[end], points[i]))
            if dist > max_dist:
                max_dist = dist
                max_index = i

        return max_index, max_dist

    def dp_recursive(points, start, end, epsilon, result):
        index, dist = find_furthest_point_index(points, start, end)

        if dist > epsilon:
            dp_recursive(points, start, index, epsilon, result)
            result.append(points[index])
            dp_recursive(points, index, end, epsilon, result)

    if len(points) < 2:
        raise ValueError("Trajectory must contain at least 2 points")

    start = 0
    end = len(points) - 1
    result = [points[start]]

    dp_recursive(points, start, end, epsilon, result)

    result.append(points[end])

    return result

def douglas_peucker(points, epsilon):
    dist_max = 0
    index = 0
    for i in range(1, len(points) - 1):
        dist = abs(cross_track_distance(points[0], points[-1], points[i]))
        if dist > dist_max:
            index = i
            dist_max = dist
    

    if dist_max > epsilon:
        rec_results_1 = douglas_peucker(points[:index+1], epsilon)
        rec_results_2 = douglas_peucker(points[index:], epsilon)
        results = rec_results_1[:-1] + rec_results_2
    else:
        results = [points[0],points[-1]]
    return results

def frechet_distance(path1, path2):
    """
    Calculate the discrete Fréchet distance between two paths using cross-track distance.

    Parameters:
    path1 (list): A list of tuples containing the latitude and longitude of the points in the first path (in decimal degrees)
    path2 (list): A list of tuples containing the latitude and longitude of the points in the second path (in decimal degrees)

    Returns:
    float: The discrete Fréchet distance between the two paths
    """
    len_path1 = len(path1)
    len_path2 = len(path2)

    if len_path1 == 0 or len_path2 == 0:
        raise ValueError("Paths must not be empty")

    memo = np.full((len_path1, len_path2), -1.0)

    def recursive_frechet(i, j):
        if memo[i][j] != -1.0:
            return memo[i][j]

        if i == 0 and j == 0:
            memo[i][j] = haversine(path1[0], path2[0])
        elif i > 0 and j == 0:
            memo[i][j] = max(recursive_frechet(i - 1, 0), haversine(path1[i], path2[0]))
        elif i == 0 and j > 0:
            memo[i][j] = max(recursive_frechet(0, j - 1), haversine(path1[0], path2[j]))
        elif i > 0 and j > 0:
            memo[i][j] = max(min(recursive_frechet(i - 1, j), recursive_frechet(i - 1, j - 1), recursive_frechet(i, j - 1)),
                            haversine(path1[i], path2[j]))
        else:
            memo[i][j] = float('inf')
        return memo[i][j]

    return recursive_frechet(len_path1 - 1, len_path2 - 1)