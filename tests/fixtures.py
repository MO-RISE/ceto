"""
Test fixtures for pinning tests.

This module contains realistic vessel and voyage profiles for different vessel types
to be used in comprehensive pinning tests.
"""

from cetos.models import VesselData, VoyageLeg, VoyageProfile

# Ferry Passenger Vessel
FERRY_PAX_VESSEL = VesselData(
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
    size=686,
)

FERRY_PAX_DAILY_VOYAGE = VoyageProfile(
    time_anchored_h=0.5,
    time_at_berth_h=2.0,
    legs_manoeuvring=[
        VoyageLeg(0.5, 5, 2.8),
        VoyageLeg(0.5, 5, 2.8),
    ],
    legs_at_sea=[
        VoyageLeg(10, 12, 2.8),
        VoyageLeg(10, 12, 2.8),
    ],
)

# Oil Tanker
OIL_TANKER_VESSEL = VesselData(
    length_m=200,
    beam_m=30,
    design_speed_kn=15,
    design_draft_m=12,
    double_ended=False,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=8_000,
    propulsion_engine_type="SSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="HFO",
    type="oil_tanker",
    size=50_000,
)

OIL_TANKER_LONG_VOYAGE = VoyageProfile(
    time_anchored_h=10.0,
    time_at_berth_h=24.0,
    legs_manoeuvring=[
        VoyageLeg(2, 8, 12),
        VoyageLeg(2, 8, 10),
    ],
    legs_at_sea=[
        VoyageLeg(500, 14, 12),
        VoyageLeg(500, 14, 10),
    ],
)

# General Cargo Vessel
GENERAL_CARGO_VESSEL = VesselData(
    length_m=150,
    beam_m=23,
    design_speed_kn=18,
    design_draft_m=8.5,
    double_ended=False,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=5_000,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="general_cargo",
    size=15_000,
)

GENERAL_CARGO_MEDIUM_VOYAGE = VoyageProfile(
    time_anchored_h=5.0,
    time_at_berth_h=12.0,
    legs_manoeuvring=[
        VoyageLeg(1.5, 6, 8.5),
        VoyageLeg(1.5, 6, 7.0),
    ],
    legs_at_sea=[
        VoyageLeg(200, 16, 8.5),
        VoyageLeg(200, 16, 7.0),
    ],
)

# Offshore Supply Vessel
OFFSHORE_VESSEL = VesselData(
    length_m=100,
    beam_m=20,
    design_speed_kn=10,
    design_draft_m=7,
    double_ended=False,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=1_000,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="offshore",
    size=None,
)

OFFSHORE_SHORT_VOYAGE = VoyageProfile(
    time_anchored_h=10.0,
    time_at_berth_h=10.0,
    legs_manoeuvring=[
        VoyageLeg(10, 10, 7),
    ],
    legs_at_sea=[
        VoyageLeg(10, 10, 7),
        VoyageLeg(20, 10, 6),
    ],
)

# RoRo Ferry
ROPAX_VESSEL = VesselData(
    length_m=180,
    beam_m=28,
    design_speed_kn=22,
    design_draft_m=6.5,
    double_ended=True,
    number_of_propulsion_engines=4,
    propulsion_engine_power_kw=2_500,
    propulsion_engine_type="HSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="ferry-ropax",
    size=25_000,
)

ROPAX_FREQUENT_VOYAGE = VoyageProfile(
    time_anchored_h=0.0,
    time_at_berth_h=4.0,
    legs_manoeuvring=[
        VoyageLeg(1, 8, 6.5),
        VoyageLeg(1, 8, 6.5),
        VoyageLeg(1, 8, 6.5),
        VoyageLeg(1, 8, 6.5),
    ],
    legs_at_sea=[
        VoyageLeg(50, 20, 6.5),
        VoyageLeg(50, 20, 6.5),
    ],
)

# Fishing vessel: Fredrika (Stigfjord 40, 2016).
# Source: Barman & Soerfeldt (2024) Table 2.1 (vessel) and Tables 4.4/4.8
# (representative 12-string fishing day; thesis Section 4.1.2-4.1.3).
FREDRIKA_VESSEL = VesselData(
    length_m=11.91,
    beam_m=4.0,
    design_speed_kn=9.0,
    design_draft_m=1.5,
    double_ended=False,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=242,
    propulsion_engine_type="HSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="miscellaneous-fishing",
    size=11.1,
    gear_type="pot_small",
)

