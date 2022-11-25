# ceto

Open-source tools for analysing vessel data.

## Development

To develop `ceto`, clone the repository, create a virtual environment, and install `ceto` as editable code by running the following command in the root directory of the repository:

```
$ pip install -e .
```

## Usage

### Energy systems module

```python

import ceto.energy_systems as ces

```

"SSD",
"MSD",
"HSD",
"LNG-Otto-MS",
"LBSI",
"gas_turbine",
"steam_turbine",

Describe the vessel with a `dict` containing the following key-value pairs:

- `length`: Length overall of the vessel in meters (m).
- `beam`: Beam or breadth of the vessel in meters (m).
- `design_speed`: Design speed of the vessel in knots (kn).
- `design_draft`: Design draft of the vessel in meters (m).
- `propulsion_engine_power`: Power of a single propulsion engine in kilo Watts (kW).,
- `propulsion_engine_type`: Type of propulsion engine. The possible types/values are:
  - `'SSD'`: Slow-Speed Diesel. An oil engine with a speed equal or lower than 300 RPM.
  - `'MSD`': Medium-Speed Diesel. An oil engine with a speed ranging from 300 to 900 RPM.
  - `'HSD'`: High-Speed Diesel. An oil engine with a speed above 900 RPM.
  - `'LNG-Otto-MS'`: Four-stroke, medium-speed (300 > RPM > 900), dual-fuel engines (LNG and oils) that operate on the Otto cycle.
  - `'LBSI`': LNG engines built by Rolls-Royce/Bergen.
  - `'gas_turbine'`: Gas turbine engine.
  - `'steam_turbine'`: Steam turbine engine. Includes oil-based fuels, LNG, and boil-off gas.
- `propulsion_engine_age`: The age of the propulsion engine. The possible types/values are:
  - `'before_1984'`: All engines manufactured before 1984.
  - `'1984-2000'`: All engines manufactured between 1984 and 2000.
  - `'after_2000'`: All engines manufactured after 2000.
- `propulsion_engine_fuel_type`: Type of fuel used by the propulson engine. The possible types/values are:
  - `'HFO'`: Heavy Fuel Oil
  - `'MDO'`: Marine Diesel Oil
  - `'MeOH'`: Methanol.
  - `'LNG'`: Liquid Natural Gas (including boil-off gas).
- `type`: The type of vessel. The possible types/values are:
  - Cargo-carrying transport ships:
    - `'bulk_carrier'`
    - `'chemical_tanker'`
    - `'container'`
    - `'general_cargo'`
    - `'liquified_gas_tanker'`
    - `'oil_tanker'`
    - `'other_liquids_tanker'`
    - `'ferry-pax'`
    - `'cruise'`
    - `'ferry-ropax'`
    - `'refrigerated_cargo'`
    - `'roro'`
    - `'vehicle'`
  - Non-merchant ships:
    - `'yacht'`
    - `'miscellaneous-fishing'`
  - Work vessels:
    - `'service-tug'`
    - `'offshore'`
    - `'service-other'`
  - Non-seagoing merchant ships:
    - `'miscellaneous-other'`
- `size`: Numerical value describing the size of the vessel in the appropriate units for its type. The appropriate unit for a given vessel type are:
  - `bulk_carrier` -> Deadweight Tonnage (DWT)
  - `chemical_tanker` -> Deadweight Tonnage (DWT)
  - `container` -> Twenty-foot Equivalent Units (TEU)
  - `general_cargo` -> Deadweight Tonnage (DWT)
  - `liquified_gas_tanker` -> Cubic Metres (CBM)
  - `oil_tanker` -> Deadweight Tonnage (DWT)
  - `other_liquids_tanker` -> Deadweight Tonnage (DWT)
  - `ferry` -> Gross Tonnes (GT)
  - `cruise` -> Gross Tonnes (GT)
  - `ropax` -> Gross Tonnes (GT)
  - `refrigerated_cargo` -> Deadweight Tonnage (DWT)
  - `roro` -> Deadweight Tonnage (DWT)
  - `vehicle` -> Number of cars (NC)
  - `yacht` -> Gross Tonnes (GT)
  - `miscellaneous-fishing` -> Gross Tonnes (GT)
  - `service-tug` -> Gross Tonnes (GT)
  - `offshore` -> Gross Tonnes (GT)
  - `service-other` -> Gross Tonnes (GT)
  - `miscellaneous-other` -> Gross Tonnes (GT)

```python

# Describe the vessel with a "vessel data" dictionary.

vessel_data = {
    "length": 24.5, # meters
    "beam": 8, # meteres
    "design_speed": 30,  # knots
    "design_draft": 1.5,  # meters
    "number_of_propulsion_engines": 2,
    "propulsion_engine_power": 1069, # per engine kW
    "propulsion_engine_type": "MSD",
    "propulsion_engine_age": "after_2001",
    "propulsion_engine_fuel_type": "MDO",
    "type": "service-other",
    "size": 63,
}


# Estimate the internal combustion system

```
