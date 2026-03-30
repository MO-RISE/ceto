# CETOS Emissions & CII Module -- Second Verification Report

**Date**: 2026-03-27
**Scope**: Verify fixes from the first verification round, cross-check calculations numerically, and identify any remaining issues
**Method**: Every value cross-referenced against primary source documents via web search; numerical calculations verified independently

---

## SUMMARY

The first verification round identified 4 critical bugs. All 4 have been fixed correctly. The code now produces correct results for the vessel types and size ranges it covers. Several non-critical issues remain from the first round (README source reference, missing size-dependent parameters). No new critical issues were found.

| Check | Result |
|-------|--------|
| CII rating boundaries fix | VERIFIED CORRECT |
| Gas carrier a=14405e7 fix | VERIFIED CORRECT |
| Vehicle carrier (3672, 0.590) fix | VERIFIED CORRECT |
| Ro-ro cargo/passenger params fix | VERIFIED CORRECT |
| GT capacity types fix | VERIFIED CORRECT |
| Emissions calculation (HFO 1000 kg) | VERIFIED CORRECT |
| CII numerical cross-check | VERIFIED CORRECT |
| WtW GHG intensity logic | VERIFIED CORRECT |
| Remaining UNCERTAIN values | See Section 4 |
| README source table | One error remains (Section 5) |

---

## 1. Verification of First-Round Fixes

### 1a. CII Rating Boundaries -- VERIFIED CORRECT

