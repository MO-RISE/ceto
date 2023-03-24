from pytest import raises, approx
from ceto.energy_systems import *


def test_suggest_alternative_energy_systems():
    vessel_data = {}
    voyage_profile = {}
    with raises(KeyError) as info:
        suggest_alternative_energy_systems(vessel_data, voyage_profile)