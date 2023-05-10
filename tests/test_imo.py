from pytest import raises, approx
from ceto.imo import (
    estimate_instantaneous_fuel_consumption_of_auxiliary_systems,
    estimate_specific_fuel_consumption,
    verify_vessel_data,
    estimate_auxiliary_power_demand,
    verify_voyage_profile,
    estimate_propulsion_engine_load,
    estimate_fuel_consumption,
    estimate_fuel_consumption_of_propulsion_engines,
)


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
        (10, 10, 7),  # distance (nm), speed (kn), draft (m)
    ],
    "legs_at_sea": [(10, 10, 7), (20, 10, 6)],  # distance (nm), speed (kn), draft (m)
}


def test_estimate_specific_fuel_consumption():
    # The sfc changes with engine load for non aux. engines or steam boilers.
    sfc_1 = estimate_specific_fuel_consumption(0.2, "SSD", "HFO", "after_2000")
    sfc_2 = estimate_specific_fuel_consumption(0.8, "SSD", "HFO", "after_2000")
    sfc_3 = estimate_specific_fuel_consumption(1.0, "SSD", "HFO", "after_2000")
    assert sfc_1 > sfc_2
    assert sfc_3 > sfc_2

    sfc_1 = estimate_specific_fuel_consumption(0.2, "HSD", "HFO", "after_2000")
    sfc_2 = estimate_specific_fuel_consumption(0.8, "HSD", "HFO", "after_2000")
    sfc_3 = estimate_specific_fuel_consumption(1.0, "HSD", "HFO", "after_2000")
    assert sfc_1 > sfc_2
    assert sfc_3 > sfc_2

    # The sfc does not change with engine load for aux. engines and steam boilers.
    sfc_1 = estimate_specific_fuel_consumption(
        0.2, "auxiliary_engine", "HFO", "after_2000"
    )
    sfc_2 = estimate_specific_fuel_consumption(
        0.8, "auxiliary_engine", "HFO", "after_2000"
    )
    sfc_3 = estimate_specific_fuel_consumption(
        1.0, "auxiliary_engine", "HFO", "after_2000"
    )
    assert sfc_1 == sfc_2
    assert sfc_3 == sfc_2


def test_verify_vessel_data():
    vessel_data = DUMMY_VESSEL_DATA.copy()

    # Correct data, no error raises
    verify_vessel_data(vessel_data)

    # Missing data
    del vessel_data["design_speed"]
    with raises(KeyError) as info:
        verify_vessel_data(vessel_data)
    assert "design_speed" in str(info)

    # None value for size not Ok for some vessel types
    # vessel_data = DUMMY_VESSEL_DATA.copy()
    # vessel_data["type"] = "oil_tanker"
    # with raises(ValueError) as info:
    #    verify_vessel_data(vessel_data)
    # assert "None" in str(info)

    # Incorrect data
    vessel_data = DUMMY_VESSEL_DATA.copy()
    vessel_data["propulsion_engine_fuel_type"] = "blue"
    with raises(ValueError) as info:
        verify_vessel_data(vessel_data)
    assert "propulsion_engine_fuel_type" in str(info)

    vessel_data = DUMMY_VESSEL_DATA.copy()
    vessel_data["propulsion_engine_type"] = "blue"
    with raises(ValueError) as info:
        verify_vessel_data(vessel_data)
    assert "propulsion_engine_type" in str(info)


def test_estimate_auxiliary_power_demand():
    # Auxiliary power demand increases size
    vessel_data = DUMMY_VESSEL_DATA.copy()
    vessel_data["type"] = "oil_tanker"
    vessel_data["size"] = 5_000
    pd_1a, pd_1b = estimate_auxiliary_power_demand(vessel_data, "at_berth")
    vessel_data["size"] = 20_000
    pd_2a, pd_2b = estimate_auxiliary_power_demand(vessel_data, "at_berth")
    assert pd_2a > pd_1a
    assert pd_2b > pd_1b
    assert pd_1a == 375
    assert pd_1b == 750


