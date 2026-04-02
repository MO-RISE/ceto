"""
Estimates of GHG emissions (CO2, CH4, N2O) from vessel fuel consumption.

All emission factors are loaded from YAML data files in cetos/data/ which
include full provenance metadata (source documents, dates, URLs, pages).
See cetos/data/emissions_factors.yaml for factor values and their sources.
"""

from cetos.factors import (
    CO2_FACTORS,
    GWP_CH4,
    GWP_N2O,
    LCV,
    NOX_FACTORS,
    PM_FACTORS,
    SOX_FACTORS,
    WTT_FACTORS,
    _CH4_LBSI,
    _CH4_LNG_NEGLIGIBLE,
    _CH4_LNG_OTTO_MS,
    _CH4_OIL,
    _N2O_LNG,
    _N2O_OIL,
)
from cetos.imo import estimate_energy_consumption, estimate_fuel_consumption
from cetos.models import ENGINE_TYPES, FUEL_TYPES, VesselData, VoyageProfile
from cetos.utils import verify_set

# Build CH4 factors as (engine_type, fuel_type) lookup
CH4_FACTORS = {}
for _et in ENGINE_TYPES:
    for _ft in FUEL_TYPES:
        if _ft == "LNG":
            if _et == "LNG-Otto-MS":
                CH4_FACTORS[(_et, _ft)] = _CH4_LNG_OTTO_MS
            elif _et == "LBSI":
                CH4_FACTORS[(_et, _ft)] = _CH4_LBSI
            elif _et in ("gas_turbine", "steam_turbine"):
                CH4_FACTORS[(_et, _ft)] = _CH4_LNG_NEGLIGIBLE
            else:
                CH4_FACTORS[(_et, _ft)] = _CH4_OIL
        else:
            CH4_FACTORS[(_et, _ft)] = _CH4_OIL

# Build N2O factors as (engine_type, fuel_type) lookup
N2O_FACTORS = {}
for _et in ENGINE_TYPES:
    for _ft in FUEL_TYPES:
        if _ft == "LNG" and _et in ("LNG-Otto-MS", "LBSI"):
            N2O_FACTORS[(_et, _ft)] = _N2O_LNG
        else:
            N2O_FACTORS[(_et, _ft)] = _N2O_OIL


def estimate_co2_emissions_from_fuel_consumption(fuel_mass_kg, fuel_type):
    """Estimate CO2 emissions from a given mass of fuel.

    Arguments:
    ----------

        fuel_mass_kg: float
            Mass of fuel consumed (kg).

        fuel_type: string
            Type of fuel. Possible values: HFO, MDO, LNG, MeOH.

    Returns:
    --------

        float
            Mass of CO2 produced (kg).

    Source:
        IMO MEPC.308(73), Table 1.
    """
    verify_set("fuel_type", fuel_type, FUEL_TYPES)
    return fuel_mass_kg * CO2_FACTORS[fuel_type]


