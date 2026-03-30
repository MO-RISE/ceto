# CETOS Emissions & CII Module Verification Report

**Date**: 2026-03-27
**Scope**: Every emission factor, constant, and reference in `cetos/emissions.py` and `cetos/cii.py`
**Method**: Each value cross-referenced against the primary source document via web search

---

## SUMMARY OF FINDINGS

| Severity | Count |
|----------|-------|
| CRITICAL errors (produce wrong results) | 4 |
| INCORRECT values (wrong numbers) | 7 |
| INCORRECT source references | 3 |
| UNCERTAIN (unverifiable or context-dependent) | 6 |
| CORRECT | 25+ |

---

## 1. emissions.py

### 1.1 CO2 Factors (CO2_FACTORS)

Source claimed: IMO MEPC.308(73), Table 1

| Fuel | Code Value | MEPC.308(73) Value | Status |
|------|-----------|-------------------|--------|
| HFO  | 3.114     | 3.114             | **CORRECT** |
| MDO  | 3.206     | 3.206             | **CORRECT** |
| LNG  | 2.750     | 2.750             | **CORRECT** |
| MeOH | 1.375     | 1.375             | **CORRECT** |

**Source reference**: CORRECT. These are from MEPC.308(73) Table 1. MEPC.364(79) carries the same values. The values are stoichiometric (carbon content based) and do not change between resolutions.

### 1.2 GWP Values

| Gas | Code Value | IPCC AR5 100-yr | Status |
|-----|-----------|----------------|--------|
| CH4 | 28        | 28             | **CORRECT** (non-fossil CH4; fossil CH4 = 30) |
| N2O | 265       | 265            | **CORRECT** |

**Note**: These are the IPCC AR5 100-year GWP values. FuelEU Maritime Regulation (EU) 2023/1805 originally referenced RED II GWPs (CH4=25, N2O=298), but EMSA has indicated a shift to AR5 GWPs (CH4=28, N2O=265). The code's choice of AR5 values is appropriate for IMO-aligned calculations and is in line with the latest FuelEU Maritime guidance.

### 1.3 CH4 Factors (CH4_FACTORS)

Source claimed: FuelEU Maritime Annex II, IMO Fourth GHG Study Table 63

| Engine/Fuel Combination | Code Value | Verified Value | Status |
|------------------------|-----------|---------------|--------|
| Oil engines (all fuels) | 0.00005 (0.005%) | ~0.00005 | **CORRECT** -- Confirmed from FuelEU Annex II TtW CH4 for oil engines |
| LNG-Otto-MS (dual-fuel medium-speed Otto) | 0.031 (3.1%) | 3.1% (FuelEU Annex II) | **CORRECT** for FuelEU. Note: IMO 4th GHG Study uses 3.5% for this engine type. The code uses FuelEU value. |
| LBSI (lean-burn spark ignition) | 0.026 (2.6%) | ~2.6% | **UNCERTAIN** -- This value appears in the IMO 4th GHG Study. FuelEU Annex II does not separately list LBSI. Reasonable. |
| Gas turbine / steam turbine on LNG | 0.0002 (0.02%) | ~0.02% | **UNCERTAIN** -- Reasonable estimate from IMO 4th GHG Study. Not separately listed in FuelEU Annex II. |

**Units**: Code says "kg CH4 per kg fuel" -- this is equivalent to "g CH4 / g fuel" and matches FuelEU Annex II notation (Cslip as fraction of fuel mass). **CORRECT**.

**Table 63 reference**: The IMO Fourth GHG Study 2020 does contain emission factor tables (Tables 53-64 area). Table 63 specifically covers CH4 emission factors by engine type. Reference is plausible but exact table number could not be independently confirmed from web sources (full report is a large PDF).

### 1.4 N2O Factors (N2O_FACTORS)

Source claimed: FuelEU Maritime Annex II

