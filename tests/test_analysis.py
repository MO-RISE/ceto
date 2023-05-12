from ceto.analysis import (
    cross_track_distance,
    douglas_peucker,
    frechet_distance,
    haversine,
)
from pytest import approx, raises


def test_cross_track_distance_same_point():
    coord1 = (0.0, 0.0)
    coord2 = (0.0, 0.1)
    coord3 = (0.0, 0.0)
    assert cross_track_distance(coord1, coord2, coord3) == approx(0)


def test_cross_track_distance_on_path():
    coord1 = (0.0, 0.0)
    coord2 = (0.0, 0.1)
    coord3 = (0.0, 0.05)
    assert cross_track_distance(coord1, coord2, coord3) == approx(0)


def test_cross_track_distance_off_path():
    coord1 = (0.0, 0.0)
    coord2 = (0.0, 0.1)
    coord3 = (0.01, 0.05)
    assert cross_track_distance(coord1, coord2, coord3) == approx(
        0.01 * 60 * 1852, rel=0.1
    )


def test_douglas_peucker():
    path = [(0.0, 0.0), (0.05, 0.05), (0.0, 0.1)]
    assert douglas_peucker(path, 10) == [(0.0, 0.0), (0.05, 0.05), (0.0, 0.1)]

    path = [(0.0, 0.0), (0.0, 0.05), (0.0, 0.1)]
    assert douglas_peucker(path, 10) == [(0.0, 0.0), (0.0, 0.1)]

    path = [(0.0, 0.0), ((9 / 60) / 1852, 0.05), (0.0, 0.1)]
    assert douglas_peucker(path, 10) == [(0.0, 0.0), (0.0, 0.1)]

    path = [(0.0, 0.0), ((9 / 60) / 1852, 0.05), (0.0, 0.1)]
    assert douglas_peucker(path, 8) == [(0.0, 0.0), ((9 / 60) / 1852, 0.05), (0.0, 0.1)]


def test_frechet_distance():
    path1 = [(0, 0), (0, 0), (0.01, 0), (0.02, 0), (0.03, 0), (0.04, 0)]
    path2 = [(0, 0), (0.01, 0.01), (0.02, 0.01), (0.03, 0.01), (0.04, 0)]

    # Test with non-empty paths
    assert frechet_distance(path1, path1) == approx(0.0)
    assert frechet_distance(path2, path2) == approx(0.0)
    assert frechet_distance(path1, path2) == approx(haversine((0, 0), (0.01, 0)))

    # Test with empty paths
    with raises(ValueError):
        frechet_distance([], [])

    # Test with one empty path
    with raises(ValueError):
        frechet_distance(path1, [])

    with raises(ValueError):
        frechet_distance([], path1)
