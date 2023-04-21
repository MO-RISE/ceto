from datetime import datetime

import ceto.ais_adapter as cais
from ceto.imo import verify_vessel_data

import pytest


def test_shiptype_mapping():
    assert cais._map_to_imo_ship_type(30) == "miscellaneous-fishing"
    assert cais._map_to_imo_ship_type(79) == "general_cargo"
    assert cais._map_to_imo_ship_type(85) == "oil_tanker"

    with pytest.warns():
        assert cais._map_to_imo_ship_type(32121) == "service-other"


def test_dims_validation():
    assert cais._validate_dimensions(100, 100, 25, 25)
    assert not cais._validate_dimensions(25, 25, 25, 25)
    assert not cais._validate_dimensions(2, 2, 25, 25)
    assert not cais._validate_dimensions(250, 250, 25, 25)
    assert not cais._validate_dimensions(100, 100, 40, 40)


def test_guesstimate_block_coefficient():
    assert cais._guesstimate_block_coefficient("service-other") == 0.65
    with pytest.raises(ValueError):
        cais._guesstimate_block_coefficient("mumbo-jumbo")


def test_guestimate_design_draft():
    assert cais._guesstimate_design_draft(2, 30) == 30 / 3.25
    assert cais._guesstimate_design_draft(10, 30) == 10


def test_guesstimate_design_speed():
    assert 13 <= cais._guesstimate_design_speed(200, "oil_tanker", 0) <= 16
    assert 20 <= cais._guesstimate_design_speed(300, "general_cargo", 0) <= 24
    assert 12 <= cais._guesstimate_design_speed(30, "ferry-pax", 0) <= 15
    assert cais._guesstimate_design_speed(200, "oil_tanker", 18) == 18


def test_guesstimate_number_of_engines():
    assert cais._guesstimate_number_of_engines("ferry-pax") == 2
    assert cais._guesstimate_number_of_engines("ferry-ropax") == 2
    assert cais._guesstimate_number_of_engines("anything-else") == 1


def test_guesstimate_engine_MCR():
    assert 6_000 <= cais._guesstimate_engine_MCR("oil_tanker", 50_000, 15) <= 10_000
    assert 10_000 <= cais._guesstimate_engine_MCR("general_cargo", 50_000, 25) <= 15_000
    assert 1_500 <= cais._guesstimate_engine_MCR("service-other", 5_000, 18) <= 3_000


def test_guesstimate_engine_type():
    assert cais._guesstimate_engine_type("general_cargo") == "SSD"
    assert cais._guesstimate_engine_type("liquified_gas_tanker") == "LNG-Otto-MS"

    assert cais._guesstimate_engine_type("anything-else") == "HSD"


def test_guesstimate_engine_fuel_type():
    assert cais._guesstimate_engine_fuel_type("liquified_gas_tanker", 0.0, 0.0) == "LNG"

    # Assumption: We are inside an ECA area
    assert cais._guesstimate_engine_fuel_type("anything-else", 0.0, 0.0) == "MDO"


def test_guesstimate_DWT():
    assert cais._guesstimate_vessel_size_as_DeadWeightTonnage(
        "oil_tanker", 200, 30, 7
    ) == 0.83 * (cais._guesstimate_block_coefficient("oil_tanker") * 200 * 30 * 7)


def test_guesstimate_GT():
    dwt = cais._guesstimate_vessel_size_as_DeadWeightTonnage("oil_tanker", 200, 30, 7)

    assert cais._guesstimate_vessel_size_as_GrossTonnage(
        "oil_tanker", dwt
    ) / dwt == pytest.approx(0.5354)

    dwt = cais._guesstimate_vessel_size_as_DeadWeightTonnage(
        "service-other", 200, 30, 7
    )

    assert cais._guesstimate_vessel_size_as_GrossTonnage(
        "service-other", dwt
    ) / dwt == pytest.approx(2.0)


def test_guesstimate_CBM():
    assert cais._guesstimate_vessel_size_as_CubicMetres(
        "oil_tanker", 50_000
    ) == pytest.approx(
        0.8 * cais._guesstimate_vessel_size_as_GrossTonnage("oil_tanker", 50_000)
    )


def test_guesstimate_vessel_data():
    vdata = cais.guesstimate_vessel_data(83, 180, 20, 15, 15, 11.7, 6, 0.0, 0.0)

    assert vdata["type"] == "oil_tanker"
    assert vdata["length"] == 200
    assert vdata["beam"] == 30
    assert vdata["design_draft"] != 6
    assert vdata["number_of_propulsion_engines"] == 1
    assert vdata["propulsion_engine_type"] == "SSD"
    assert vdata["propulsion_engine_fuel_type"] == "MDO"

    assert vdata["double_ended"] == False
    assert vdata["propulsion_engine_age"] == "after_2000"

    assert "size" in vdata.keys()
    assert "design_speed" in vdata.keys()
    assert "propulsion_engine_power" in vdata.keys()

    assert verify_vessel_data(vdata) is None  # Will raise if vdata is not ok


def test_guesstimate_voyage_data():
    vdata = cais.guesstimate_voyage_data(
        56,
        12,
        56,
        11,
        9.5,
        10.5,
        18,
        20,
        datetime.fromtimestamp(0),
        datetime.fromtimestamp(10_000 / 3600),
        23,
    )

    assert "time_anchored" in vdata.keys()
    assert "time_at_berth" in vdata.keys()
    assert "legs_manoeuvring" in vdata.keys()
    assert "legs_at_sea" in vdata.keys()

    print(vdata)

    assert vdata["time_anchored"] == 0
    assert vdata["time_at_berth"] == 0
    assert len(vdata["legs_manoeuvring"]) == 0
    assert len(vdata["legs_at_sea"]) == 1
