from pytest import raises, approx
from ceto.energy_systems import *


def test_suggest_alternative_energy_systems():
    vessel_data = {}
    voyage_profile = {}
    response = suggest_alternative_energy_systems(vessel_data, voyage_profile)
    assert response.get("error")