The code now stores exp(d) multiplier values directly in `CII_RATING_BOUNDARIES` and applies them as `required_cii * exp_d_value` without `math.exp()`. Every value was checked against MEPC.354(78) Table 1 as extracted from [imorules.com](https://imorules.com/GUID-6A295E06-7352-44FE-9B62-1F63B5652B48.html):

| Ship Type | Code Values | MEPC.354(78) Values | Status |
|-----------|-------------|---------------------|--------|
| bulk_carrier | (0.86, 0.94, 1.06, 1.18) | (0.86, 0.94, 1.06, 1.18) | CORRECT |
| gas_carrier | (0.81, 0.91, 1.12, 1.44) | (0.81, 0.91, 1.12, 1.44) [>=65k DWT] | CORRECT |
| tanker | (0.82, 0.93, 1.08, 1.28) | (0.82, 0.93, 1.08, 1.28) | CORRECT |
| container | (0.83, 0.94, 1.07, 1.19) | (0.83, 0.94, 1.07, 1.19) | CORRECT |
| general_cargo | (0.83, 0.94, 1.06, 1.19) | (0.83, 0.94, 1.06, 1.19) | CORRECT |
| refrigerated_cargo | (0.78, 0.91, 1.07, 1.20) | (0.78, 0.91, 1.07, 1.20) | CORRECT |
| combination_carrier | (0.87, 0.96, 1.06, 1.14) | (0.87, 0.96, 1.06, 1.14) | CORRECT |
| lng_carrier | (0.89, 0.98, 1.06, 1.13) | (0.89, 0.98, 1.06, 1.13) [>=100k DWT] | CORRECT |
| vehicle_carrier | (0.86, 0.94, 1.06, 1.16) | (0.86, 0.94, 1.06, 1.16) | CORRECT |
| roro_cargo | (0.76, 0.89, 1.08, 1.27) | (0.76, 0.89, 1.08, 1.27) | CORRECT |
| roro_passenger | (0.76, 0.92, 1.14, 1.30) | (0.76, 0.92, 1.14, 1.30) | CORRECT |
| cruise_passenger | (0.87, 0.95, 1.06, 1.16) | (0.87, 0.95, 1.06, 1.16) | CORRECT |

The `calculate_cii_rating` function at line 182 correctly uses direct multiplication (`required_cii * exp_d1`) without `math.exp()`. This is correct.

**Note**: The code uses the >=65k DWT boundaries for gas_carrier and >=100k DWT boundaries for lng_carrier. Ships below these thresholds have different boundary vectors per MEPC.354(78) (e.g., gas carrier <65k: 0.85, 0.95, 1.06, 1.25; LNG carrier <100k: 0.78, 0.92, 1.10, 1.37). This is a known limitation documented in the code comments, not a bug.

### 1b. Gas Carrier a=14405e7 -- VERIFIED CORRECT

The code has:
```python
"gas_carrier": (14405e7, 2.071),  # 1.4405 x 10^11
```

In Python, `14405e7` evaluates to `14405 * 10^7 = 1.4405 * 10^11 = 144,050,000,000`. This matches the MEPC.353(78) notation "14405E7" exactly.

Verification that it produces reasonable CII values:
- Gas carrier, 65,000 DWT: CII_ref = 14405e7 * 65000^(-2.071) = **15.52 gCO2/(DWT*nm)** -- reasonable for a gas carrier
- Gas carrier, 80,000 DWT: CII_ref = **10.10** -- reasonable (decreasing with size as expected)

The [Open-IMO-CII-Calculator on GitHub](https://github.com/Etive-Mor/Open-IMO-CII-Calculator) confirms this same value: a = 14405E7 for gas carriers >= 65,000 DWT.

### 1c. Vehicle Carrier (3672, 0.590) -- VERIFIED CORRECT

The code has:
```python
"vehicle_carrier": (3672, 0.590),  # MEPC.353(78), for >=57,700 GT
```

This matches MEPC.353(78) Table 1 exactly as confirmed from [imorules.com](https://imorules.com/GUID-3D89CD6D-A4CE-44C7-8CB9-70F67D95A6A8.html):
- Ro-ro cargo ship (vehicle carrier), 57,700 GT and above: a=3672, c=0.590
- Ro-ro cargo ship (vehicle carrier), 30,000-57,699 GT: a=3672, c=0.590 (same values)
- Ro-ro cargo ship (vehicle carrier), less than 30,000 GT: a=330, c=0.329 (different -- not in code)

### 1d. Ro-ro Cargo and Ro-ro Passenger -- VERIFIED CORRECT

The code has:
```python
"roro_cargo": (1967, 0.485),      # MEPC.353(78)
"roro_passenger": (2023, 0.460),  # MEPC.353(78)
```

Both match MEPC.353(78) Table 1 exactly:
- Ro-ro cargo ship: a=1967, c=0.485 (GT-based)
- Ro-ro passenger ship: a=2023, c=0.460 (GT-based)

### 1e. GT Capacity Types -- VERIFIED CORRECT

The code has:
```python
_GT_CAPACITY_TYPES = {"roro_passenger", "cruise_passenger", "vehicle_carrier", "roro_cargo"}
```

Per MEPC.353(78) and MEPC.354(78), the following types use GT:
- Ro-ro passenger ship: GT -- IN SET
- Cruise passenger ship: GT -- IN SET
- Ro-ro cargo ship (vehicle carrier): GT -- IN SET
- Ro-ro cargo ship: GT -- IN SET

All four GT-based types are included. This was fixed from the first verification where vehicle_carrier and roro_cargo were missing.

---

## 2. CII Numerical Cross-Check

### Test Case: Bulk Carrier, 50,000 DWT, HFO, 10,000 tonnes fuel, 50,000 nm, Year 2024

**Attained CII:**
- CO2 = 10,000,000 kg fuel * 3.114 kg CO2/kg fuel = 31,140,000 kg CO2
- CO2 in grams = 31,140,000,000 g
- Attained CII = 31,140,000,000 / (50,000 * 50,000) = **12.456 gCO2/(DWT*nm)**

**Required CII for 2024:**
- CII_ref = 4745 * 50000^(-0.622) = 5.6686
- Z = 7% for 2024
- Required CII = 5.6686 * (1 - 7/100) = **5.2718 gCO2/(DWT*nm)**

**Rating:**
- Attained/Required ratio = 12.456 / 5.2718 = 2.36
- Rating boundaries: A <= 4.53, B <= 4.96, C <= 5.59, D <= 6.22
- 12.456 > 6.22, so rating = **E**

This makes physical sense: a vessel consuming 10,000 tonnes of HFO over 50,000 nm with only 50,000 DWT is extremely carbon-intensive. The E rating is expected.

The code's `calculate_attained_cii`, `calculate_required_cii`, and `calculate_cii_rating` functions all implement these formulas correctly.

---

## 3. Emissions Cross-Check

### 3a. GHG Emissions for 1000 kg HFO (SSD oil engine)

| Pollutant | Code Factor | Calculation | Result | Expected | Status |
|-----------|-------------|-------------|--------|----------|--------|
| CO2 | 3.114 kg/kg | 1000 * 3.114 | 3114.0 kg | 3114 kg | CORRECT |
| CH4 | 0.00005 kg/kg | 1000 * 0.00005 | 0.05 kg | ~0.05 kg | CORRECT |
| N2O | 0.00018 kg/kg | 1000 * 0.00018 | 0.18 kg | ~0.18 kg | CORRECT |
| CO2eq | -- | 3114 + 0.05*28 + 0.18*265 | **3163.1 kg** | 3163.1 kg | CORRECT |

The `estimate_ghg_emissions` function correctly applies: `co2eq = co2 + ch4 * GWP_CH4 + n2o * GWP_N2O`

### 3b. Well-to-Wake GHG Intensity

**MDO with SSD oil engine:**
- TtW CO2eq per kg fuel = 3.206 + 0.00005*28 + 0.00018*265 = 3.2551 kg CO2eq/kg fuel
- TtW GHG intensity = (3.2551 * 1000) / 42.7 = **76.23 gCO2eq/MJ**
- WtT = 14.4 gCO2eq/MJ
- WtW = 76.23 + 14.4 = **90.63 gCO2eq/MJ**

**HFO with SSD oil engine:**
- TtW CO2eq per kg fuel = 3.114 + 0.00005*28 + 0.00018*265 = 3.1631 kg CO2eq/kg fuel
- TtW GHG intensity = (3.1631 * 1000) / 40.2 = **78.68 gCO2eq/MJ**
- WtT = 13.5 gCO2eq/MJ
- WtW = 78.68 + 13.5 = **92.18 gCO2eq/MJ**

**Reasonableness check:**
- FuelEU Maritime 2025 limit: 89.34 gCO2eq/MJ (2% reduction from 2020 baseline of 91.16)
- HFO WtW = 92.18 -- exceeds the 2025 limit, which is expected (fossil HFO cannot meet FuelEU)
- MDO WtW = 90.63 -- also exceeds the 2025 limit, which is expected
- These values are in the expected range of ~90-93 gCO2eq/MJ for fossil marine fuels

The code's `estimate_well_to_wake_emissions` function implements this correctly. The formula `ghg_intensity = (wtw_total * 1000.0) / total_energy_mj` correctly converts from kg to grams and divides by energy in MJ.

**Minor note**: As identified in the first report, using IMO LCV (40.2 MJ/kg for HFO) rather than FuelEU LCV (40.5 MJ/kg) introduces a ~0.7% difference for HFO. With FuelEU's 40.5, the HFO TtW would be 78.10 instead of 78.68. This is a design choice, not a bug, but should be documented.

---

## 4. Values Flagged as UNCERTAIN in First Report

### 4a. CH4 LBSI Factor 0.026

**Status: VERIFIED as reasonable.**

The [Sustainable Ships emission properties page](https://www.sustainable-ships.org/stories/2025/fuel-emissions-properties) lists LBSI methane slip as **2.60%** for both IMO and EU frameworks. This converts to 0.026 kg CH4/kg fuel, matching the code exactly.

Note: FuelEU Annex II does not have a separate "LBSI" category -- it groups engines differently. The 2.6% value comes from the IMO Fourth GHG Study. The code's use of this value is appropriate for IMO-aligned calculations.

### 4b. N2O LNG Factor 0.00011

**Status: VERIFIED CORRECT.**

Web search confirmed the FuelEU Maritime Annex II TtW N2O emission factor for LNG dual-fuel engines (both Otto medium-speed and Otto slow-speed) is **0.00011 g N2O/g fuel**, equivalent to 0.00011 kg N2O/kg fuel. Multiple sources corroborate this, including the ESSF SAPS WS1 FuelEU calculation methodologies document.

### 4c. PM Factors

**Status: STILL UNCERTAIN but reasonable.**

The PM factors (HFO: 0.6, MDO: 0.3, LNG: 0.02, MeOH: 0.03 g/kg fuel) could not be traced to a single specific table in either the IMO Fourth GHG Study or the EMEP/EEA Guidebook via web search. The EMEP/EEA Guidebook 2023 chapter on maritime navigation contains PM emission factors, but they are expressed in g/kWh (energy-based) rather than g/kg fuel (mass-based), making direct comparison difficult without knowing the specific fuel consumption.

The values are within the range of published estimates:
- HFO 0.6 g/kg: Plausible for VLSFO (0.50% S). Pre-2020 HFO (3.5% S) would be much higher (~6-7 g/kg).
- MDO 0.3 g/kg: Plausible for low-sulfur distillate.
- LNG 0.02 and MeOH 0.03 g/kg: Plausible -- negligible PM from clean fuels.

**Recommendation**: Consider adding a comment noting these are engineering estimates suitable for screening-level assessments, not regulatory compliance values.

### 4d. NOx MSD/HSD Values

**Status: VERIFIED as consistent with IMO regulatory limits.**

The code's NOx factors were checked against the IMO Regulation 13 NOx limits:

**SSD (slow-speed diesel, n < 130 rpm):**
- Code: 18.1 (pre-Tier), 17.0 (Tier I), 14.4 (Tier II)
- IMO Reg 13: Tier I = 17.0 g/kWh, Tier II = 14.4 g/kWh for n < 130 rpm
- **SSD values match IMO limits exactly.** The pre-Tier value 18.1 is a reasonable baseline.

**MSD (medium-speed diesel, typically 300-900 rpm):**
- Code: 14.0 (pre-Tier), 12.0 (Tier I), 10.5 (Tier II)
- IMO Reg 13 at 500 rpm: Tier I = 45 * 500^(-0.20) = 13.0 g/kWh, Tier II = 44 * 500^(-0.23) = 10.5 g/kWh
- The Tier II value of 10.5 matches the IMO limit at ~500 rpm. The Tier I value of 12.0 is slightly below the limit at 500 rpm (13.0) but within the MSD speed range -- at ~720 rpm, the Tier I limit is 12.1 g/kWh.
- **MSD values are reasonable representative values for typical MSD engines.**

**HSD (high-speed diesel, typically > 1000 rpm):**
- Code: 12.0 (pre-Tier), 10.0 (Tier I), 8.0 (Tier II)
- IMO Reg 13 at 1500 rpm: Tier I = 10.4 g/kWh, Tier II = 8.2 g/kWh
- At n >= 2000 rpm: Tier I = 9.8 g/kWh, Tier II = 7.7 g/kWh
- **HSD values are reasonable representative values.** The Tier II value of 8.0 falls between the 1500 rpm limit (8.2) and the 2000 rpm limit (7.7).

---

## 5. README Emission Factor Source Table

| Row | README Source | Actual Source | Status |
|-----|-------------|---------------|--------|
| CO2 (Cf) | IMO MEPC.308(73) | MEPC.308(73) Table 1 | CORRECT |
| CH4 (methane slip) | FuelEU Maritime Annex II, IMO 4th GHG Study | FuelEU Annex II + IMO 4th GHG Study | CORRECT |
| N2O | FuelEU Maritime Annex II | FuelEU Annex II | CORRECT |
| WtT (upstream) | FuelEU Maritime Annex II | FuelEU Annex II | CORRECT |
| NOx | IMO NOx Technical Code | IMO NOx Technical Code / Reg 13 + 4th GHG Study | CORRECT |
| SOx | IMO MARPOL Annex VI | MARPOL Annex VI | CORRECT |
| PM | IMO 4th GHG Study, EMEP/EEA Guidebook | 4th GHG Study + EMEP/EEA | CORRECT |
| CII reference lines | **IMO MEPC.339(76)** | **MEPC.353(78)** | **WRONG** |
| CII reduction factors | IMO MEPC.338(76) | MEPC.338(76) | CORRECT |
| CII rating boundaries | IMO MEPC.354(78) | MEPC.354(78) | CORRECT |
| GWP (AR5) | IPCC AR5 | IPCC AR5 | CORRECT |

**One error remains**: The README claims CII reference lines come from "IMO MEPC.339(76)" but this is the CII Rating Guidelines (G4), not the reference lines. The correct source is **MEPC.353(78)** (which supersedes MEPC.337(76)). The code itself (`cii.py` line 8 and line 18) correctly references MEPC.353(78), but the README was not updated. This was flagged in the first report but not fixed.

---

## 6. Code Logic Review

### 6a. Well-to-Wake GHG Intensity Calculation

The `estimate_well_to_wake_emissions` function logic is correct:

1. WtT factor conversion: `wtt_kg_co2eq_per_kg_fuel = wtt_gco2eq_per_mj * lcv / 1000.0` -- CORRECT (converts gCO2eq/MJ to kgCO2eq/kg fuel)
2. WtT total: `total_fuel_kg * wtt_kg_co2eq_per_kg_fuel` -- CORRECT
3. TtW total: from `estimate_ghg_emissions` CO2eq (includes CO2 + CH4*28 + N2O*265) -- CORRECT
4. WtW total: `wtt_total + ttw_total` -- CORRECT
5. GHG intensity: `(wtw_total * 1000.0) / total_energy_mj` -- CORRECT (converts kg to g)

The algebra is self-consistent: for any fuel quantity, the function correctly produces `WtW = WtT + TtW` in gCO2eq/MJ, which is the FuelEU Maritime metric.

### 6b. CII Rating Logic

The `calculate_cii_rating` function (lines 182-193) correctly implements the MEPC.354(78) rating scheme:
- A: attained <= required * exp(d1)
- B: attained <= required * exp(d2)
- C: attained <= required * exp(d3)
- D: attained <= required * exp(d4)
- E: attained > required * exp(d4)

The boundary comparisons use `<=` which is correct per the IMO guidelines.

---

## 7. Remaining Non-Critical Issues (Carried Forward from First Report)

1. **README CII reference line source**: Says MEPC.339(76), should say MEPC.353(78). This is the only remaining source reference error.

2. **Missing size-dependent CII parameters**: The code uses single parameter sets per vessel type. MEPC.353(78) specifies different parameters for:
   - Gas carrier: >=65k DWT vs <65k DWT
   - General cargo: >=20k DWT vs <20k DWT
   - LNG carrier: >=100k DWT vs 65k-100k DWT vs <65k DWT
   - Vehicle carrier: >=57,700 GT vs 30k-57,700 GT vs <30k GT

   Similarly, MEPC.354(78) has different rating boundaries for gas carrier (<65k), LNG carrier (<100k).

3. **Missing 2027-2030 CII reduction factors**: MEPC.400(83) from April 2025 defined factors for 2027 (13.625%), 2028 (16.25%), 2029 (18.875%), 2030 (21.5%).

4. **HFO LCV inconsistency for FuelEU**: IMO uses 40.2 MJ/kg, FuelEU uses 40.5 MJ/kg. The code uses 40.2 throughout. Impact is ~0.7% for HFO only.

5. **NOx engine age categories**: The code categories ("before_1984", "1984-2000", "after_2000") do not map exactly to IMO Tier boundaries (pre-2000, 2000-2011, 2011+). This is inherited from the vessel data model and is a simplification, not a bug in the emissions module per se.

---

## 8. Conclusion

All 4 critical bugs identified in the first verification round have been correctly fixed:

- CII rating boundaries now use exp(d) multipliers directly from MEPC.354(78)
- Gas carrier a=14405e7 correctly equals 1.4405 x 10^11
- Vehicle carrier parameters (3672, 0.590) match MEPC.353(78)
- Ro-ro cargo (1967, 0.485) and ro-ro passenger (2023, 0.460) match MEPC.353(78)
- GT capacity types now correctly include vehicle_carrier and roro_cargo

The emissions calculations produce correct results (verified numerically). The well-to-wake GHG intensity calculation is algebraically sound and produces realistic values (~90-92 gCO2eq/MJ for fossil fuels, correctly exceeding the FuelEU 2025 limit of 89.34).

The CH4 LBSI factor (0.026) and N2O LNG factor (0.00011) have been verified as correct. PM factors remain unverifiable from web sources but are reasonable engineering estimates.

**One README error remains**: CII reference lines cite MEPC.339(76) instead of MEPC.353(78).

---

## Sources Consulted

- [MEPC.353(78) -- CII Reference Lines G2 (imorules.com)](https://imorules.com/GUID-3D89CD6D-A4CE-44C7-8CB9-70F67D95A6A8.html)
- [MEPC.354(78) -- CII Rating Boundaries G4 (imorules.com)](https://imorules.com/GUID-6A295E06-7352-44FE-9B62-1F63B5652B48.html)
- [MEPC.353(78) PDF (IMO)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.353(78).pdf)
- [MEPC.354(78) PDF (IMO)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.354(78).pdf)
- [Open-IMO-CII-Calculator (GitHub)](https://github.com/Etive-Mor/Open-IMO-CII-Calculator)
- [Sustainable Ships -- Emission Properties](https://www.sustainable-ships.org/stories/2025/fuel-emissions-properties)
- [Sustainable Ships -- FuelEU Maritime](https://www.sustainable-ships.org/rules-regulations/fueleu)
- [DieselNet -- IMO Marine Engine Regulations](https://dieselnet.com/standards/inter/imo.php)
- [IMO -- NOx Regulation 13](https://www.imo.org/en/ourwork/environment/pages/nitrogen-oxides-(nox)-%E2%80%93-regulation-13.aspx)
- [ESSF SAPS WS1 -- FuelEU Calculation Methodologies](https://www.intercargo.org/wp-content/uploads/2025/05/2025-May-ESSF-SAPS-WS1-FuelEU-calculation-methodologies.pdf)
- [DNV CII FAQs 2024](https://www.dnv.com/maritime/insights/topics/CII-carbon-intensity-indicator/answers-to-frequent-questions/)
