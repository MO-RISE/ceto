from pytest import approx, raises

from cetos.sfc import SFCCurve


def test_from_points_interpolation():
    """Piecewise-linear interpolation between measured points (g/kWh default)."""
    curve = SFCCurve.from_points([(0.5, 200), (1.0, 180)])
    assert curve(0.5) == approx(0.200)
    assert curve(1.0) == approx(0.180)
    # Linear interpolation at the midpoint.
    assert curve(0.75) == approx(0.190)


def test_from_points_units_kg_per_kwh():
    """Points can be supplied directly in kg/kWh."""
    curve = SFCCurve.from_points([(0.5, 0.2), (1.0, 0.18)], units="kg/kWh")
    assert curve(0.5) == approx(0.2)
    assert curve(1.0) == approx(0.18)


def test_from_points_unsorted_input_is_sorted():
    """Points given out of order are sorted by load."""
    curve = SFCCurve.from_points([(1.0, 180), (0.5, 200), (0.75, 185)])
    assert curve(0.5) == approx(0.200)
    assert curve(0.75) == approx(0.185)
    assert curve(1.0) == approx(0.180)


def test_from_points_clamps_outside_range_by_default():
    """Loads outside the measured range clamp to the nearest endpoint."""
    curve = SFCCurve.from_points([(0.5, 200), (1.0, 180)])
    assert curve(0.1) == approx(0.200)


def test_from_points_extrapolation_error():
    """extrapolation='error' rejects loads outside the measured range."""
    curve = SFCCurve.from_points([(0.5, 200), (1.0, 180)], extrapolation="error")
    with raises(ValueError) as info:
        curve(0.1)
    assert "outside" in str(info)
    # Loads within the measured range still work.
    assert curve(0.75) == approx(0.190)


def test_from_points_requires_at_least_two_points():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200)])
    assert "at least 2" in str(info)


def test_from_points_rejects_duplicate_loads():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200), (0.5, 190)])
    assert "duplicate" in str(info)


def test_from_points_rejects_load_out_of_range():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200), (1.5, 180)])
    assert "load" in str(info)


def test_from_points_rejects_non_positive_sfc():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200), (1.0, -1)])
    assert "sfc" in str(info)


def test_from_points_pchip_passes_through_points():
    """PCHIP interpolation passes exactly through the measured points."""
    points = [(0.25, 210), (0.5, 190), (0.75, 180), (1.0, 185)]
    curve = SFCCurve.from_points(points, interpolation="pchip")
    for load, sfc in points:
        assert curve(load) == approx(sfc / 1000.0)


def test_from_points_pchip_differs_from_linear_between_points():
    """PCHIP and linear interpolation generally disagree between points."""
    points = [(0.25, 210), (0.5, 190), (0.75, 180), (1.0, 185)]
    pchip = SFCCurve.from_points(points, interpolation="pchip")
    linear = SFCCurve.from_points(points, interpolation="linear")
    assert pchip(0.6) != approx(linear(0.6))


def test_from_points_pchip_stays_within_data_range():
    """PCHIP is shape-preserving: it does not overshoot the data range."""
    points = [(0.25, 210), (0.5, 190), (0.75, 180), (1.0, 185)]
    curve = SFCCurve.from_points(points, interpolation="pchip")
    for i in range(101):
        load = 0.25 + 0.75 * i / 100
        assert 0.180 - 1e-9 <= curve(load) <= 0.210 + 1e-9


def test_from_points_pchip_clamps_outside_range():
    """PCHIP curves clamp to the endpoint value outside the measured range."""
    curve = SFCCurve.from_points(
        [(0.5, 200), (0.75, 185), (1.0, 190)], interpolation="pchip"
    )
    assert curve(0.1) == approx(0.200)


def test_from_points_pchip_extrapolation_error():
    curve = SFCCurve.from_points(
        [(0.5, 200), (0.75, 185), (1.0, 190)],
        interpolation="pchip",
        extrapolation="error",
    )
    with raises(ValueError) as info:
        curve(0.1)
    assert "outside" in str(info)


def test_from_points_rejects_unknown_interpolation():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200), (1.0, 180)], interpolation="cubic")
    assert "interpolation" in str(info)


def test_from_callable():
    curve = SFCCurve.from_callable(lambda _load: 180.0)
    assert curve(0.5) == approx(0.180)


def test_from_callable_units_kg_per_kwh():
    curve = SFCCurve.from_callable(lambda _load: 0.18, units="kg/kWh")
    assert curve(0.5) == approx(0.18)


def test_from_callable_rejects_non_callable():
    with raises(ValueError) as info:
        SFCCurve.from_callable(123)
    assert "callable" in str(info)


def test_from_callable_rejects_negative_return():
    """A callable returning a non-positive SFC fails at construction time."""
    with raises(ValueError) as info:
        SFCCurve.from_callable(lambda _load: -5.0)
    assert "sfc" in str(info)


def test_from_callable_surfaces_callable_errors():
    """An error raised by the callable surfaces as a ValueError at build time."""

    def bad(_load):
        raise RuntimeError("boom")

    with raises(ValueError) as info:
        SFCCurve.from_callable(bad)
    assert "RuntimeError" in str(info)


def test_constant():
    curve = SFCCurve.constant(190)
    assert curve(0.1) == approx(0.190)
    assert curve(0.5) == approx(0.190)
    assert curve(1.0) == approx(0.190)


def test_constant_rejects_non_positive():
    with raises(ValueError) as info:
        SFCCurve.constant(0)
    assert "value" in str(info)


def test_rejects_unknown_units():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200), (1.0, 180)], units="lb/hph")
    assert "units" in str(info)


def test_rejects_unknown_extrapolation():
    with raises(ValueError) as info:
        SFCCurve.from_points([(0.5, 200), (1.0, 180)], extrapolation="quadratic")
    assert "extrapolation" in str(info)


def test_call_rejects_load_out_of_range():
    """Evaluating a curve outside [0, 1] raises a ValueError."""
    curve = SFCCurve.from_points([(0.5, 200), (1.0, 180)])
    with raises(ValueError) as info:
        curve(1.5)
    assert "engine_load" in str(info)
    with raises(ValueError) as info:
        curve(-0.1)
    assert "engine_load" in str(info)


def test_repr():
    assert "SFCCurve" in repr(SFCCurve.constant(190))
