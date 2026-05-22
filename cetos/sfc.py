"""
User-supplied specific fuel consumption (SFC) curves.

An SFC curve maps propulsion-engine load (a fraction between 0.0 and 1.0) to a
specific fuel consumption in kg/kWh. By default cetos uses the IMO Fourth GHG
Study 2020 model (see :func:`cetos.imo.estimate_specific_fuel_consumption`).
This module lets a user supply their own measured or known curve instead, by
attaching an :class:`SFCCurve` to ``VesselData.propulsion_engine_sfc_curve``.
"""

import math
import numbers

import numpy as np

from cetos.utils import verify_range

# Supported units for SFC input, with their conversion factor to kg/kWh.
_SFC_UNITS = {
    "g/kWh": 1e-3,
    "kg/kWh": 1.0,
}


def _verify_positive_finite(name, value):
    """Verify that a value is a finite, strictly positive number."""
    if not isinstance(value, numbers.Real):
        raise ValueError(f"'{name}' must be a number, got {value!r}.")
    if not math.isfinite(value):
        raise ValueError(f"'{name}' must be finite, got {value}.")
    if value <= 0:
        raise ValueError(f"'{name}' must be strictly positive, got {value}.")


class SFCCurve:
    """A specific fuel consumption curve: engine load -> SFC (kg/kWh).

    Do not instantiate directly; use one of the factory class methods:

        - :meth:`SFCCurve.from_points`: linear or shape-preserving cubic
          interpolation of measured (load, SFC) points, e.g. from an engine
          shop-test report.
        - :meth:`SFCCurve.from_callable`: wrap an arbitrary load -> SFC
          function.
        - :meth:`SFCCurve.constant`: a load-independent SFC.

    An :class:`SFCCurve` is callable: ``curve(engine_load)`` returns the SFC in
    kg/kWh. Internally all values are stored in kg/kWh, matching the return
    value of :func:`cetos.imo.estimate_specific_fuel_consumption`.
    """

    def __init__(self, _evaluate, _description):
        # Internal constructor. Use the factory class methods instead.
        self._evaluate = _evaluate
        self._description = _description

    @staticmethod
    def _unit_factor(units):
        """Return the multiplier that converts ``units`` to kg/kWh."""
        if units not in _SFC_UNITS:
            raise ValueError(
                f"'units' must be one of {sorted(_SFC_UNITS)}, got {units!r}."
            )
        return _SFC_UNITS[units]

    @classmethod
    def from_points(
        cls,
        points,
        *,
        units="g/kWh",
        interpolation="linear",
        extrapolation="clamp",
    ):
        """Build a curve by interpolating measured points.

        This is the typical case: engine datasheets and shop-test reports give
        SFC at a handful of part loads (e.g. 25%, 50%, 75%, 85%, 100%). For a
        faithful curve, supply points that capture its shape -- in particular
        one near the 70-90% load minimum where the SFC bucket bottoms out.

        Arguments:
        ----------

            points: iterable of (load, sfc)
                At least two (engine_load, sfc) pairs. ``load`` is a fraction
                between 0.0 and 1.0; ``sfc`` is expressed in ``units``. Points
                are sorted by load automatically; duplicate loads are rejected.

            units (optional): string
                Units of the ``sfc`` values: 'g/kWh' (default) or 'kg/kWh'.

            interpolation (optional): string
                How to interpolate between the measured points:
                    - 'linear' (default): piecewise-linear. Bounded and
                      predictable, but its chords slightly overestimate a
                      convex SFC curve between points.
                    - 'pchip': shape-preserving piecewise cubic (monotone
                      Hermite). Smooth and, unlike a plain cubic spline, free
                      of overshoot. Best when the measured points are sparse.

            extrapolation (optional): string
                Behaviour for an engine load outside the measured range:
                    - 'clamp' (default): hold the nearest endpoint value.
                    - 'error': raise a ValueError.

        Returns:
        --------

            SFCCurve
        """
        factor = cls._unit_factor(units)
        if interpolation not in ("linear", "pchip"):
            raise ValueError(
                f"'interpolation' must be 'linear' or 'pchip', got {interpolation!r}."
            )
        if extrapolation not in ("clamp", "error"):
            raise ValueError(
                f"'extrapolation' must be 'clamp' or 'error', got {extrapolation!r}."
            )

        points = list(points)
        if len(points) < 2:
            raise ValueError("'from_points' requires at least 2 (load, sfc) points.")

        loads = []
        sfcs = []
        for point in points:
            try:
                load, sfc = point
            except (TypeError, ValueError) as err:
                raise ValueError(
                    f"Each point must be a (load, sfc) pair, got {point!r}."
                ) from err
            verify_range("load", load, 0.0, 1.0)
            _verify_positive_finite("sfc", sfc)
            loads.append(float(load))
            sfcs.append(float(sfc) * factor)

        order = np.argsort(loads)
        loads = np.asarray(loads)[order]
        sfcs = np.asarray(sfcs)[order]
        if np.any(np.diff(loads) == 0):
            raise ValueError("'from_points' received duplicate load values.")

        lowest, highest = float(loads[0]), float(loads[-1])

        if interpolation == "linear":

            def _interpolate(engine_load):
                return float(np.interp(engine_load, loads, sfcs))

        else:
            from scipy.interpolate import PchipInterpolator

            _pchip = PchipInterpolator(loads, sfcs, extrapolate=False)

            def _interpolate(engine_load):
                return float(_pchip(engine_load))

        def _evaluate(engine_load):
            if not lowest <= engine_load <= highest:
                if extrapolation == "error":
                    raise ValueError(
                        f"'engine_load' {engine_load} is outside the curve's "
                        f"measured range [{lowest}, {highest}] and "
                        f"extrapolation='error'."
                    )
                # 'clamp': hold the nearest endpoint value.
                engine_load = min(max(engine_load, lowest), highest)
            return _interpolate(engine_load)

        description = (
            f"from_points, {len(loads)} points, "
            f"load {lowest:.2f}-{highest:.2f}, "
            f"interpolation={interpolation!r}, extrapolation={extrapolation!r}"
        )
        return cls(_evaluate, description)

    @classmethod
    def from_callable(cls, fn, *, units="g/kWh"):
        """Build a curve from an arbitrary user function.

        The full-flexibility escape hatch. The function is sample-evaluated at
        construction time to catch obvious errors early.

        Arguments:
        ----------

            fn: callable
                A function taking an engine load (fraction between 0.0 and 1.0)
                and returning an SFC expressed in ``units``.

            units (optional): string
                Units of the value returned by ``fn``: 'g/kWh' (default) or
                'kg/kWh'.

        Returns:
        --------

            SFCCurve
        """
        factor = cls._unit_factor(units)
        if not callable(fn):
            raise ValueError(f"'from_callable' requires a callable, got {fn!r}.")

        def _evaluate(engine_load):
            sfc = fn(engine_load) * factor
            _verify_positive_finite("sfc", sfc)
            return float(sfc)

        # Sample-evaluate to surface obvious errors at construction time.
        for sample_load in (0.1, 0.5, 1.0):
            try:
                _evaluate(sample_load)
            except ValueError:
                raise
            except Exception as err:  # noqa: BLE001 - re-raised as ValueError
                raise ValueError(
                    f"The callable raised {type(err).__name__} when evaluated "
                    f"at load={sample_load}: {err}"
                ) from err

        name = getattr(fn, "__name__", repr(fn))
        return cls(_evaluate, f"from_callable({name})")

    @classmethod
    def constant(cls, value, *, units="g/kWh"):
        """Build a load-independent (flat) curve.

        Arguments:
        ----------

            value: float
                The SFC, expressed in ``units``.

            units (optional): string
                Units of ``value``: 'g/kWh' (default) or 'kg/kWh'.

        Returns:
        --------

            SFCCurve
        """
        factor = cls._unit_factor(units)
        _verify_positive_finite("value", value)
        sfc = float(value) * factor

        def _evaluate(_):
            return sfc

        return cls(_evaluate, f"constant({sfc:.5f} kg/kWh)")

    def __call__(self, engine_load):
        """Return the specific fuel consumption (kg/kWh) at ``engine_load``.

        Arguments:
        ----------

            engine_load: float
                Engine load as a fraction between 0.0 and 1.0.

        Returns:
        --------

            float
                Specific fuel consumption (kg/kWh).
        """
        verify_range("engine_load", engine_load, 0.0, 1.0)
        return self._evaluate(engine_load)

    def __repr__(self):
        return f"SFCCurve({self._description})"