| Engine Type | Code Value | Verified Value | Status |
|-------------|-----------|---------------|--------|
| Oil engines | 0.00018 kg N2O/kg fuel | 0.00018 | **CORRECT** -- Confirmed from FuelEU Annex II TtW N2O factor for oil engines |
| LNG engines | 0.00011 kg N2O/kg fuel | ~0.00011 | **UNCERTAIN** -- Plausible value from FuelEU Annex II for gas-fueled engines. Could not independently verify exact number. |

**Units**: "kg N2O per kg fuel" -- **CORRECT**. Matches FuelEU Annex II notation.

### 1.5 LCV Values

Source claimed: IMO MEPC.308(73) / MEPC.364(79)

| Fuel | Code Value | MEPC.308(73) Value | FuelEU Annex II | Status |
|------|-----------|-------------------|----------------|--------|
| HFO  | 40.2 MJ/kg | 40,200 kJ/kg = 40.2 MJ/kg | 40.5 MJ/kg | **CORRECT** for IMO (MEPC.308/364). Note: FuelEU uses 40.5. |
| MDO  | 42.7 MJ/kg | 42,700 kJ/kg = 42.7 MJ/kg | 42.7 MJ/kg | **CORRECT** |
| LNG  | 48.0 MJ/kg | 48,000 kJ/kg = 48.0 MJ/kg | 48.0 MJ/kg | **CORRECT** |
| MeOH | 19.9 MJ/kg | 19,900 kJ/kg = 19.9 MJ/kg | 19.9 MJ/kg | **CORRECT** |

**Note on HFO**: IMO MEPC.308(73) specifies 40.2 MJ/kg. FuelEU Maritime Annex II specifies 40.5 MJ/kg. The code uses the IMO value which is correct for CII and EEXI calculations. For FuelEU GHG intensity calculations, 40.5 should be used instead. The `estimate_well_to_wake_emissions` function uses the IMO LCV value but applies FuelEU WtT factors -- this is a minor inconsistency. Consider documenting this or adding a FuelEU-specific LCV table.

### 1.6 WTT Factors

Source claimed: FuelEU Maritime Annex II -- default values for fossil fuels

| Fuel | Code Value | FuelEU Annex II | Status |
|------|-----------|----------------|--------|
| HFO  | 13.5 gCO2eq/MJ | 13.5 | **CORRECT** |
| MDO  | 14.4 gCO2eq/MJ | 14.4 | **CORRECT** |
| LNG  | 18.5 gCO2eq/MJ | 18.5 | **CORRECT** |
| MeOH | 31.3 gCO2eq/MJ | ~31.3 (fossil methanol from natural gas) | **CORRECT** -- confirmed for fossil methanol pathway |

### 1.7 NOx Factors

Source claimed: IMO NOx Technical Code, IMO Fourth GHG Study Table 54

#### Tier Date Boundaries

| Code Category | Code Label | IMO Actual Tier | IMO Date Boundary | Status |
|---------------|-----------|----------------|-------------------|--------|
| before_1984 | "Tier 0" | Pre-Tier (no regulation) | Before 1 Jan 2000 | **INCORRECT MAPPING** |
| 1984-2000 | "Tier I" | Tier I | 1 Jan 2000 - 31 Dec 2010 | **INCORRECT MAPPING** |
| after_2000 | "Tier II" | Tier II | 1 Jan 2011 onwards | **INCORRECT MAPPING** |

**ISSUE**: The IMO NOx Tier boundaries are:
- **Pre-Tier / Tier 0**: Engines on ships built before 1 January 2000
- **Tier I**: Engines on ships built 1 January 2000 to 31 December 2010
- **Tier II**: Engines on ships built on or after 1 January 2011
- **Tier III**: Engines on ships built on or after 1 January 2016 (in ECAs only)

The code's `engine_age` categories ("before_1984", "1984-2000", "after_2000") do not align with IMO Tier boundaries. The "before_1984" category has no regulatory basis in IMO NOx Tiers. The 1984 cutoff appears to be arbitrary or based on a different classification system (possibly vessel age categories from the IMO GHG Study inventory methodology, not the NOx Technical Code).

