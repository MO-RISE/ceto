from ceto.weights import *

DUMMY_VESSEL_DATA = {
    "design_speed": 10,  # kn
    "design_draft": 7,  # m
    "number_of_propulsion_engines": 1,
    "propulsion_engine_power": 1_000,
    "propulsion_engine_type": "MSD",
    "propulsion_engine_age": "after_2001",
    "propulsion_engine_fuel_type": "MDO",
    "type": "offshore",
    "size": None,
}

DUMMY_VOYAGE_PROFILE = {
    "time_anchored": 10.0,  # time
    "time_at_berth": 10.0,  # time
    "legs_manoeuvring": [
        (10, 10, 7),  # distance (nm), speed (kn), draft (m)
    ],
    "legs_at_sea": [(10, 10, 7), (20, 10, 7)],  # distance (nm), speed (kn), draft (m)
}


def test_estimate_internal_combustion_system_weight_and_volume():

    ice = estimate_internal_combustion_system_weight_and_volume(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )
    assert ice["mass"] != 0.0
    assert ice["volume"] != 0.0


def test_estimate_gas_hydrogen_system_weight_and_volume():

    gas = estimate_gas_hydrogen_system_weight_and_volume(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )

    ice = estimate_internal_combustion_system_weight_and_volume(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )

    # Hydrogen gas system is larger and heavier than ICE
    assert gas["mass"] > ice["mass"]
    assert gas["volume"] > ice["volume"]


def test_estimate_liquid_hydrogen_system_weight_and_volume():

    liquid = estimate_liquid_hydrogen_system_weight_and_volume(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )

    ice = estimate_internal_combustion_system_weight_and_volume(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )

    # Hydrogen liquid system is smaller and lighter than ICE
    assert liquid["mass"] > ice["mass"]
    assert liquid["volume"] > ice["volume"]
