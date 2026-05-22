from dataclasses import replace

from pytest import approx, raises

from cetos.imo import (
    estimate_auxiliary_power_demand,
    estimate_fuel_consumption,
    estimate_fuel_consumption_of_propulsion_engines,
    estimate_instantaneous_fuel_consumption_of_auxiliary_systems,
    estimate_propulsion_engine_load,
    estimate_propulsion_engine_sfc,
    estimate_specific_fuel_consumption,
)
from cetos.models import VesselData, VoyageLeg, VoyageProfile
from cetos.sfc import SFCCurve

DUMMY_VESSEL_DATA = VesselData(
    design_speed_kn=10,
    design_draft_m=7,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=1_000,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
    type="offshore",
    size=None,
    double_ended=False,
    length_m=100,
    beam_m=20,
)

DUMMY_VOYAGE_PROFILE = VoyageProfile(
    time_anchored_h=10.0,
    time_at_berth_h=10.0,
    legs_manoeuvring=[
        VoyageLeg(10, 10, 7),  # distance (nm), speed (kn), draft (m)
    ],
    legs_at_sea=[
        VoyageLeg(10, 10, 7),
        VoyageLeg(20, 10, 6),
    ],
)


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


def test_estimate_auxiliary_power_demand():
    # Auxiliary power demand increases with size
    vessel_data_small = replace(DUMMY_VESSEL_DATA, type="oil_tanker", size=5_000)
    pd_1a, pd_1b = estimate_auxiliary_power_demand(vessel_data_small, "at_berth")
    vessel_data_large = replace(DUMMY_VESSEL_DATA, type="oil_tanker", size=20_000)
    pd_2a, pd_2b = estimate_auxiliary_power_demand(vessel_data_large, "at_berth")
    assert pd_2a > pd_1a
    assert pd_2b > pd_1b
    assert pd_1a == 375
    assert pd_1b == 750


def test_estimate_propulsion_engine_load():
    # Engine load increases with speed
    el_1 = estimate_propulsion_engine_load(0, 7, DUMMY_VESSEL_DATA, delta_w=0.8)
    el_2 = estimate_propulsion_engine_load(10, 7, DUMMY_VESSEL_DATA, delta_w=0.8)
    assert el_1 < el_2

    # Engine load increases with draft
    el_1 = estimate_propulsion_engine_load(10, 6, DUMMY_VESSEL_DATA, delta_w=0.8)
    el_2 = estimate_propulsion_engine_load(10, 8, DUMMY_VESSEL_DATA, delta_w=0.8)
    assert el_1 < el_2

    # Speed must be between 0 kn and 110% the design speed
    with raises(ValueError) as info:
        estimate_propulsion_engine_load(
            DUMMY_VESSEL_DATA.design_speed_kn * 1.1 + 0.1, 7, DUMMY_VESSEL_DATA
        )
    assert "speed" in str(info)
    with raises(ValueError) as info:
        estimate_propulsion_engine_load(-0.01, 7, DUMMY_VESSEL_DATA)
    assert "speed" in str(info)

    # Draft must be between 30% and 150% the design draft
    with raises(ValueError) as info:
        estimate_propulsion_engine_load(
            6, 0.29 * DUMMY_VESSEL_DATA.design_draft_m, DUMMY_VESSEL_DATA
        )
    assert "draft" in str(info)
    with raises(ValueError) as info:
        estimate_propulsion_engine_load(
            6, 1.51 * DUMMY_VESSEL_DATA.design_draft_m, DUMMY_VESSEL_DATA
        )
    assert "draft" in str(info)


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


def test_estimate_fuel_consumption():
    vp0 = VoyageProfile(
        time_at_berth_h=0,
        time_anchored_h=0,
        legs_manoeuvring=[],
        legs_at_sea=[],
    )
    fc_ = estimate_fuel_consumption(DUMMY_VESSEL_DATA, vp0)
    assert fc_["total_kg"] == 0
    assert max(fc_["at_berth"].values()) == 0
    assert max(fc_["anchored"].values()) == 0
    assert max(fc_["manoeuvring"].values()) == 0
    assert max(fc_["at_sea"].values()) == 0

    design_draft = DUMMY_VESSEL_DATA.design_draft_m
    vp1 = VoyageProfile(
        time_at_berth_h=10,
        time_anchored_h=10,
        legs_manoeuvring=[
            VoyageLeg(10, 5, design_draft),
            VoyageLeg(10, 10, design_draft),
        ],
        legs_at_sea=[
            VoyageLeg(5, 5, design_draft),
            VoyageLeg(10, 10, design_draft),
        ],
    )

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


def test_estimate_propulsion_engine_sfc():
    # Without a custom curve, the resolver reproduces the IMO model exactly.
    load = 0.6
    expected_imo = estimate_specific_fuel_consumption(load, "MSD", "MDO", "after_2000")
    assert estimate_propulsion_engine_sfc(DUMMY_VESSEL_DATA, load) == approx(
        expected_imo
    )

    # With a custom curve, the resolver returns the curve's value.
    vessel = replace(
        DUMMY_VESSEL_DATA, propulsion_engine_sfc_curve=SFCCurve.constant(200)
    )
    assert estimate_propulsion_engine_sfc(vessel, load) == approx(0.200)


def test_custom_sfc_curve_changes_propulsion_fuel_consumption():
    # A custom curve overrides the IMO SFC model for the propulsion engines.
    fc_imo = estimate_fuel_consumption(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)

    # A deliberately high flat SFC must increase propulsion fuel consumption.
    vessel_high = replace(
        DUMMY_VESSEL_DATA, propulsion_engine_sfc_curve=SFCCurve.constant(500)
    )
    fc_high = estimate_fuel_consumption(vessel_high, DUMMY_VOYAGE_PROFILE)

    assert (
        fc_high["at_sea"]["propulsion_engines_kg"]
        > fc_imo["at_sea"]["propulsion_engines_kg"]
    )
    # Auxiliary engines still use the IMO model, so they are unaffected.
    assert fc_high["at_sea"]["auxiliary_engines_kg"] == approx(
        fc_imo["at_sea"]["auxiliary_engines_kg"]
    )


def test_custom_curve_matching_imo_reproduces_fuel_consumption():
    # A custom curve that mirrors the IMO model reproduces the IMO result.
    imo_curve = SFCCurve.from_callable(
        lambda load: estimate_specific_fuel_consumption(
            load, "MSD", "MDO", "after_2000"
        ),
        units="kg/kWh",
    )
    vessel = replace(DUMMY_VESSEL_DATA, propulsion_engine_sfc_curve=imo_curve)

    fc_custom = estimate_fuel_consumption(vessel, DUMMY_VOYAGE_PROFILE)
    fc_imo = estimate_fuel_consumption(DUMMY_VESSEL_DATA, DUMMY_VOYAGE_PROFILE)

    assert fc_custom["at_sea"]["propulsion_engines_kg"] == approx(
        fc_imo["at_sea"]["propulsion_engines_kg"]
    )