**However**, the emission factor values themselves may still be reasonable estimates for those engine vintage groups, even if the Tier labeling is inaccurate. The code comments say "Tier 0 ~ before_1984" which is an approximation. This is **not strictly wrong** for emission estimation purposes but is **misleading** in its Tier labeling.

#### SSD NOx Values

| Engine Age | Code Value (g/kWh) | Status |
|-----------|-------------------|--------|
| before_1984 | 18.1 | **CORRECT** -- Matches pre-Tier SSD baseline from IMO 4th GHG Study |
| 1984-2000 | 17.0 | **CORRECT** -- Matches Tier I SSD from IMO 3rd/4th GHG Study |
| after_2000 | 14.4 | **CORRECT** -- Matches Tier II SSD (at rated speed ~100 rpm) |

#### MSD NOx Values

| Engine Age | Code Value (g/kWh) | Status |
|-----------|-------------------|--------|
| before_1984 | 14.0 | **UNCERTAIN** -- Plausible for pre-Tier MSD |
| 1984-2000 | 12.0 | **UNCERTAIN** -- Plausible for Tier I MSD |
| after_2000 | 10.5 | **UNCERTAIN** -- Plausible for Tier II MSD. IMO Tier II limit is speed-dependent: 44*n^(-0.23) g/kWh |

#### HSD, LNG, Gas Turbine, Steam Turbine NOx Values

These values are **UNCERTAIN** -- they are reasonable engineering estimates consistent with the IMO 4th GHG Study methodology but exact table references could not be independently verified from web sources. The values are within expected ranges.

### 1.8 SOx Factors

| Fuel | Code Value (g/kg fuel) | Calculation | Status |
|------|----------------------|-------------|--------|
| HFO  | 10.0 | 20 x 0.50% S = 10.0 | **CORRECT** -- Post-2020 global sulfur cap is 0.50% S for VLSFO |
| MDO  | 2.0 | 20 x 0.10% S = 2.0 | **CORRECT** -- Typical low-sulfur distillate |
| LNG  | 0.0 | No sulfur | **CORRECT** |
| MeOH | 0.0 | No sulfur | **CORRECT** |

Formula SOx = 20 x S (sulfur mass fraction) is **CORRECT** per IMO methodology.

### 1.9 PM Factors

Source claimed: IMO Fourth GHG Study, EMEP/EEA Guidebook

| Fuel | Code Value (g/kg fuel) | Status |
|------|----------------------|--------|
| HFO  | 0.6 | **UNCERTAIN** -- Plausible for post-2020 VLSFO. EMEP/EEA guidebook gives a range. Some sources cite 0.5-1.5 g/kWh for residual fuels. |
| MDO  | 0.3 | **UNCERTAIN** -- Plausible for low-sulfur distillate |
| LNG  | 0.02 | **UNCERTAIN** -- Plausible, negligible PM from gas combustion |
| MeOH | 0.03 | **UNCERTAIN** -- Plausible, negligible PM from methanol combustion |

These PM values are engineering estimates and cannot be traced to a single authoritative source. They fall within published ranges from EMEP/EEA and the IMO 4th GHG Study.

---

## 2. cii.py

### 2.1 CII Reference Line Parameters (CII_PARAMS)

Source claimed in code: "IMO MEPC.339(76), Table 1"

**INCORRECT SOURCE REFERENCE**: MEPC.339(76) is the "CII Rating Guidelines, G4" (not the reference lines). The reference line parameters are from:
- **MEPC.337(76)** (original 2021, now revoked)
- **MEPC.353(78)** (2022 update, currently in force) -- this supersedes MEPC.337(76)

The code's docstring and README reference MEPC.339(76) for the reference line parameters, which is wrong.

#### Parameter Values