def estimate_co2_emissions(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate CO2 emissions for a vessel voyage.

    Calculates fuel consumption using the IMO Fourth GHG Study methodology,
    then applies the CO2 conversion factor for the vessel's fuel type.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile.

        include_steam_boilers (optional): boolean
            If True, the fuel consumption of the steam boilers is included.
            Defaults to True.

        limit_7_percent (optional): boolean
            If True, when the engine load is less than 7% the fuel consumption
            is neglected. Defaults to True.

        delta_w (optional): float
            Speed-power correction factor. See estimate_fuel_consumption for
            details. Defaults to None.

    Returns:
    --------

        Dict
            Total CO2 emissions (kg) and breakdown by operation mode, along
            with the underlying fuel consumption.

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.
        [2] IMO MEPC.308(73), Table 1 — CO2 emission factors.
    """
    fuel_type = vessel_data.propulsion_engine_fuel_type
    co2_factor = CO2_FACTORS[fuel_type]

    fc = estimate_fuel_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    result = {
        "total_kg_co2": fc["total_kg"] * co2_factor,
        "total_fuel_kg": fc["total_kg"],
        "fuel_type": fuel_type,
        "co2_factor": co2_factor,
    }

    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        result[mode] = {
            "co2_kg": fc[mode]["subtotal_kg"] * co2_factor,
            "fuel_kg": fc[mode]["subtotal_kg"],
        }

    return result


def estimate_ghg_emissions(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate total GHG emissions (CO2, CH4, N2O) for a vessel voyage.

    Calculates fuel consumption, then applies emission factors for CO2, CH4,
    and N2O. Returns total CO2-equivalent using IPCC AR5 GWP values.

    CH4 emissions are particularly important for LNG-fueled vessels due to
    methane slip (incomplete combustion). N2O has high GWP (265) but very
    small mass emissions.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile.

        include_steam_boilers (optional): boolean
            If True, the fuel consumption of the steam boilers is included.
            Defaults to True.

        limit_7_percent (optional): boolean
            If True, when the engine load is less than 7% the fuel consumption
            is neglected. Defaults to True.

        delta_w (optional): float
            Speed-power correction factor. See estimate_fuel_consumption for
            details. Defaults to None.

    Returns:
    --------

        Dict
            Total emissions (kg) for CO2, CH4, N2O and CO2-equivalent,
            with breakdown by operation mode.

    Source:
    -------

        [1] IMO. Fourth IMO GHG Study 2020. IMO.
        [2] IMO MEPC.308(73), Table 1 — CO2 emission factors.
        [3] FuelEU Maritime Annex II — CH4 and N2O emission factors.
        [4] IPCC AR5 — Global Warming Potentials.
    """
    fuel_type = vessel_data.propulsion_engine_fuel_type
    engine_type = vessel_data.propulsion_engine_type

    co2_factor = CO2_FACTORS[fuel_type]
    ch4_factor = CH4_FACTORS[(engine_type, fuel_type)]
    n2o_factor = N2O_FACTORS[(engine_type, fuel_type)]

    fc = estimate_fuel_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    def _calc_mode(fuel_kg):
        co2 = fuel_kg * co2_factor
        ch4 = fuel_kg * ch4_factor
        n2o = fuel_kg * n2o_factor
        co2eq = co2 + ch4 * GWP_CH4 + n2o * GWP_N2O
        return {
            "fuel_kg": fuel_kg,
            "co2_kg": co2,
            "ch4_kg": ch4,
            "n2o_kg": n2o,
            "co2eq_kg": co2eq,
        }

    result = {}
    total_co2 = 0.0
    total_ch4 = 0.0
    total_n2o = 0.0
    total_co2eq = 0.0

    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        mode_result = _calc_mode(fc[mode]["subtotal_kg"])
        result[mode] = mode_result
        total_co2 += mode_result["co2_kg"]
        total_ch4 += mode_result["ch4_kg"]
        total_n2o += mode_result["n2o_kg"]
        total_co2eq += mode_result["co2eq_kg"]

    result["total_kg_co2"] = total_co2
    result["total_kg_ch4"] = total_ch4
    result["total_kg_n2o"] = total_n2o
    result["total_kg_co2eq"] = total_co2eq
    result["total_fuel_kg"] = fc["total_kg"]
    result["fuel_type"] = fuel_type
    result["engine_type"] = engine_type

    return result


def estimate_well_to_wake_emissions(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
    wtt_override_gco2eq_per_mj=None,
):
    """Estimate well-to-wake GHG emissions for a vessel voyage.

    Combines Tank-to-Wake (TtW) emissions from combustion with Well-to-Tank
    (WtT) upstream emissions from fuel production. Returns the GHG intensity
    in gCO2eq/MJ as required by FuelEU Maritime.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile.

        include_steam_boilers (optional): boolean
            Defaults to True.

        limit_7_percent (optional): boolean
            Defaults to True.

        delta_w (optional): float
            Speed-power correction factor. Defaults to None.

        wtt_override_gco2eq_per_mj (optional): float
            Override the default WtT factor (gCO2eq/MJ). Use for renewable
            fuels with certified WtT values that differ from fossil defaults.
            Defaults to None (uses FuelEU Maritime Annex II defaults).

    Returns:
    --------

        Dict
            Well-to-wake emissions breakdown including WtT, TtW, total WtW,
            GHG intensity (gCO2eq/MJ), and per-mode breakdown.

    Source:
    -------

        [1] FuelEU Maritime Annex II — WtT default emission factors.
        [2] IMO MEPC.308(73) — CO2 emission factors and LCV values.
        [3] FuelEU Maritime Annex II — CH4 and N2O factors.
    """
    fuel_type = vessel_data.propulsion_engine_fuel_type
    lcv = LCV[fuel_type]

    # WtT factor: use override if provided, otherwise use default
    if wtt_override_gco2eq_per_mj is not None:
        wtt_gco2eq_per_mj = wtt_override_gco2eq_per_mj
    else:
        wtt_gco2eq_per_mj = WTT_FACTORS[fuel_type]

    # WtT factor in kg CO2eq per kg fuel = gCO2eq/MJ * MJ/kg / 1000
    wtt_kg_co2eq_per_kg_fuel = wtt_gco2eq_per_mj * lcv / 1000.0

    # Get TtW emissions (CO2 + CH4 + N2O as CO2eq)
    ghg = estimate_ghg_emissions(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    total_fuel_kg = ghg["total_fuel_kg"]
    total_energy_mj = total_fuel_kg * lcv

    # WtT total
    wtt_total = total_fuel_kg * wtt_kg_co2eq_per_kg_fuel

    # TtW total (from GHG calculation — CO2eq including CH4 and N2O)
    ttw_total = ghg["total_kg_co2eq"]

    # WtW total
    wtw_total = wtt_total + ttw_total

    # GHG intensity in gCO2eq/MJ (the FuelEU Maritime metric)
    if total_energy_mj > 0:
        ghg_intensity = (wtw_total * 1000.0) / total_energy_mj
    else:
        ghg_intensity = 0.0

    result = {
        "wtt_kg_co2eq": wtt_total,
        "ttw_kg_co2eq": ttw_total,
        "wtw_kg_co2eq": wtw_total,
        "ghg_intensity_gco2eq_per_mj": ghg_intensity,
        "total_fuel_kg": total_fuel_kg,
        "total_energy_mj": total_energy_mj,
        "fuel_type": fuel_type,
        "wtt_factor_gco2eq_per_mj": wtt_gco2eq_per_mj,
        "ttw_kg_co2": ghg["total_kg_co2"],
        "ttw_kg_ch4": ghg["total_kg_ch4"],
        "ttw_kg_n2o": ghg["total_kg_n2o"],
    }

    # Per-mode breakdown
    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        fuel_kg = ghg[mode]["fuel_kg"]
        wtt_mode = fuel_kg * wtt_kg_co2eq_per_kg_fuel
        ttw_mode = ghg[mode]["co2eq_kg"]
        result[mode] = {
            "wtt_co2eq_kg": wtt_mode,
            "ttw_co2eq_kg": ttw_mode,
            "wtw_co2eq_kg": wtt_mode + ttw_mode,
            "fuel_kg": fuel_kg,
        }

    return result


def estimate_air_pollutant_emissions(
    vessel_data: VesselData,
    voyage_profile: VoyageProfile,
    include_steam_boilers=True,
    limit_7_percent=True,
    delta_w=None,
):
    """Estimate air pollutant emissions (NOx, SOx, PM) for a vessel voyage.

    NOx is energy-based (g/kWh) and depends on engine type and age (IMO Tier).
    SOx is fuel-mass-based and depends on fuel sulfur content.
    PM is fuel-mass-based and depends on fuel type.

    Arguments:
    ----------

        vessel_data: VesselData
            VesselData instance describing the vessel.

        voyage_profile: VoyageProfile
            VoyageProfile instance describing the voyage profile.

        include_steam_boilers (optional): boolean
            Defaults to True.

        limit_7_percent (optional): boolean
            Defaults to True.

        delta_w (optional): float
            Speed-power correction factor. Defaults to None.

    Returns:
    --------

        Dict
            Total NOx, SOx, and PM emissions (kg) with breakdown by mode.

    Source:
    -------

        [1] IMO NOx Technical Code — NOx emission factors.
        [2] IMO MARPOL Annex VI — SOx / sulfur limits.
        [3] IMO Fourth GHG Study 2020 — PM emission factors.
        [4] EMEP/EEA Air Pollutant Emission Inventory Guidebook.
    """
    fuel_type = vessel_data.propulsion_engine_fuel_type
    engine_type = vessel_data.propulsion_engine_type
    engine_age = vessel_data.propulsion_engine_age

    nox_g_per_kwh = NOX_FACTORS[(engine_type, engine_age)]
    sox_g_per_kg_fuel = SOX_FACTORS[fuel_type]
    pm_g_per_kg_fuel = PM_FACTORS[fuel_type]

    # Get fuel consumption (for SOx and PM)
    fc = estimate_fuel_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    # Get energy consumption (for NOx)
    ec = estimate_energy_consumption(
        vessel_data,
        voyage_profile,
        include_steam_boilers=include_steam_boilers,
        limit_7_percent=limit_7_percent,
        delta_w=delta_w,
    )

    result = {}
    total_nox = 0.0
    total_sox = 0.0
    total_pm = 0.0

    for mode in ["at_berth", "anchored", "manoeuvring", "at_sea"]:
        fuel_kg = fc[mode]["subtotal_kg"]
        energy_kwh = ec[mode]["subtotal_kwh"]

        nox_kg = nox_g_per_kwh * energy_kwh / 1000.0
        sox_kg = sox_g_per_kg_fuel * fuel_kg / 1000.0
        pm_kg = pm_g_per_kg_fuel * fuel_kg / 1000.0

        result[mode] = {
            "nox_kg": nox_kg,
            "sox_kg": sox_kg,
            "pm_kg": pm_kg,
            "fuel_kg": fuel_kg,
            "energy_kwh": energy_kwh,
        }
        total_nox += nox_kg
        total_sox += sox_kg
        total_pm += pm_kg

    result["total_kg_nox"] = total_nox
    result["total_kg_sox"] = total_sox
    result["total_kg_pm"] = total_pm
    result["total_fuel_kg"] = fc["total_kg"]
    result["fuel_type"] = fuel_type
    result["engine_type"] = engine_type

    return result
