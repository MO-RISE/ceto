# ceto

Open-source tools for analysing vessel data.

## Development

To develop `ceto`, clone the repository, create a virtual environment, and install `ceto` as editable code by running the following command in the root directory of the repository:

```
$ pip install -e .
```

## Usage

### General

For better or for worse, `ceto` uses two specific dictionaries as arguments of many of its functions: `vessel_data` and `voyage_profile`. Here are some examples of these dictionaries:

```python
vessel_data = {
    "length": 39.8,  # meters
    "beam": 10.46,  # meteres
    "design_speed": 13.5,  # knots
    "design_draft": 2.84,  # meters
    "double_ended": False,  # True or False
    "number_of_propulsion_engines": 4,
    "propulsion_engine_power": 330,  # per engine kW
    "propulsion_engine_type": "MSD",
    "propulsion_engine_age": "after_2000",
    "propulsion_engine_fuel_type": "MDO",
    "type": "ferry-pax",
    "size": 686,  # GT
}

voyage_profile = {
    "time_anchored": 10.0,  # hours
    "time_at_berth": 10.0,  # hours
    "legs_manoeuvring": [
        (10, 10, 6),  # distance (nm), speed (kn), draft (m)
    ],
    "legs_at_sea": [(30, 10, 6), (30, 10, 6)],  # distance (nm), speed (kn), draft (m)
}

```

The `vessel_data` dictionary must have the following key-value pairs:
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

The `voyage_profile` dictionary must have the following key-value pairs:

  - `time_anchored`: Time spent anchored (h).
  - `time_at_berth`: Time spent at berth (h).
  - `legs_manoeuvring`: List of (distance (nm), speed (kn), draft (m)) tuples summarizing the conditions and distance the vessel spent manoeuvring. 
  - `legs_at_sea`': List of (distance (nm), speed (kn), draft (m)) tuples summarizing the conditions and distance the vessel at sea.

Whether a vessel is "at sea" or "manoeuvring" can be determined through the criteria presented in [1].

## Module

- `imo`: This module includes functions for estimating the fuel consumption of vessels. Based on [1].
- `energy_systems`: This module includes functions for estimating the details of vessel energy systems (i.e. internal combustion systems, battery systems, and hydrogen systems).

## References

 [1] IMO. Fourth IMO GHG Study 2020. IMO.