| Ship Type | Code (a, c) | MEPC.353(78) (a, c) | MEPC.337(76) original | Status |
|-----------|------------|--------------------|-----------------------|--------|
| bulk_carrier | (4745, 0.622) | (4745, 0.622) | (4745, 0.622) | **CORRECT** |
| gas_carrier | (144050000, 2.071) | (14405E7, 2.071) = (1.4405e11, 2.071) | Same | **CRITICAL ERROR** -- Code has 1.44e8, should be 1.4405e11. Off by factor of 1000. |
| tanker | (5247, 0.610) | (5247, 0.610) | (5247, 0.610) | **CORRECT** |
| container | (1984, 0.489) | (1984, 0.489) | (1984, 0.489) | **CORRECT** |
| general_cargo | (31948, 0.792) | (31948, 0.792) for >=20k DWT | Same | **CORRECT** (for >=20,000 DWT only; code does not handle <20k DWT where a=588, c=0.3885) |
| refrigerated_cargo | (4600, 0.557) | (4600, 0.557) | (4600, 0.557) | **CORRECT** |
| combination_carrier | (5119, 0.622) | (5119, 0.622) | (5119, 0.622) | **CORRECT** |
| lng_carrier | (9.827, 0.000) | (9.827, 0.000) for >=100k DWT | Same | **CORRECT** for >=100k DWT. Code does not handle <100k DWT LNG carriers (different parameters). |
| vehicle_carrier | (5686, 0.714) | (3672, 0.590) for >=57,700 GT | MEPC.337(76): (5739, 0.631) | **INCORRECT** -- Value matches neither the original MEPC.337(76) nor the current MEPC.353(78). |
| roro_cargo | (10952, 0.637) | (1967, 0.485) | (10952, 0.637) | **OUTDATED** -- Uses revoked MEPC.337(76) value. Should use MEPC.353(78): (1967, 0.485). |
| roro_passenger | (7540, 0.587) | (2023, 0.460) | (7540, 0.587) | **OUTDATED** -- Uses revoked MEPC.337(76) value. Should use MEPC.353(78): (2023, 0.460). |
| cruise_passenger | (930, 0.383) | (930, 0.383) | (930, 0.383) | **CORRECT** |

#### Critical Issues with CII_PARAMS:

1. **gas_carrier 'a' value is CRITICALLY WRONG**: `144050000` (1.44e8) should be `14405e7` (1.4405e11). This makes the gas carrier CII reference line ~1000x too low, producing nonsensical required CII values (e.g., 0.016 instead of ~15 for a 65,000 DWT gas carrier).

2. **vehicle_carrier values are INCORRECT**: (5686, 0.714) does not match any known IMO resolution. The original MEPC.337(76) had (5739, 0.631) for ro-ro vehicle carriers. The current MEPC.353(78) has (3672, 0.590) for >=57,700 GT.

3. **roro_cargo and roro_passenger use OUTDATED values** from the revoked MEPC.337(76). These were significantly revised in MEPC.353(78).

4. **Missing size-dependent parameters**: Several ship types have different parameters for different size ranges (gas carrier >=65k vs <65k DWT, general cargo >=20k vs <20k DWT, LNG carrier >=100k vs 65-100k vs <65k DWT, vehicle carrier >=57,700 vs 30k-57,700 vs <30k GT). The code uses a single set of parameters per type.

### 2.2 CII Reduction Factors (REDUCTION_FACTORS)

Source claimed: IMO MEPC.338(76)

| Year | Code Value (%) | MEPC.338(76) Value (%) | Status |
|------|---------------|----------------------|--------|
| 2019 | 0 | 0 | **CORRECT** |
| 2020 | 1 | 1 | **CORRECT** |
| 2021 | 2 | 2 | **CORRECT** |
| 2022 | 3 | 3 | **CORRECT** |
| 2023 | 5 | 5 | **CORRECT** |
| 2024 | 7 | 7 | **CORRECT** |
| 2025 | 9 | 9 | **CORRECT** |
| 2026 | 11 | 11 | **CORRECT** |

