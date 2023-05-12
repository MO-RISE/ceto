from typing import List, Tuple
from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
import numpy as np


import math

R = 6371000  # Earth's radius in meters


def haversine(point_1, point_2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.

    Parameters:
    point_1 (tuple): A tuple containing the latitude and longitude of the first point (in decimal degrees)
    point_2 (tuple): A tuple containing the latitude and longitude of the second point (in decimal degrees)

    Returns:
    float: The great-circle distance between the two points in kilometers
    """

    lat1, lon1 = point_1
    lat2, lon2 = point_2

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (math.sin(dlat / 2) ** 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * (
        math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def bearing(point_1, point_2):
    """
    Calculate the initial bearing from one point to another on the Earth's surface.

    Parameters:
    point_1 (tuple): A tuple containing the latitude and longitude of the first point (in decimal degrees)
    point_2 (tuple): A tuple containing the latitude and longitude of the second point (in decimal degrees)

    Returns:
    float: The initial bearing from the first point to the second point in degrees (0-360)
    """
    lat1, lon1 = point_1
    lat2, lon2 = point_2

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
        lat2_rad
    ) * math.cos(dlon)

    initial_bearing_rad = math.atan2(y, x)

    # Convert radians to degrees and normalize the result to the range [0, 360)
    initial_bearing_deg = (math.degrees(initial_bearing_rad) + 360) % 360

    return initial_bearing_deg


def cross_track_distance(start_point, end_point, point):
    """
    Calculate the cross-track distance between a point and a rhumb line on the surface of the Earth.

    Parameters:
    start_point (tuple): A tuple containing the latitude and longitude of the starting point of the rhumb line (in decimal degrees)
    end_point (tuple): A tuple containing the latitude and longitude of the ending point of the rhumb line (in decimal degrees)
    point (tuple): A tuple containing the latitude and longitude of the point to calculate cross-track distance for (in decimal degrees)

    Returns:
    float: The cross-track distance between the point and the rhumb line in kilometers
    """

    d13 = haversine(start_point, point) / R
    bearing13 = math.radians(bearing(start_point, end_point))
    bearing12 = math.radians(bearing(start_point, point))

    return math.asin(math.sin(d13) * math.sin(bearing13 - bearing12)) * R


def douglas_peucker(path, epsilon):
    """
    Simplify a path using the Douglas-Peucker algorithm with cross-track distance.

    Parameters:
    path (list): A list of tuples containing the latitude and longitude of the path in the trajectory (in decimal degrees)
    epsilon (float): The tolerance value used to determine if a point should be kept in the simplified trajectory (in meters)

    Returns:
    list: A list of tuples containing the simplified trajectory path
    """
    dist_max = 0
    index = 0
    for i in range(1, len(path) - 1):
        dist = abs(cross_track_distance(path[0], path[-1], path[i]))
        if dist > dist_max:
            index = i
            dist_max = dist

    if dist_max > epsilon:
        rec_results_1 = douglas_peucker(path[: index + 1], epsilon)
        rec_results_2 = douglas_peucker(path[index:], epsilon)
        results = rec_results_1[:-1] + rec_results_2
    else:
        results = [path[0], path[-1]]
    return results


def frechet_distance(path_1, path_2):
    """
    Calculate the discrete Fréchet distance between two paths using cross-track distance.

    Parameters:
    path_1 (list): A list of tuples containing the latitude and longitude of the points in the first path (in decimal degrees)
    path_2 (list): A list of tuples containing the latitude and longitude of the points in the second path (in decimal degrees)

    Returns:
    float: The discrete Fréchet distance between the two paths
    """
    len_path_1 = len(path_1)
    len_path_2 = len(path_2)

    if len_path_1 == 0 or len_path_2 == 0:
        raise ValueError("Paths must not be empty")

    memo = np.full((len_path_1, len_path_2), -1.0)

    def recursive_frechet(i, j):
        if memo[i][j] != -1.0:
            return memo[i][j]

        if i == 0 and j == 0:
            memo[i][j] = haversine(path_1[0], path_2[0])
        elif i > 0 and j == 0:
            memo[i][j] = max(
                recursive_frechet(i - 1, 0), haversine(path_1[i], path_2[0])
            )
        elif i == 0 and j > 0:
            memo[i][j] = max(
                recursive_frechet(0, j - 1), haversine(path_1[0], path_2[j])
            )
        elif i > 0 and j > 0:
            memo[i][j] = max(
                min(
                    recursive_frechet(i - 1, j),
                    recursive_frechet(i - 1, j - 1),
                    recursive_frechet(i, j - 1),
                ),
                haversine(path_1[i], path_2[j]),
            )
        else:
            memo[i][j] = float("inf")
        return memo[i][j]

    return recursive_frechet(len_path_1 - 1, len_path_2 - 1)


def cluster_paths(
    paths: List[List[Tuple[float, float]]],
    alpha: float = 0.3,
    eps: float = 100,
    min_samples: int = 2,
    epsilon: float = 10,
) -> List[int]:
    """
    Cluster paths based on their Fréchet distance and direction similarity.

    Arguments:
        paths: A list of paths, where each path is a list of (x, y) coordinate tuples.
        alpha: The weight of the angular difference in the distance calculation, ranging from 0 to 1.
        eps: The maximum distance between two samples for them to be considered as in the same cluster.
        min_samples: The number of samples in a neighborhood for a point to be considered as a core point.
        epsilon: The threshold cross-track distance used to determine if a point should be kept in path simplification step (Douglas-Peucker algorithm).

    Returns:
        A list of cluster labels for each path. Noise points are given the label -1.
    """

    # Simplify the paths
    simplified_paths = [douglas_peucker(path, epsilon) for path in paths]

    # Compute path directions
    path_directions = [
        np.arctan2(path[-1][1] - path[0][1], path[-1][0] - path[0][0])
        for path in simplified_paths
    ]

    # Compute pairwise distances between all pairs of trajectories using the Fréchet distance
    distance_matrix = np.zeros([len(simplified_paths), len(simplified_paths)])
    for i, i_path in enumerate(simplified_paths):
        for j, j_path in enumerate(simplified_paths):
            if i == j:
                distance_matrix[i, j] = 0
            else:
                fr_dist = frechet_distance(i_path, j_path)
                angular_diff = angular_diff = np.abs(
                    path_directions[i] - path_directions[j]
                )
                distance_matrix[i, j] = (1 - alpha) * fr_dist + alpha * angular_diff

    # Apply DBSCAN clustering to group similar trajectories together
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="precomputed")
    labels = clustering.fit_predict(distance_matrix)

    return labels


def generate_representative_path(
    paths: List[List[Tuple[float, float]]], epsilon: float = 10
) -> List[Tuple[float, float]]:
    """Generate representative path

    Generates a path representative of a group of similar paths by
    simplyfing each of the given paths then clustering the points
    of the simplified paths. The simplification is done with the
    Douglas-Peucker algorithm and the clustering with Agglomerative
    Clustering.

    Arguments:
    ----------

        paths: list
            List of similar paths where a path is list of (lat, lon) tuples.

        epsilon: float
            The threshold cross-track distance used to determine if
            a point should be kept in path simplification step
            (Douglas-Peucker algorithm).

    Returns:
    --------

        list
            The representative path as a list of (lat, lon) tuples.

    """
    # Find the representative waypoints.
    s_paths = [douglas_peucker(path, epsilon) for path in paths]
    n_waypoints = (
        int(np.ceil(sum([len(s_path) for s_path in s_paths]) / len(s_paths))) + 1
    )
    agglomerative_clustering = AgglomerativeClustering(n_clusters=n_waypoints)

    # Add the index as a third element in the input points for the Agglomerative Clustering algorithm
    points = np.array(
        [
            (point[0], point[1], index)
            for sublist in s_paths
            for index, point in enumerate(sublist)
        ]
    )
    points_np = np.array(points)[
        :, :2
    ]  # Exclude the index from the numpy array for clustering
    agglomerative_clustering.fit(points_np)

    # Calculate cluster centers
    cluster_centers = []
    ref = np.array([(p[0], p[1]) for p in paths[0]])
    for cluster_id in np.unique(agglomerative_clustering.labels_):
        cluster_points = points[agglomerative_clustering.labels_ == cluster_id]
        cluster_center = cluster_points[:, :2].mean(axis=0)
        closest_point_idx = np.argmin(np.linalg.norm(ref - cluster_center, axis=1))
        cluster_centers.append(
            (cluster_center[0], cluster_center[1], closest_point_idx)
        )

    # Sort the cluster centers based on the third element (the index)
    ordered_cluster_centers = sorted(cluster_centers, key=lambda x: x[2])

    # Remove the index from the final output
    ordered_cluster_centers = [(p[0], p[1]) for p in ordered_cluster_centers]

    return ordered_cluster_centers


def generate_representative_route(trajectories, epsilon: float = 10):
    """Generate a represenative route

    Generates a route represenative of a group of trajectories by:
    1) Generating a path representive of the paths of all the trajectories by
       simplyfing the paths and clustering their points.
    2) Approximating the time at each leg of the representativ path.
    3) Calculating the speed at each leg from the time at each leg and the
       leg distances.

    Arguments:
    ----------

        trajectories: list
            List of trajectories, where a trajectory is a dict containing the following
            key-value pairs:
                - 'path': List of (lat, lon) tuples.
                - 'timestamp': List of Unix timestamps in seconds.

        epsilon: float
            The threshold cross-track distance used to determine if
            a point should be kept in path simplification step
            (Douglas-Peucker algorithm).

    Returns:
    --------

        dict
            Dictionary representing a route and containing the following key-value
            pairs:
                - 'path': List of (lat, lon) tuples.
                - 'speed': List of speeds for each leg (kn).
                - 'time': List of time spent at each leg (h).
                - 'distance': List of distances for each leg (nm).

    """

    def _find_index_of_closest_point(path, point):
        index = 0
        max_dist = 1e6
        for i, p in enumerate(path):
            dist = haversine(p, point)
            if dist < max_dist:
                max_dist = dist
                index = i
        return index

    # Generate a path representative of all the paths
    r_path = generate_representative_path(
        [trajectory["path"] for trajectory in trajectories], epsilon
    )

    leg_times_h = [0] * (len(r_path) - 1)
    for trajectory in trajectories:
        # Find the indexes closest to the points in the representative path
        indexes = [
            _find_index_of_closest_point(trajectory["path"], rp) for rp in r_path
        ]

        for i in range(len(indexes)):
            if i > 0:
                leg_times_h[i - 1] += (
                    trajectory["timestamp"][indexes[i]]
                    - trajectory["timestamp"][indexes[i - 1]]
                ) / 3_600

    avg_leg_times_h = [leg_time / len(trajectories) for leg_time in leg_times_h]

    # Calculate leg distances
    leg_distances_nm = []
    for i in range(len(r_path)):
        if i > 0:
            leg_distances_nm.append(haversine(r_path[i], r_path[i - 1]) / 1_852)

    # Calculate the average leg speeds
    avg_leg_speeds_kn = [
        ((leg_distance / leg_time))
        for leg_time, leg_distance in zip(avg_leg_times_h, leg_distances_nm)
    ]

    return {
        "path": r_path,
        "speed": avg_leg_speeds_kn,
        "time": avg_leg_times_h,
        "distance": leg_distances_nm,
    }


def make_voyage_profile(
    leg_distances,
    leg_speeds,
    design_draft,
    time_anchored=0.0,
    time_at_berth=0.0,
    speed_threshold=5.0,
):
    """Make a voyage profile

    Arguments:
    ----------

        leg_distances: list
            List of leg distances (nm)

        leg_speeds: list
            List of leg speeds (kn)

        design_draft: float
            Design draft (m)

        time_anchored: float
            Time anchored (h)

        time_at_berth: float
            Time at berth (h)

        speed_threshold: float
            Speed threshold to differentiate between "legs_manouvering" and "legs_at_sea".
            Default value of 5.0 kn.

    Returns:
    --------

        dict
            Dictionary representing a voyage profile.

    TODO: Implement criteria for 'manoeuvring' and 'at sea' in [1].
    """

    voyage_profile = {
        "time_anchored": time_anchored,
        "time_at_berth": time_at_berth,
        "legs_manoeuvring": [],
        "legs_at_sea": [],
    }
    for speed, distance in zip(leg_speeds, leg_distances):
        key = "legs_manoeuvring" if speed < speed_threshold else "legs_at_sea"
        voyage_profile[key].append((distance, speed, design_draft))
    return voyage_profile


def calculate_total_fuel_consumption(ifc, timestamps):
    """Calculate the total fuel consumption over a period of time based on instantaneous fuel consumption measurements.

    Parameters
    ----------
    ifc : list
        List of instantaneous fuel consumption measurements in liters per hour (L/h).
    timestamps : list
        List of Unix timestamps corresponding to the instantaneous fuel consumption measurements.

    Returns
    -------
    float
        The total fuel consumption over the time period, in liters (L).

    """

    # Calculate the time interval between adjacent measurements
    dt = np.diff(timestamps) / 3_600

    # Calculate the average fuel consumption between adjacent measurements
    fc_avg = np.convolve(ifc, np.array([0.5, 0.5]), mode="valid")

    # Calculate the total fuel consumption by summing the product of the average fuel consumption and time interval
    total_fc = np.sum(fc_avg * dt)

    return total_fc
