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
- **GHG Emissions**: CO2, CH4, N2O with CO2-equivalent (IMO MEPC.308, FuelEU Maritime Annex II)
- **Well-to-Wake Analysis**: Full lifecycle GHG intensity for FuelEU Maritime compliance
- **Air Pollutant Emissions**: NOx, SOx, PM (IMO NOx Technical Code, MARPOL Annex VI)
- **CII Rating**: Carbon Intensity Indicator A-E rating per IMO MEPC.339/338/354
- **Energy System Analysis**: Analyze batteries, hydrogen systems, and hybrid propulsion
- **AIS Data Processing**: Convert AIS data to voyage profiles
- **Multiple Vessel Types**: Support for 19 vessel types (ferries, container ships, tankers, etc.)

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
    legs_manoeuvring=[VoyageLeg(distance_nm=10, speed_kn=10, draft_m=6)],
    legs_at_sea=[
        VoyageLeg(distance_nm=30, speed_kn=10, draft_m=6),
        VoyageLeg(distance_nm=30, speed_kn=10, draft_m=6),
    ],
)

# Calculate fuel consumption
results = imo.estimate_fuel_consumption(vessel_data, voyage_profile)
print(f"Total fuel consumption: {results['total_kg']} kg")
```

## Emissions & Regulatory Compliance

### GHG Emissions

```python
from cetos import imo
from cetos.emissions import estimate_ghg_emissions, estimate_well_to_wake_emissions

# After defining vessel_data and voyage_profile (see Quick Start above):

# CO2-equivalent emissions (CO2 + CH4 + N2O)
ghg = estimate_ghg_emissions(vessel_data, voyage_profile)
print(f"Total CO2eq: {ghg['total_kg_co2eq']:.0f} kg")
print(f"  CO2:  {ghg['total_kg_co2']:.0f} kg")
print(f"  CH4:  {ghg['total_kg_ch4']:.2f} kg (× GWP 28 = {ghg['total_kg_ch4'] * 28:.0f} kg CO2eq)")
print(f"  N2O:  {ghg['total_kg_n2o']:.4f} kg (× GWP 265 = {ghg['total_kg_n2o'] * 265:.0f} kg CO2eq)")

# Well-to-Wake for FuelEU Maritime compliance
wtw = estimate_well_to_wake_emissions(vessel_data, voyage_profile)
print(f"GHG intensity: {wtw['ghg_intensity_gco2eq_per_mj']:.1f} gCO2eq/MJ")
print(f"  Well-to-Tank: {wtw['wtt_kg_co2eq']:.0f} kg CO2eq")
print(f"  Tank-to-Wake: {wtw['ttw_kg_co2eq']:.0f} kg CO2eq")

# Override WtT for renewable fuels (e.g., green methanol at 5 gCO2eq/MJ)
wtw_green = estimate_well_to_wake_emissions(
    vessel_data, voyage_profile, wtt_override_gco2eq_per_mj=5.0
)
```

### Air Pollutants (NOx, SOx, PM)

```python
from cetos.emissions import estimate_air_pollutant_emissions

pollutants = estimate_air_pollutant_emissions(vessel_data, voyage_profile)
print(f"NOx: {pollutants['total_kg_nox']:.1f} kg")
print(f"SOx: {pollutants['total_kg_sox']:.1f} kg")
print(f"PM:  {pollutants['total_kg_pm']:.2f} kg")
```

### CII Rating (Carbon Intensity Indicator)

```python
from cetos.cii import estimate_cii

cii = estimate_cii(vessel_data, voyage_profile, year=2024)
print(f"CII Rating: {cii['rating']}")
print(f"Attained CII: {cii['attained_cii']:.2f} gCO2/(DWT·nm)")
print(f"Required CII: {cii['required_cii']:.2f} gCO2/(DWT·nm)")
```

### Emission Factor Sources

| Factor | Source | Stability |
|--------|--------|-----------|
| CO2 (Cf) | IMO MEPC.308(73) | Stoichiometric — never changes |
| CH4 (methane slip) | FuelEU Maritime Annex II, IMO 4th GHG Study | Engine-type dependent; updates possible |
| N2O | FuelEU Maritime Annex II | Stable |
| WtT (upstream) | FuelEU Maritime Annex II | Fixed for fossil fuels; variable for renewables |
| NOx | IMO NOx Technical Code | Engine-age dependent (Tier 0/I/II) |
| SOx | IMO MARPOL Annex VI | Based on fuel sulfur content (0.5% global cap) |
| PM | IMO 4th GHG Study, EMEP/EEA Guidebook | Post-2020 values |
| CII reference lines | IMO MEPC.339(76) | Per vessel type |
| CII reduction factors | IMO MEPC.338(76) | Tighten annually; beyond 2026 TBD |
| CII rating boundaries | IMO MEPC.354(78) | Per vessel type |
| GWP (AR5) | IPCC AR5 | CH4=28, N2O=265 |

## Modules

### IMO Module (`cetos.imo`)
Functions for estimating vessel fuel and energy consumption based on IMO Fourth GHG Study 2020 methodologies.

### Emissions (`cetos.emissions`)
GHG emissions (CO2, CH4, N2O), well-to-wake analysis, and air pollutant emissions (NOx, SOx, PM). Covers FuelEU Maritime and EU ETS requirements.

### CII (`cetos.cii`)
Carbon Intensity Indicator calculation with A-E rating per IMO MEPC.339/338/354. Supports 12 vessel categories with annual reduction factors.

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
[2] IMO MEPC.308(73) — 2024 Guidelines on the method of calculation of the attained EEXI. CO2 emission factors.
[3] FuelEU Maritime Regulation (EU) 2023/1805 — Annex II: Default emission factors (WtT, TtW, CH4, N2O).
[4] IMO MEPC.339(76) — CII reference line parameters.
[5] IMO MEPC.338(76) — Annual CII reduction factors.
[6] IMO MEPC.354(78) — CII rating boundaries.
[7] IMO NOx Technical Code — NOx emission factors by engine type and tier.
[8] IMO MARPOL Annex VI — SOx emission control and fuel sulfur limits.
[9] EMEP/EEA Air Pollutant Emission Inventory Guidebook — PM emission factors.
[10] IPCC Fifth Assessment Report (AR5) — Global Warming Potentials (CH4=28, N2O=265).

## Contact

- **Issues**: [GitHub Issues](https://github.com/RISE-Maritime/cetos/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RISE-Maritime/cetos/discussions)