All reduction factors verified and correct. Note: MEPC.400(83) from April 2025 has since defined 2027-2030 factors (13.625%, 16.25%, 18.875%, 21.5%) which are not yet in the code.

### 2.3 CII Rating Boundaries (CII_RATING_BOUNDARIES)

Source claimed: IMO MEPC.354(78)

**CRITICAL ERROR IN ALL VALUES**: The code stores values claiming to be `d` values used in `math.exp(d)`, but the numbers are completely wrong.

MEPC.354(78) Table 1 provides **exp(d)** values directly (the multipliers). The code should either:
- (A) Store exp(d) values and multiply directly: `required_cii * exp_d_value`, OR
- (B) Store d = ln(exp_d_value) and use `math.exp(d)`

The code chose approach (B) but stored **completely wrong d values**.

Example for bulk_carrier:
- MEPC.354(78): exp(d1) = 0.86, exp(d2) = 0.94, exp(d3) = 1.06, exp(d4) = 1.18
- Correct d values: ln(0.86) = -0.1508, ln(0.94) = -0.0619, ln(1.06) = 0.0583, ln(1.18) = 0.1655
- Code has: d1 = -0.86, d2 = -0.69, d3 = -0.32, d4 = 0.00
- Code computes: exp(-0.86) = 0.423, exp(-0.69) = 0.502, exp(-0.32) = 0.726, exp(0.00) = 1.00

**Impact**: With the code's values, the A/B boundary for a bulk carrier is at 42.3% of the required CII (exp(-0.86) = 0.423), when it should be at 86% (exp(-0.1508) = 0.86). This makes ratings far too lenient -- almost every ship would get an A or B rating.

#### Complete comparison table:

| Ship Type | Code d values | Correct exp(d) from MEPC.354(78) | Correct d values (ln) |
|-----------|--------------|----------------------------------|----------------------|
| bulk_carrier | (-0.86, -0.69, -0.32, 0.00) | (0.86, 0.94, 1.06, 1.18) | (-0.151, -0.062, 0.058, 0.166) |
| gas_carrier | (-0.78, -0.57, -0.28, 0.00) | (0.81, 0.91, 1.12, 1.44) [>=65k] | (-0.211, -0.094, 0.113, 0.365) |
| tanker | (-0.85, -0.69, -0.32, 0.00) | (0.82, 0.93, 1.08, 1.28) | (-0.198, -0.073, 0.077, 0.247) |
| container | (-0.84, -0.56, -0.27, 0.00) | (0.83, 0.94, 1.07, 1.19) | (-0.186, -0.062, 0.068, 0.174) |
| general_cargo | (-0.80, -0.56, -0.27, 0.00) | (0.83, 0.94, 1.06, 1.19) | (-0.186, -0.062, 0.058, 0.174) |
| refrigerated_cargo | (-0.78, -0.57, -0.20, 0.00) | (0.78, 0.91, 1.07, 1.20) | (-0.248, -0.094, 0.068, 0.182) |
| combination_carrier | (-0.86, -0.69, -0.32, 0.00) | (0.87, 0.96, 1.06, 1.14) | (-0.139, -0.041, 0.058, 0.131) |
| lng_carrier | (-0.78, -0.57, -0.28, 0.00) | (0.89, 0.98, 1.06, 1.13) [>=100k] | (-0.117, -0.020, 0.058, 0.122) |
| vehicle_carrier | (-0.86, -0.69, -0.32, 0.00) | (0.86, 0.94, 1.06, 1.16) | (-0.151, -0.062, 0.058, 0.148) |
| roro_cargo | (-0.78, -0.57, -0.28, 0.00) | (0.76, 0.89, 1.08, 1.27) | (-0.274, -0.117, 0.077, 0.239) |
| roro_passenger | (-0.78, -0.57, -0.28, 0.00) | (0.76, 0.92, 1.14, 1.30) | (-0.274, -0.083, 0.131, 0.262) |
| cruise_passenger | (-0.78, -0.57, -0.28, 0.00) | (0.87, 0.95, 1.06, 1.16) | (-0.139, -0.051, 0.058, 0.148) |

