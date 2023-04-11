from pytest import raises, approx
from ceto.energy_systems import *

DUMMY_VESSEL_DATA = {
    "design_speed": 10,  # kn
    "design_draft": 7,  # m
    "number_of_propulsion_engines": 1,
    "propulsion_engine_power": 1_000,
    "propulsion_engine_type": "MSD",
    "propulsion_engine_age": "after_2000",
    "propulsion_engine_fuel_type": "MDO",
    "type": "offshore",
    "size": None,
    "double_ended": False,
    "length": 100,
    "beam": 20,
}

DUMMY_VOYAGE_PROFILE = {
    "time_anchored": 10.0,  # time
    "time_at_berth": 10.0,  # time
    "legs_manoeuvring": [
        (10, 10, 6),  # distance (nm), speed (kn), draft (m)
    ],
    "legs_at_sea": [(10, 10, 6), (20, 10, 6)],  # distance (nm), speed (kn), draft (m)
}


def test_suggest_alternative_energy_systems():
    vessel_data = {}
    voyage_profile = {}
    with raises(KeyError) as info:
        suggest_alternative_energy_systems(vessel_data, voyage_profile)

    gas, batter = suggest_alternative_energy_systems(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )
    assert len(gas) != 0
    assert len(batter) != 0
