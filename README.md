![cetos-logo](./cetos-logo.svg)

# Open-source tools for analyzing vessel data

[![CI](https://github.com/RISE-Maritime/cetos/workflows/CI%20checks/badge.svg)](https://github.com/RISE-Maritime/cetos/actions)
[![PyPI](https://img.shields.io/pypi/v/cetos)](https://pypi.org/project/cetos/)
[![Python Version](https://img.shields.io/pypi/pyversions/cetos)](https://pypi.org/project/cetos/)
[![License](https://img.shields.io/github/license/RISE-Maritime/cetos)](https://github.com/RISE-Maritime/cetos/blob/main/LICENSE)

## Overview

cetos provides tools for analyzing vessel performance, estimating fuel consumption, and evaluating energy systems for maritime vessels. It implements methodologies from the IMO Fourth GHG Study 2020.

### Features

- **Fuel Consumption Estimation**: Calculate vessel fuel consumption based on IMO methodologies
- **Custom SFC Curves**: Override the IMO fuel model with your own measured engine SFC curve
- **Energy System Analysis**: Analyze batteries, hydrogen systems, and hybrid propulsion
- **AIS Data Processing**: Convert AIS data to voyage profiles
- **Multiple Vessel Types**: Support for various vessel types (ferries, container ships, tankers, etc.)

## Installation

Install cetos using pip:

```bash
pip install cetos
```

## Quick Start

```python
from cetos import imo
from cetos.models import VesselData, VoyageLeg, VoyageProfile

# Define vessel characteristics
vessel_data = VesselData(
    length_m=39.8,
    beam_m=10.46,
    design_speed_kn=13.5,
    design_draft_m=2.84,
    double_ended=False,
    number_of_propulsion_engines=4,
    propulsion_engine_power_kw=330,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="ferry-pax",
    size=686,  # GT
)

# Define voyage profile with voyage legs
voyage_profile = VoyageProfile(
    time_anchored_h=10.0,
    time_at_berth_h=10.0,
    legs_manoeuvring=[VoyageLeg(distance_nm=10, speed_kn=10, draft_m=2.8)],
    legs_at_sea=[
        VoyageLeg(distance_nm=30, speed_kn=10, draft_m=2.8),
        VoyageLeg(distance_nm=30, speed_kn=10, draft_m=2.8),
    ],
)

# Calculate fuel consumption
results = imo.estimate_fuel_consumption(vessel_data, voyage_profile)
print(f"Total fuel consumption: {results['total_kg']} kg")
```

## Custom SFC curves

By default, cetos estimates specific fuel consumption (SFC) using the IMO Fourth GHG Study 2020 model. You can instead supply your own SFC curve — for example, one measured on an engine test bed — and cetos will use it for the propulsion engines.

Continuing from the Quick Start above:

```python
from cetos import SFCCurve

# Build an SFC curve from measured points (g/kWh at part loads, the default unit)
sfc_curve = SFCCurve.from_points(
    [(0.25, 205), (0.50, 190), (0.75, 182), (0.85, 180), (1.00, 185)],
    interpolation="pchip",  # smooth, shape-preserving; "linear" is the default
)

# Attach the curve to the vessel. Fuel estimates now use your curve for the
# propulsion engines in place of the IMO model (auxiliary engines and steam
# boilers are unaffected).
vessel_data.propulsion_engine_sfc_curve = sfc_curve

results = imo.estimate_fuel_consumption(vessel_data, voyage_profile)
print(f"Total fuel consumption: {results['total_kg']} kg")
```

A curve can also be passed directly to `VesselData(...)` as the `propulsion_engine_sfc_curve` argument. Besides `SFCCurve.from_points`, two other constructors are available:

- `SFCCurve.from_callable(fn, units="g/kWh")` — wrap any `load -> SFC` function
- `SFCCurve.constant(value, units="g/kWh")` — a flat, load-independent SFC

SFC values are interpreted as `g/kWh` by default; pass `units="kg/kWh"` if your data is already in `kg/kWh`.

## Modules

### IMO Module (`cetos.imo`)
Functions for estimating vessel fuel consumption based on IMO Fourth GHG Study 2020 methodologies.

### Energy Systems (`cetos.energy_systems`)
Tools for analyzing vessel energy systems including batteries, hydrogen, and internal combustion engines.

### AIS Adapter (`cetos.ais_adapter`)
Process AIS (Automatic Identification System) data and convert it to voyage profiles.

### Analysis (`cetos.analysis`)
Additional analysis tools for vessel performance evaluation.

## Development

### Quick Setup with uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/RISE-Maritime/cetos.git
cd cetos

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/RISE-Maritime/cetos.git
cd cetos

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Using Dev Containers

This repository includes a dev container configuration for VS Code. Simply open the repository in VS Code and select "Reopen in Container" when prompted.

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
ruff check --fix .
```

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## References

[1] IMO. Fourth IMO GHG Study 2020. International Maritime Organization.

## Contact

- **Issues**: [GitHub Issues](https://github.com/RISE-Maritime/cetos/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RISE-Maritime/cetos/discussions)