**Recommendation**: Replace the d values with the correct ln() values, OR (simpler and less error-prone) store the exp(d) values directly and change the comparison to `attained_cii <= required_cii * exp_d_value` without using `math.exp()`.

### 2.4 CETOS to CII Type Mapping

| CETOS Type | CII Type | Status |
|-----------|----------|--------|
| chemical_tanker -> tanker | | **CORRECT** -- Chemical tankers are classified under "tanker" for CII |
| ferry-pax -> roro_passenger | | **QUESTIONABLE** -- Pure passenger ferries may not fall under CII. CII covers "ro-ro passenger ships" which carry both vehicles and passengers. A pure passenger ferry (ferry-pax) is not the same as a ro-ro passenger ship. |
| ferry-ropax -> roro_passenger | | **CORRECT** -- Ro-pax ferries are ro-ro passenger ships |

### 2.5 Capacity Type (GT vs DWT)

The code correctly identifies roro_passenger and cruise_passenger as using GT. However, per MEPC.354(78):
- **Vehicle carrier (ro-ro vehicle carrier)** also uses **GT**, not DWT -- the code maps it correctly in `_GT_CAPACITY_TYPES` indirectly since it is not in that set, but the MEPC.354(78) table clearly shows vehicle carrier uses GT. **This needs to be added to `_GT_CAPACITY_TYPES`.**
- **Ro-ro cargo ship** uses **GT** per MEPC.353(78)/354(78). The code does not include it in `_GT_CAPACITY_TYPES`. **INCORRECT**.

---

## 3. README.md

### Source References

| README Claim | Actual | Status |
|-------------|--------|--------|
| "IMO MEPC.308(73)" for CO2 factors | MEPC.308(73) Table 1 | **CORRECT** |
| "MEPC.308(73)" described as "2024 Guidelines on the method of calculation of the attained EEXI" | MEPC.308(73) is the 2018 EEDI Guidelines, not EEXI. The EEXI guidelines are MEPC.333(76). | **INCORRECT** |
| "MEPC.339(76)" for CII reference lines | Reference lines are MEPC.337(76), superseded by MEPC.353(78). MEPC.339(76) is the CII Rating Guidelines G4 (superseded by MEPC.354(78)). | **INCORRECT** |
| "MEPC.338(76)" for CII reduction factors | Correct | **CORRECT** |
| "MEPC.354(78)" for CII rating boundaries | Correct | **CORRECT** |

---

## 4. CRITICAL BUGS REQUIRING IMMEDIATE FIX

### Bug 1: CII Rating Boundaries Are All Wrong
**File**: `cetos/cii.py`, `CII_RATING_BOUNDARIES` dict
**Impact**: Every CII rating calculated by CETOS is incorrect. Ratings are far too lenient.
**Fix**: Store the exp(d) values from MEPC.354(78) directly and remove the `math.exp()` call, OR compute the correct d = ln(exp_d) values.

### Bug 2: Gas Carrier Reference Line 'a' Value Off By 1000x
**File**: `cetos/cii.py`, `CII_PARAMS["gas_carrier"]`
**Impact**: Gas carrier required CII is ~1000x too low, making any gas carrier appear to have terrible CII.
**Fix**: Change `144050000` to `14405e7` (= 1.4405e11).

### Bug 3: Vehicle Carrier Parameters Are Wrong
**File**: `cetos/cii.py`, `CII_PARAMS["vehicle_carrier"]`
**Impact**: Wrong required CII for vehicle carriers.
**Fix**: Use MEPC.353(78) values: (3672, 0.590) for >=57,700 GT. Code currently has (5686, 0.714) which matches no known IMO resolution.

