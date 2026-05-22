from dataclasses import replace

from pytest import raises

from cetos.models import VesselData, VoyageLeg, VoyageProfile
from cetos.sfc import SFCCurve

VALID_VESSEL_DATA = VesselData(
    length_m=100,
    beam_m=20,
    design_speed_kn=10,
    design_draft_m=7,
    type="offshore",
    size=None,
    double_ended=False,
    number_of_propulsion_engines=1,
    propulsion_engine_power_kw=1_000,
    propulsion_engine_type="MSD",
    propulsion_engine_age="after_2000",
    propulsion_engine_fuel_type="MDO",
)


def test_vessel_data_valid_creation():
    """Test that valid VesselData can be created without errors."""
    vessel = VALID_VESSEL_DATA
    assert vessel.length_m == 100
    assert vessel.beam_m == 20
    assert vessel.design_speed_kn == 10
    assert vessel.propulsion_engine_type == "MSD"


def test_vessel_data_invalid_fuel_type():
    """Test that invalid fuel type raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, propulsion_engine_fuel_type="blue")
    assert "propulsion_engine_fuel_type" in str(info)


def test_vessel_data_invalid_engine_type():
    """Test that invalid engine type raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, propulsion_engine_type="blue")
    assert "propulsion_engine_type" in str(info)


def test_vessel_data_invalid_engine_age():
    """Test that invalid engine age raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, propulsion_engine_age="ancient")
    assert "propulsion_engine_age" in str(info)


def test_vessel_data_invalid_vessel_type():
    """Test that invalid vessel type raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, type="submarine")
    assert "type" in str(info)


def test_vessel_data_invalid_length():
    """Test that out-of-range length raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, length_m=1.0)
    assert "length_m" in str(info)

    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, length_m=500.0)
    assert "length_m" in str(info)


def test_vessel_data_invalid_engine_power():
    """Test that out-of-range engine power raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, propulsion_engine_power_kw=1.0)
    assert "propulsion_engine_power_kw" in str(info)


def test_vessel_data_invalid_number_of_engines():
    """Test that invalid number of engines raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, number_of_propulsion_engines=5)
    assert "number_of_propulsion_engines" in str(info)


def test_vessel_data_invalid_sfc_curve():
    """Test that a non-SFCCurve propulsion SFC curve raises ValueError."""
    with raises(ValueError) as info:
        replace(VALID_VESSEL_DATA, propulsion_engine_sfc_curve=lambda load: 0.18)
    assert "propulsion_engine_sfc_curve" in str(info)


def test_vessel_data_accepts_sfc_curve():
    """Test that an SFCCurve is accepted as the propulsion SFC curve."""
    vessel = replace(
        VALID_VESSEL_DATA, propulsion_engine_sfc_curve=SFCCurve.constant(190)
    )
    assert vessel.propulsion_engine_sfc_curve is not None


def test_voyage_leg_valid_creation():
    """Test that valid VoyageLeg can be created without errors."""
    leg = VoyageLeg(distance_nm=10, speed_kn=10, draft_m=7)
    assert leg.distance_nm == 10
    assert leg.speed_kn == 10
    assert leg.draft_m == 7


def test_voyage_leg_invalid_speed():
    """Test that out-of-range speed raises ValueError."""
    with raises(ValueError) as info:
        VoyageLeg(distance_nm=10, speed_kn=0.0, draft_m=7)
    assert "speed_kn" in str(info)

    with raises(ValueError) as info:
        VoyageLeg(distance_nm=10, speed_kn=60, draft_m=7)
    assert "speed_kn" in str(info)


def test_voyage_leg_invalid_draft():
    """Test that out-of-range draft raises ValueError."""
    with raises(ValueError) as info:
        VoyageLeg(distance_nm=10, speed_kn=10, draft_m=0.0)
    assert "draft_m" in str(info)

    with raises(ValueError) as info:
        VoyageLeg(distance_nm=10, speed_kn=10, draft_m=30)
    assert "draft_m" in str(info)


def test_voyage_profile_valid_creation():
    """Test that valid VoyageProfile can be created without errors."""
    profile = VoyageProfile(
        time_anchored_h=10.0,
        time_at_berth_h=10.0,
        legs_manoeuvring=[VoyageLeg(10, 10, 7)],
        legs_at_sea=[VoyageLeg(10, 10, 7), VoyageLeg(20, 10, 6)],
    )
    assert profile.time_anchored_h == 10.0
    assert profile.time_at_berth_h == 10.0
    assert len(profile.legs_manoeuvring) == 1
    assert len(profile.legs_at_sea) == 2


def test_voyage_profile_with_tuples():
    """Test that VoyageProfile accepts raw tuples and converts them to VoyageLeg."""
    profile = VoyageProfile(
        time_anchored_h=5.0,
        time_at_berth_h=5.0,
        legs_manoeuvring=[(10, 10, 7)],
        legs_at_sea=[(20, 8, 6)],
    )
    assert isinstance(profile.legs_manoeuvring[0], VoyageLeg)
    assert isinstance(profile.legs_at_sea[0], VoyageLeg)
    assert profile.legs_manoeuvring[0].distance_nm == 10


def test_voyage_profile_empty_legs():
    """Test that VoyageProfile can have empty legs lists."""
    profile = VoyageProfile(
        time_anchored_h=0.0,
        time_at_berth_h=0.0,
        legs_manoeuvring=[],
        legs_at_sea=[],
    )
    assert len(profile.legs_manoeuvring) == 0
    assert len(profile.legs_at_sea) == 0


def test_voyage_profile_invalid_time():
    """Test that negative time values raise ValueError."""
    with raises(ValueError) as info:
        VoyageProfile(
            time_anchored_h=-1.0,
            time_at_berth_h=0.0,
            legs_manoeuvring=[],
            legs_at_sea=[],
        )
    assert "time_anchored_h" in str(info)