def test_estimate_propulsion_engine_load():
    # Engine load increases with speed
    el_1 = estimate_propulsion_engine_load(5, 7, DUMMY_VESSEL_DATA)
    el_2 = estimate_propulsion_engine_load(10, 7, DUMMY_VESSEL_DATA)
    assert el_1 < el_2
    # Engine load increases with draft
    el_1 = estimate_propulsion_engine_load(10, 6, DUMMY_VESSEL_DATA)
    el_2 = estimate_propulsion_engine_load(10, 8, DUMMY_VESSEL_DATA)
    assert el_1 < el_2


def test_estimate_instantaneous_fuel_consumption_of_auxiliary_systems():
    # Offshore vessel should have the same fc regardless of operation mode
    (
        ifc_aux_1,
        ifc_boiler_1,
    ) = estimate_instantaneous_fuel_consumption_of_auxiliary_systems(
        DUMMY_VESSEL_DATA, "at_berth"
    )
    (
        ifc_aux_2,
        ifc_boiler_2,
    ) = estimate_instantaneous_fuel_consumption_of_auxiliary_systems(
        DUMMY_VESSEL_DATA, "at_sea"
    )
    assert ifc_aux_2 == ifc_aux_1
    assert ifc_boiler_2 == ifc_boiler_1


def test_verify_voyage_profile():
    # Raise error if missing key-value pairs
    voyage_profile = DUMMY_VOYAGE_PROFILE.copy()
    del voyage_profile["time_at_berth"]

    with raises(KeyError) as info:
        verify_voyage_profile(voyage_profile)
    assert "time_at_berth" in str(info)


def test_estimate_fuel_consumption():
    vp0 = {
        "time_at_berth": 0,
        "time_anchored": 0,
        "legs_manoeuvring": [],
        "legs_at_sea": [],
    }
    fc_ = estimate_fuel_consumption(DUMMY_VESSEL_DATA, vp0)
    assert fc_["total_kg"] == 0
    assert max(fc_["at_berth"].values()) == 0
    assert max(fc_["anchored"].values()) == 0
    assert max(fc_["manoeuvring"].values()) == 0
    assert max(fc_["at_sea"].values()) == 0

    design_draft = DUMMY_VESSEL_DATA["design_draft"]
    vp1 = {
        "time_at_berth": 10,
        "time_anchored": 10,
        "legs_manoeuvring": [(10, 5, design_draft), (10, 10, design_draft)],
        "legs_at_sea": [(5, 5, design_draft), (10, 10, design_draft)],
    }

    fc_ = estimate_fuel_consumption(DUMMY_VESSEL_DATA, vp1)
    assert fc_["total_kg"] != approx(0.0)
    assert fc_["at_berth"]["auxiliary_engines_kg"] != approx(0.0)
    assert fc_["anchored"]["auxiliary_engines_kg"] != approx(0.0)
    assert fc_["manoeuvring"]["auxiliary_engines_kg"] != approx(0.0)
    assert fc_["at_sea"]["auxiliary_engines_kg"] != approx(0.0)

    # No boiler
    assert fc_["at_berth"]["steam_boilers_kg"] == approx(0.0)
    assert fc_["anchored"]["steam_boilers_kg"] == approx(0.0)
    assert fc_["manoeuvring"]["steam_boilers_kg"] == approx(0.0)
    assert fc_["at_sea"]["steam_boilers_kg"] == approx(0.0)

    assert fc_["manoeuvring"]["propulsion_engines_kg"] != approx(0.0)
    assert fc_["at_sea"]["propulsion_engines_kg"] != approx(0.0)


def test_estimate_fuel_consumption_of_propulsion_engines():
    fc, fc_avg = estimate_fuel_consumption_of_propulsion_engines(
        DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE
    )

    fc_all = estimate_fuel_consumption(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)

    assert fc != 0.0
    assert fc == approx(
        fc_all["manoeuvring"]["propulsion_engines_kg"]
        + fc_all["at_sea"]["propulsion_engines_kg"]
    )