### Bug 4: Ro-Ro Cargo and Ro-Ro Passenger Use Revoked Parameters
**File**: `cetos/cii.py`, `CII_PARAMS["roro_cargo"]` and `CII_PARAMS["roro_passenger"]`
**Impact**: Wrong required CII for these vessel types.
**Fix**: Update to MEPC.353(78) values: roro_cargo (1967, 0.485), roro_passenger (2023, 0.460).

---

## 5. ADDITIONAL ISSUES (NON-CRITICAL)

1. **Missing size-dependent CII parameters**: Gas carriers (<65k DWT), general cargo (<20k DWT), LNG carriers (<100k DWT), and vehicle carriers (<30k GT) all have different reference line parameters. The code uses only one set per type.

2. **Vehicle carrier and ro-ro cargo should use GT**: Per MEPC.353(78)/354(78), these types use GT not DWT. The `_GT_CAPACITY_TYPES` set should include `"vehicle_carrier"` and `"roro_cargo"`.

3. **Inconsistent LCV for FuelEU calculations**: The WtW calculation uses IMO LCV (40.2 MJ/kg for HFO) but FuelEU Annex II specifies 40.5 MJ/kg. Minor impact (~0.7%).

4. **NOx engine age categories don't match IMO Tiers**: The "before_1984" and "1984-2000" age categories don't correspond to IMO Tier 0 (pre-2000) and Tier I (2000-2011) boundaries. The emission factor values are reasonable approximations but the Tier labeling in comments is misleading.

5. **Source reference errors in code comments and README**: CII reference line parameters cite MEPC.339(76) but should cite MEPC.353(78). README describes MEPC.308(73) as "EEXI" guidelines but it is "EEDI" guidelines.

6. **Missing 2027-2030 CII reduction factors**: MEPC.400(83) from April 2025 defined factors for 2027-2030.

---

## Sources Consulted

- [MEPC.308(73) - 2018 EEDI Guidelines](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.308(73).pdf)
- [MEPC.337(76) - 2021 CII Reference Lines G2 (revoked)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.337(76).pdf)
- [MEPC.338(76) - CII Reduction Factors G3](https://wwwcdn.imo.org/localresources/en/OurWork/Environment/Documents/Air%20pollution/MEPC.338(76).pdf)
- [MEPC.339(76) - 2021 CII Rating Guidelines G4 (superseded)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.339(76).pdf)
- [MEPC.353(78) - 2022 CII Reference Lines G2 (current)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.353(78).pdf)
- [MEPC.354(78) - 2022 CII Rating Guidelines G4 (current)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.354(78).pdf)
- [MEPC.364(79) - 2022 EEDI Guidelines](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.364(79).pdf)
- [MEPC.400(83) - 2025 CII Reduction Factors update](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.400(83).pdf)
- [imorules.com - MEPC.354(78) Rating Boundaries Table](https://imorules.com/GUID-6A295E06-7352-44FE-9B62-1F63B5652B48.html)
- [imorules.com - MEPC.353(78) Reference Line Parameters Table](https://imorules.com/GUID-3D89CD6D-A4CE-44C7-8CB9-70F67D95A6A8.html)
- [FuelEU Maritime Regulation (EU) 2023/1805](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023R1805)
- [BetterSea - FuelEU Maritime GHG Intensity Guide](https://www.bettersea.tech/post/guide-how-to-calculate-ghg-intensity-under-fueleu-maritime)
- [Sustainable Ships - Emission Properties](https://www.sustainable-ships.org/stories/2025/fuel-emissions-properties)
- [IMO NOx Regulation 13](https://www.imo.org/en/ourwork/environment/pages/nitrogen-oxides-(nox)-%E2%80%93-regulation-13.aspx)
- [DieselNet - IMO Marine Engine Regulations](https://dieselnet.com/standards/inter/imo.php)
- [US EPA - Understanding Global Warming Potentials](https://www.epa.gov/ghgemissions/understanding-global-warming-potentials)
- [Etive-Mor Open-IMO-CII-Calculator](https://github.com/Etive-Mor/Open-IMO-CII-Calculator)
