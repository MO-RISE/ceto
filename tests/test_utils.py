from ceto.utils import ms_to_knots, knots_to_ms

import pytest


def test_conversions():
    speed_ms = 10.0
    expected_speed_kn = 10 * 3600 / 1852

    assert ms_to_knots(speed_ms) == pytest.approx(expected_speed_kn)
    assert knots_to_ms(ms_to_knots(speed_ms)) == pytest.approx(speed_ms)