# Approximate representative day, ~8.8 h total, 12 strings of pots.
# Table 4.4 averages for the 10 days with >=12 strings:
#   steaming out 1.0 h / 7.7 nm; fishing 6.8 h / 22.6 nm; steaming in 1.0 h / 7.2 nm.
# Within the 6.8 h fishing mode, the boat alternates between picking pots at
# 0.7 kn (~24 min/string * 12 = 4.8 h) and short transits between strings at
# ~9 kn (~2.0 h, ~19.2 nm). Both sub-modes are tagged "fishing" for the
# hydraulics/DC duty cycles, but propulsion power differs hugely.
FREDRIKA_DAY_VOYAGE = VoyageProfile(
    time_anchored_h=0.0,
    time_at_berth_h=0.0,
    legs_at_sea=[
        VoyageLeg(7.7, 8.8, 1.5),  # steaming out: 0.875 h
        VoyageLeg(7.2, 8.8, 1.5),  # steaming in: 0.818 h
    ],
    legs_fishing=[
        VoyageLeg(18.0, 9.0, 1.5),  # between-string transits: 2.0 h
        VoyageLeg(3.4, 0.7, 1.5),  # pot pickup, 12 strings * 24 min: 4.857 h
    ],
)

# Fishing vessel: Mira (Stigfjord 37, 1999). Smaller engine, slower transit.
MIRA_VESSEL = VesselData(
    length_m=11.0,
    beam_m=4.1,
    design_speed_kn=7.0,
    design_draft_m=1.5,
    double_ended=False,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=167,
    propulsion_engine_type="HSD",
    propulsion_engine_age="1984-2000",
    propulsion_engine_fuel_type="MDO",
    type="miscellaneous-fishing",
    size=12.11,
    gear_type="pot_small",
)

# Mira average day: 7 strings, ~7.1 h, 21.3 nm (Table 4.5).
# Within the 4.2 h fishing mode: ~2.8 h pot pickup at 0.7 kn (7 strings * 24 min)
# and ~1.4 h between-string transits at 7 kn.
MIRA_DAY_VOYAGE = VoyageProfile(
    time_anchored_h=0.0,
    time_at_berth_h=0.0,
    legs_at_sea=[
        VoyageLeg(5.4, 7.0, 1.5),  # steaming out: 0.77 h
        VoyageLeg(6.3, 7.0, 1.5),  # steaming in: 0.9 h
    ],
    legs_fishing=[
        VoyageLeg(9.8, 7.0, 1.5),  # between-string transits: 1.4 h
        VoyageLeg(1.96, 0.7, 1.5),  # pot pickup, 7 strings * 24 min: 2.8 h
    ],
)

# Minimal voyage profile (edge case)
MINIMAL_VOYAGE = VoyageProfile(
    time_anchored_h=0.0,
    time_at_berth_h=1.0,
    legs_manoeuvring=[],
    legs_at_sea=[],
)

# Maximal complex voyage (stress test)
COMPLEX_VOYAGE = VoyageProfile(
    time_anchored_h=20.0,
    time_at_berth_h=30.0,
    legs_manoeuvring=[
        VoyageLeg(1, 5, 7),
        VoyageLeg(2, 6, 7),
        VoyageLeg(1, 4, 6.5),
    ],
    legs_at_sea=[
        VoyageLeg(100, 15, 8),
        VoyageLeg(150, 14, 7.5),
        VoyageLeg(200, 16, 7),
        VoyageLeg(100, 13, 6.5),
    ],
)

# AIS data samples for different vessel types
AIS_FERRY_PAX = {
    "ship_type": 60,  # Passenger ship
    "to_bow": 20,
    "to_stern": 20,
    "to_port": 5,
    "to_starboard": 5,
    "speed": 12,
    "draught": 2.8,
    "lat": 56.0,
    "lon": 12.0,
}

AIS_OIL_TANKER = {
    "ship_type": 80,  # Tanker
    "to_bow": 150,
    "to_stern": 50,
    "to_port": 15,
    "to_starboard": 15,
    "speed": 14,
    "draught": 12,
    "lat": 57.0,
    "lon": 11.0,
}

AIS_CARGO = {
    "ship_type": 70,  # Cargo
    "to_bow": 100,
    "to_stern": 50,
    "to_port": 11,
    "to_starboard": 12,
    "speed": 16,
    "draught": 8.5,
    "lat": 58.0,
    "lon": 12.5,
}
