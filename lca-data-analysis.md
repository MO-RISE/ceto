# Maritime Life Cycle Analysis (LCA): Data Requirements and Sources for CETOS

## Executive Summary

This document analyzes the data requirements for adding Life Cycle Analysis (LCA) functionality to CETOS, which currently calculates fuel consumption (kg) and energy demand (kWh) by fuel type (HFO, MDO, MeOH, LNG) and engine type (SSD, MSD, HSD, LNG-Otto-MS, LBSI, gas turbine, steam turbine). The analysis covers what additional data is needed, where to get it, and the recommended implementation path.

**Key finding:** CETOS already produces the hardest-to-calculate input -- fuel consumption in kg by fuel type. Adding basic well-to-wake LCA requires only a set of emission factors (constants) multiplied against that fuel consumption. A minimum viable implementation can be built using freely available, authoritative emission factors from IMO and FuelEU Maritime regulatory sources.

---

## 1. LCA Data Requirements by Phase

### 1A. Well-to-Tank (WtT) -- Fuel Production Upstream Emissions

WtT covers all emissions from extraction/cultivation of feedstock through refining, transport, and bunkering onto the ship.

#### Required emission factors (per fuel type, in gCO2eq/MJ):

| Fuel Type | WtT Default (gCO2eq/MJ) | Source |
|---|---|---|
| HFO (RME-RMK grades) | 13.5 | FuelEU Maritime Annex II |
| LFO | 13.2 | FuelEU Maritime Annex II |
| MDO/MGO (DMX-DMB grades) | 14.4 | FuelEU Maritime Annex II |
| LNG (all engine types) | 18.5 | FuelEU Maritime Annex II |
| LPG (Propane) | 7.8 | FuelEU Maritime Annex II |
| LPG (Butane) | 7.8 | FuelEU Maritime Annex II |
| Methanol (from natural gas) | 31.3 | FuelEU Maritime Annex II |
| Ammonia (from natural gas) | 121.0 | FuelEU Maritime / literature |
| Hydrogen grey (from SMR) | ~100-130 | Literature varies |
| Hydrogen blue (SMR + CCS) | ~30-50 | Literature varies |
| Hydrogen green (electrolysis, renewable) | ~0-10 | Literature varies |
| Bio-methanol (various feedstocks) | ~4.5-33.0 | Highly variable by pathway |
| Biodiesel (FAME) | ~18-30 | Depends on feedstock |

#### Key considerations:
- **Regional variation is significant.** A 2025 study found HSFO WtT carbon intensity ranges from 1.0 to 22.7 gCO2e/MJ depending on the producing country (e.g., Saudi Arabia at the low end, Russia/China higher). The global volume-weighted average is 12.4 gCO2e/MJ.
- **Upstream breakdown:** For HSFO, upstream extraction accounts for ~55% of WtT emissions, refining ~32%, transport ~6%, shipping ~4%, distribution ~2%.
- **For regulatory compliance (FuelEU Maritime), fossil fuel WtT values are fixed** -- companies cannot deviate from the Annex II defaults for fossil fuels. This simplifies implementation considerably.
- **For alternative/renewable fuels**, actual certified values may be used if they are better than defaults.

#### Gases included in WtT:
- CO2, CH4, N2O (converted to CO2eq using GWP values)
- GWP values (IPCC AR5): CO2 = 1, CH4 = 28, N2O = 265
- FuelEU currently uses RED II GWPs: CO2 = 1, CH4 = 25, N2O = 298 (transitioning to AR5)

### 1B. Tank-to-Wake (TtW) -- Combustion Emissions

TtW covers emissions during fuel combustion onboard the vessel.

#### CO2 Emission Factors (Cf) -- IMO MEPC.308(73) / MEPC.364(79):

These are the most stable and well-established factors:

| Fuel Type | Cf (t CO2 / t fuel) | LCV (MJ/kg) |
|---|---|---|
| Diesel/Gas Oil (MDO/MGO) | 3.206 | 42.7 |
| Light Fuel Oil (LFO) | 3.151 | 41.2 |
| Heavy Fuel Oil (HFO) | 3.114 | 40.2 |
| LPG Propane | 3.000 | 46.3 |
| LPG Butane | 3.030 | 45.7 |
| Ethane | 2.927 | 46.4 |
| LNG | 2.750 | 48.0 |
| Methanol | 1.375 | 19.9 |
| Ethanol | 1.913 | 26.8 |
| Ammonia | 0.000 | 18.6 |
| Hydrogen | 0.000 | 120.0 |

**These CO2 factors are stoichiometric** (based on carbon content of fuel) and do not change with engine type, load, or age. They are extremely stable over time.

#### CH4 Emission Factors (highly dependent on engine type):

CH4 emissions are dominated by "methane slip" in gas-fueled engines. This is one of the most variable and debated parameters in maritime LCA.

| Engine Type | CH4 Slip (% of fuel mass) | Source |
|---|---|---|
| SSD (oil fuels) | ~0.005% | Negligible |
| MSD (oil fuels) | ~0.005% | Negligible |
| HSD (oil fuels) | ~0.005% | Negligible |
| Dual-fuel medium-speed Otto (LNG) | 3.1-3.5% | FuelEU: 3.1%, IMO: 3.5% |
| Dual-fuel slow-speed Otto (LNG) | 1.7% | Both FuelEU and IMO |
| LNG diesel dual-fuel slow-speed (HPDF) | 0.15-0.2% | IMO: 0.15%, FuelEU: 0.2% |
| LBSI (lean-burn spark ignition, LNG) | 2.6% | IMO 4th GHG Study |
| Steam turbine/boiler (LNG) | ~0% | No methane slip |
| Gas turbine (LNG) | ~0.02% | Very low |

**CH4 matters enormously for LNG**: With a GWP of 28, even 3% methane slip can add 10+ gCO2eq/MJ to the lifecycle emissions, substantially eroding LNG's CO2 advantage over HFO.

#### N2O Emission Factors:

| Engine Type | N2O (g N2O / g fuel) | Notes |
|---|---|---|
| SSD/MSD/HSD (oil fuels) | 0.00018 | FuelEU default |
| LNG engines | 0.00011 | FuelEU default |
| Steam turbine | 0.00018 | Same as diesel |
| Gas turbine | 0.00018 | Same as diesel |

N2O has a GWP of 265, but mass emissions are very small. Contribution is typically 1-3 gCO2eq/MJ.

#### NOx Emission Factors (g/kWh, energy-based):

NOx depends on engine type, age (Tier 0/I/II/III), and load:

| Engine Type | Tier 0 (pre-2000) | Tier I (2000-2011) | Tier II (2011-2016) | Tier III (ECA, post-2016) |
|---|---|---|---|---|
| SSD (<130 rpm) | 18.1 | 17.0 | 14.4 | 3.4 |
| MSD (130-2000 rpm) | 14.0 | 12.0 | 10.5 | ~2.5 |
| HSD (>2000 rpm) | 12.0 | 10.0 | 8.0 | ~2.0 |

Source: IMO NOx Technical Code / 4th GHG Study

#### SOx Emission Factors:

SOx is directly proportional to fuel sulfur content:
- SOx (g/kWh) = 20 * S (where S is % sulfur by mass)
- Post-2020 global sulfur cap: 0.5% (VLSFO) or 0.1% in ECAs
- HFO + scrubber: effectively 3.5% S at combustion, treated in exhaust
- MDO/MGO: typically 0.1-0.5% S
- LNG/Methanol/Ammonia/Hydrogen: 0% S (zero SOx)

#### PM Emission Factors:

PM depends on fuel type, sulfur content, and engine load:
- After IMO 2020 (0.5% S fuel): PM reduced by ~80% vs pre-2020 HFO
- Typical values: 0.2-0.6 g/kWh for VLSFO, much lower for LNG/methanol

#### Black Carbon (BC):

- Included in IMO 4th GHG Study, increased ~12% from 2012-2018
- Ratio to CO2: ~0.0016 g BC / g CO2 (main engine)
- Climate forcing effects are complex and debated

#### Aggregate energy-based emission factors (g/kWh) -- simplified reference values:

From AIS-based emissions models (UCSB/emLab, averages across engine types):

| Pollutant | Main Engine | Auxiliary Engine | Boiler |
|---|---|---|---|
| CO2 | 629.8 | 699.7 | 958.0 |
| NOx | 13.0 | 12.1 | 2.0 |
| SOx | 3.9 (pre-2020) | 4.3 (pre-2020) | 5.8 (pre-2020) |
| PM | 0.6 | 0.6 | 0.4 |
| CH4 | 0.01 | 0.01 | 0.002 |
| N2O | 0.03 | 0.03 | 0.04 |
| CO | 0.54 | 0.54 | 0.20 |

Post-2020 corrections: SOx multiply by 0.2, PM multiply by 0.206

### 1C. Ship Construction / Manufacturing

Construction typically accounts for 3-6% of lifecycle energy and emissions, vs 72-75% for operations and 20-22% for fuel supply chain.

#### Required data:

| Input | Typical Value | Notes |
|---|---|---|
| Steel production (hot-rolled) | 1.8-2.2 t CO2 / t steel | Varies by production method (BF-BOF vs EAF) |
| Green steel | 0.4-0.8 t CO2 / t steel | Emerging; EAF with renewable energy |
| Steel per ship | 80-95% of ship lightweight | Structural steel dominates |
| Aluminum | 8-12 t CO2 / t aluminum | For superstructures on passenger/naval vessels |
| Main engine manufacturing | Included in steel + processing | Limited specific data available |
| Shipyard energy | 3-6% of lifecycle | Electricity, cutting, welding |
| Battery manufacturing | 39-196 kg CO2eq / kWh | Wide range by location and chemistry |
| Battery (NMC, China) | 114-137 kg CO2eq / kWh | Ternary lithium-ion |
| Battery (LFP, China) | 82.5 kg CO2eq / kWh | Lithium iron phosphate |
| Battery (NMC, USA) | 72.9 kg CO2eq / kWh | Lower grid carbon intensity |
| Battery (NMC, South Korea) | 141 kg CO2eq / kWh | Higher grid intensity |
| PEMFC manufacturing | ~20% of lifetime carbon footprint | Dominated by platinum use |
| SOFC manufacturing | Lower than PEMFC | Dominated by stainless steel |
| Fuel cell stack cost | >3,000 USD/kW | Relevant for cost-benefit analysis |

**Key finding for CETOS:** Construction-phase LCA is data-intensive and ship-specific. For a fuel consumption library, this is typically out of scope. However, CETOS already estimates battery and hydrogen system weights, which could serve as inputs to construction-phase calculations if desired.

### 1D. Ship Maintenance / Operation

#### Required data:

| Input | Typical Value | Notes |
|---|---|---|
| Drydocking interval | 5 years typical | Energy for hull cleaning, painting |
| Antifouling paint | Biocide release over time | Environmental impact, not GHG |
| Biofouling (without antifouling) | Up to 40% fuel increase | Operational impact on fuel consumption |
| Lubricant oil consumption | 0.3-1.2 g/kWh | Depends on engine type/age |
| Lubricant oil disposal | Waste oil processing emissions | Minor contribution to total |
| Shore power connections | Grid electricity emissions | Location-dependent |

**Key finding for CETOS:** Maintenance-phase LCA is typically excluded from regulatory frameworks (FuelEU, IMO LCA guidelines). It is a minor contributor to lifecycle emissions and requires highly ship-specific data.

### 1E. End of Life / Ship Recycling

#### Required data:

| Input | Typical Value | Notes |
|---|---|---|
| Steel recovery rate | 85-95% | From ship recycling |
| CO2 savings from recycled steel | 1.5 kg CO2eq per kg scrap | vs primary steel production |
| Energy savings from recycled steel | 13.4 MJ per kg scrap | Primary energy saved |
| Iron ore savings | 1.4 kg per kg scrap | Resource savings |
| Ship recycling industry output | ~4.5 million t steel/year | Global |
| Rerolling emissions (from ship scrap) | Significant | Cutting/rerolling consumes energy |
| Battery disposal/recycling | Emerging data | Li-ion recycling rates increasing |
| Hazardous materials | Asbestos, PCBs, heavy metals | Environmental impact, not GHG |

**Key finding for CETOS:** End-of-life LCA is out of scope for a fuel consumption library. It is excluded from all current maritime regulations (FuelEU, IMO, CII).

---

## 2. Databases and Data Sources

### 2.1 Free / Open Sources

#### IMO Fourth GHG Study (2020)
- **URL:** https://www.imo.org/en/ourwork/environment/pages/fourth-imo-greenhouse-gas-study-2020.aspx
- **Content:** Comprehensive emission factors for all major pollutants (CO2, CH4, N2O, NOx, SOx, PM, BC, CO, NMVOC) by engine type, fuel type, engine age, and load. Specific fuel consumption baselines. Fleet composition data.
- **Cost:** Free (PDF download)
- **Update frequency:** Every ~6 years (3rd study: 2014, 4th study: 2020, 5th study expected ~2026)
- **Authority:** THE authoritative source for maritime emission factors. Used by all regulatory frameworks.
- **Machine-readable:** PDF only. Tables must be manually extracted.
- **Python integration:** Manual transcription of tables into Python dicts/dataclasses. This is exactly what CETOS already does for SFC baselines in `imo.py`.

#### IMO MEPC Resolutions (Emission Factors)
- **MEPC.308(73):** CO2 conversion factors (Cf) for EEDI -- the definitive CO2 per tonne fuel values
- **MEPC.364(79):** Updated EEDI guidelines with additional fuel types
- **MEPC.391(81):** 2024 LCA Guidelines on Life Cycle GHG Intensity of Marine Fuels (defines 128 fuel/energy pathways across 14 fuel groups)
- **MEPC.376(80):** 2023 LCA Guidelines (predecessor)
- **URL:** https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/
- **Cost:** Free (PDF)
- **Authority:** Regulatory standard. Mandatory for compliance.
- **Machine-readable:** PDF only.

#### FuelEU Maritime Regulation (EU) 2023/1805 -- Annex II
- **URL:** https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023R1805
- **Content:** Complete default WtT and TtW emission factors for all fossil fuels, biofuels, and RFNBOs. Includes Cf, Cslip, LCV, CH4, N2O factors. Mandatory for EU compliance.
- **Cost:** Free
- **Update frequency:** Regulatory amendments as needed. Initial version 2023, with delegated acts ongoing.
- **Authority:** EU law. Mandatory for ships calling at EU ports.
- **Machine-readable:** PDF. Tables can be extracted.
- **Python integration:** Ideal for hardcoding as these are legally fixed values for fossil fuels.
- **Key value:** GHG intensity reference baseline = 91.16 gCO2eq/MJ (the benchmark for reduction targets).

#### GREET Model (Argonne National Lab)
- **URL:** https://www.energy.gov/eere/bioenergy/articles/greet-greenhouse-gases-regulated-emissions-and-energy-use-transportation
- **Content:** Complete well-to-wake lifecycle analysis for transportation fuels. Includes a dedicated Marine Module with fuel pathways for conventional and alternative marine fuels.
- **Cost:** Free (publicly funded by US DOE)
- **Update frequency:** Annual updates
- **Authority:** US government reference model, widely cited in academic literature
- **Machine-readable:** Excel-based model. Python wrappers exist in the community.
- **Python integration:** Possible via Excel parsing or manual extraction of factors. Not natively a Python library.

#### ICCT (International Council on Clean Transportation)
- **URL:** https://theicct.org/
- **Content:** Well-to-wake emission factor briefings, methane slip studies (FUMES project), comparative fuel analyses. Key publications:
  - "Accounting for well-to-wake CO2 equivalent emissions" (March 2021, updated August 2021)
  - "Key issues in LCA methodology for marine fuels" (April 2023)
  - Real-world NOx emissions data (October 2023)
- **Cost:** Free (research publications)
- **Update frequency:** Ongoing research publications
- **Authority:** Highly respected independent research organization. Influences IMO policy.
- **Machine-readable:** PDF reports with tables.

#### IPCC Emission Factors (2006 Guidelines, 2019 Refinement)
- **URL:** https://www.ipcc-nggip.iges.or.jp/public/2006gl/
- **Content:** Default Tier 1 emission factors for all fuels by sector. Stationary combustion chapter covers marine fuels. CO2 factors (kg/TJ), CH4, N2O.
- **Cost:** Free
- **Update frequency:** Major updates every ~10 years. 2019 refinement is current.
- **Authority:** THE global standard for national GHG inventories.
- **Machine-readable:** PDF with tables. IPCC Emission Factor Database (EFDB) has online search.

#### EMEP/EEA Air Pollutant Emission Inventory Guidebook (2023)
- **URL:** https://www.eea.europa.eu/en/analysis/publications/emep-eea-guidebook-2023
- **Content:** Chapter 1.A.3.d Navigation provides Tier 1, 2, and 3 emission factors for maritime shipping. Covers NOx, SOx, PM, CO, NMVOC, and GHGs by engine type and fuel type. Very detailed methodology with load-dependent factors.
- **Cost:** Free
- **Update frequency:** ~Every 4 years (2016, 2019, 2023)
- **Authority:** Official EU methodology for emission inventories
- **Machine-readable:** PDF. Downloadable emission factor viewer available.

#### OpenLCA / Nexus
- **URL:** https://www.openlca.org/ / https://nexus.openlca.org/
- **Content:** Open-source LCA software with ~300,000 datasets across multiple databases. Includes free datasets (ELCD) and paid ones (ecoinvent). Transportation datasets available but not maritime-specific.
- **Cost:** Software is free. Some databases are free, others paid (ecoinvent license needed separately).
- **Machine-readable:** Native LCA data format, importable into OpenLCA software. Python integration possible via Brightway.

#### EXIOBASE
- **URL:** https://www.exiobase.eu/
- **Content:** Multi-regional environmentally extended input-output database. 44 countries, 160 industry sectors, 200 product categories. Includes "Sea and coastal water transport" sector. Time series from 1995 onward.
- **Cost:** Free for academic use
- **Update frequency:** Periodic (latest v3.9.4, year 2022)
- **Machine-readable:** Available in OpenLCA format, also via Climatiq API
- **Python integration:** Can be imported into Python via pandas or Brightway

#### Brightway (Python LCA Framework)
- **URL:** https://brightway.dev/ / https://pypi.org/project/brightway2/
- **Content:** Open-source Python framework for LCA calculations. Can import ecoinvent and other databases. Performs static and Monte Carlo LCA calculations.
- **Cost:** Free (software). Database licenses separate.
- **Authority:** Standard academic tool for computational LCA
- **Machine-readable:** Native Python
- **Python integration:** Direct -- this IS a Python library on PyPI

### 2.2 Commercial / Paid Sources

#### ecoinvent
- **URL:** https://ecoinvent.org/
- **Content:** ~20,000 datasets covering all industries. Maritime transport datasets based on tonne-kilometre functional unit. Includes upstream supply chain emissions.
- **Cost:** Commercial license (pricing via calculator, estimated EUR 3,000-10,000+/year for commercial; educational discounts available; free for universities in low-income countries)
- **Update frequency:** Annual versions (current: v3.12)
- **Authority:** THE standard commercial LCA database. Gold standard in the field.
- **Machine-readable:** Via ecoQuery portal, or integration through LCA software (SimaPro, OpenLCA, Brightway)
- **API access:** Via third-party APIs (Climatiq, Emitly). No official direct API.
- **Python integration:** Via Brightway2 (import ecoinvent into Python)
- **Limitation for CETOS:** License prohibits redistribution of raw data. Cannot hardcode ecoinvent values into an open-source library without violating license terms.

#### GaBi / Sphera
- **URL:** https://sphera.com/ / https://lcadatabase.sphera.com/
- **Content:** ~20,000 DEKRA-verified datasets across 60+ industries including transportation. Proprietary LCA software + database.
- **Cost:** Commercial license (pricing not public, estimated comparable to ecoinvent)
- **Update frequency:** Regular updates
- **Authority:** Major commercial LCA database, widely used in industry
- **Machine-readable:** Via Sphera software only
- **Python integration:** Not directly. Would need manual extraction.
- **Limitation for CETOS:** Same redistribution issues as ecoinvent.

#### DNV Maritime Reports
- **URL:** https://www.dnv.com/maritime/
- **Content:** Alternative fuel assessment reports with well-to-wake emission data. Comparative analyses of fuel pathways including LNG, hydrogen, ammonia, methanol. Emission values in g CO2e/kWh shaft output.
- **Cost:** Reports typically free to download. Advisory services paid.
- **Authority:** Major maritime classification society. Highly authoritative.
- **Machine-readable:** PDF reports.

#### Lloyd's Register (LR)
- **URL:** https://www.lr.org/
- **Content:** Published the first cradle-to-grave LCA of an LNG carrier (2024). Lifecycle analysis including construction, operation, and end-of-life.
- **Cost:** Reports free to download.
- **Authority:** Major classification society.

#### Climatiq API
- **URL:** https://www.climatiq.io/
- **Content:** API providing emission factors from ecoinvent, EXIOBASE, EPA, and other sources. Includes maritime shipping factors.
- **Cost:** Free tier available (limited). Paid tiers for commercial use.
- **Machine-readable:** REST API (JSON responses)
- **Python integration:** Direct via HTTP requests

### 2.3 Regulatory / Institutional Sources

#### EU JRC / ELCD (European Reference Life Cycle Database)
- **URL:** https://nexus.openlca.org/ (ELCD available through Nexus)
- **Content:** EU reference lifecycle data including energy and transport
- **Cost:** Free
- **Note:** Being superseded by newer EU databases

#### IEA (International Energy Agency)
- **URL:** https://www.iea.org/
- **Content:** Energy statistics, fuel production data, emissions from energy sector
- **Cost:** Some data free, detailed datasets paid
- **Relevance:** Background data for WtT calculations (refinery emissions, energy mix)

#### GESAMP Working Group 46 (LCA of Marine Fuels)
- **URL:** http://www.gesamp.org/work/groups/gesamp-working-groupo-n-life-cycle-ghg-intensity-of-marine-fuels
- **Content:** Developing default WtT and TtW emission factors for the IMO LCA framework. First meeting September 2024. Member states can propose default factors until August 2025.
- **Authority:** Advisory body to IMO. Will define the official IMO default emission factors.
- **Status:** Work in progress. Final factors expected 2025-2026.

---

## 3. Free vs. Paid Data Availability

| Data Needed | Free Source | Paid Source | Recommended for CETOS |
|---|---|---|---|
| CO2 per tonne fuel (Cf) | IMO MEPC.308(73) | -- | IMO (definitive, stable) |
| LCV per fuel type | IMO MEPC / FuelEU Annex II | -- | FuelEU (regulatory standard) |
| WtT emission factors (gCO2eq/MJ) | FuelEU Annex II, IMO LCA Guidelines | ecoinvent, GaBi | FuelEU Annex II (legally binding) |
| TtW CH4 slip by engine type | FuelEU Annex II, IMO 4th GHG Study | -- | FuelEU Annex II (default) |
| TtW N2O factors | FuelEU Annex II, IMO 4th GHG Study | -- | FuelEU Annex II (default) |
| NOx by engine type/tier | EMEP/EEA Guidebook, IMO 4th GHG Study | -- | EMEP/EEA Guidebook |
| SOx (from sulfur content) | Formula: 20*S | -- | Calculate from fuel S% |
| PM by engine/fuel type | EMEP/EEA Guidebook, IMO 4th GHG Study | -- | EMEP/EEA Guidebook |
| Black carbon | IMO 4th GHG Study | -- | IMO 4th GHG Study |
| SFC baselines by engine type/age | IMO 4th GHG Study | -- | Already in CETOS (`imo.py`) |
| Steel production emissions | IPCC, worldsteel data | ecoinvent, GaBi | IPCC (for rough estimates) |
| Battery manufacturing emissions | Academic literature (open access) | ecoinvent | Literature values |
| Fuel cell manufacturing emissions | Academic literature | ecoinvent | Literature values |
| Complete lifecycle (cradle-to-gate) | GREET Model (free) | ecoinvent, GaBi | GREET for completeness |
| Regional WtT variation | arXiv paper (2502.07201) | ecoinvent | Literature values |

---

## 4. Data Reliability and Update Frequency

### Stable Factors (change very rarely):

| Factor | Stability | Why |
|---|---|---|
| CO2 per tonne fuel (Cf) | Very stable | Based on stoichiometry / carbon content |
| LCV per fuel type | Very stable | Physical property of fuel |
| N2O per gram fuel | Relatively stable | Well-characterized combustion chemistry |
| SOx calculation (20*S) | Very stable | Direct chemical relationship |
| Steel production emissions | Moderately stable | Changes with global energy mix, ~1-2%/year |

### Changing Factors (update needed periodically):

| Factor | Variability | Why |
|---|---|---|
| CH4 slip (methane) | High variability | Engine technology improving; FuelEU vs IMO disagree (3.1% vs 3.5% for DF-MS Otto) |
| WtT for fossil fuels | Moderate | Changes with refinery efficiency, energy mix; varies by region |
| WtT for alternative fuels | Very high | Depends on production pathway (green/blue/grey), electricity grid mix |
| NOx by engine tier | Changes with fleet age | New tiers reduce NOx significantly |
| Battery manufacturing emissions | Rapidly changing | Technology improving, grid decarbonizing |
| PM emission factors | Moderate | Changed significantly with IMO 2020 sulfur cap |

### Risk of outdated data:

- **CO2 factors:** Minimal risk. These are physical constants.
- **CH4 slip factors:** Moderate risk. Active research area. FuelEU and IMO are currently refining these values. Using the wrong slip factor can swing LNG lifecycle emissions by 10-20%.
- **WtT factors for renewables:** High risk. Green hydrogen/ammonia/methanol emissions depend heavily on the electricity source, which changes as grids decarbonize.
- **NOx factors:** Low risk for tank-to-wake. Fleet composition changes slowly.

### Cross-database comparison:

Different sources show notable disagreement for some values:
- **MGO WtW:** Average 88.2 gCO2e/MJ (range 81.8-173.9), CoV 3.9% -- relatively consistent
- **LNG WtW:** Average 79.9 gCO2e/MJ (range 63.0-166.0), CoV 11.7% -- moderate variation due to methane slip
- **Grey Methanol WtW:** Average 94.4 gCO2e/MJ (range 89.4-200.3), CoV 4.6%
- **Green Methanol WtW:** Average 13.6 gCO2e/MJ (range 4.5-33.0), CoV 72.3% -- huge variation
- **Green Ammonia WtW:** Range 0.0-36.3 gCO2e/MJ, CoV 140.8% -- extreme variation

---

## 5. Existing Open-Source Implementations

### Python Libraries and Tools

#### 1. py-open-IMO-CII-calculator
- **URL:** https://github.com/Etive-Mor/py-open-IMO-CII-calculator
- **What it does:** Calculates IMO Carbon Intensity Indicator (CII) ratings (A-E) for ships
- **Emission factors included:** CO2 conversion factors (Cf) for 8 fuel types from MEPC.364(79)
- **Fuel types:** Diesel/Gas Oil, LFO, HFO, LPG Propane, LPG Butane, Ethane, LNG, Methanol, Ethanol
- **PyPI:** Not yet published (stated as "coming soon")
- **Relevance to CETOS:** Limited -- only does CII rating, not full LCA. But contains the Cf factors in code.

#### 2. MarU (Kystverket/Norwegian Coastal Administration)
- **URL:** https://github.com/Kystverket/maru
- **What it does:** AIS-based ship traffic emission estimation for Norwegian waters. Estimates emissions distributed across ship types, sizes, and geographic areas.
- **Technology:** Python (PySpark for distributed processing)
- **Methodology:** Based on ICCT methodology and IMO 4th GHG Study
- **PyPI:** Not published
- **Relevance to CETOS:** Similar methodology base (IMO 4th GHG Study). Could be useful reference for emission factor tables in code.

#### 3. poeminv (Port Emission Inventory)
- **URL:** https://github.com/maritime-datasystems/poeminv
- **What it does:** Creates port emission inventories. Calculates ship emissions during movement and mooring.
- **Methodology:** Based on EPA Ports Emissions Inventory Guidance
- **Features:** Vessel information inference, track analysis, engine load calculation
- **PyPI:** Available via pip
- **Relevance to CETOS:** Has emission factor tables for port operations. Different methodology (EPA vs IMO).

#### 4. Brightway2
- **URL:** https://pypi.org/project/brightway2/
- **What it does:** General-purpose LCA framework in Python
- **Features:** Import ecoinvent and other databases, static and Monte Carlo calculations, parameterized models
- **PyPI:** Yes (`pip install brightway2`)
- **Relevance to CETOS:** Could be used as a backend for full LCA calculations if ecoinvent license is available. Overkill for basic emission factor multiplication.

#### 5. MariTEAM Model (NTNU/SINTEF)
- **URL:** https://mariteam.indecol.no/ (results viewer)
- **Publication:** "Global Shipping Emissions from a Well-to-Wake Perspective" (Env. Sci. & Tech., 2021)
- **What it does:** Bottom-up well-to-wake geospatial emission inventory for global shipping
- **Code availability:** Not found as a public GitHub repository. Academic model.
- **Relevance to CETOS:** Excellent methodological reference. Published emission factor tables in the paper.

#### 6. Ocean GHG (UCSB emLab)
- **URL:** https://emlab-ucsb.github.io/ocean-ghg/ais_model.html
- **What it does:** AIS-based ocean shipping emission model
- **Emission factors included:** CO2, NOx, SOx, PM, CH4, CO, N2O for main engine, auxiliary engine, and boilers (in g/kWh)
- **Relevance to CETOS:** Clean, simple emission factor tables that could be directly adopted. Well-documented methodology.

### Key Academic Papers with Implementation Details:
- Balcombe et al. (2022) -- "How to decarbonise international shipping" -- comprehensive WtW factors
- Lindstad et al. (2020) -- "Reduction of maritime GHG emissions" -- well-to-wake methodology
- Gilbert et al. (2018) -- MariTEAM model framework
- Brynolf et al. (2014) -- LCA of marine fuels (foundational work)

---

## 6. Regulatory Context

### 6.1 FuelEU Maritime (EU) -- Regulation (EU) 2023/1805
- **Methodology:** Well-to-Wake (WtW), combining WtT and TtW
- **Unit:** GHG intensity in gCO2eq/MJ
- **Reference value:** 91.16 gCO2eq/MJ (baseline)
- **Reduction targets:** -2% from 2025, -6% from 2030, -14.5% from 2035, -31% from 2040, -62% from 2045, -80% from 2050
- **Mandatory emission factors:** Yes -- Annex II provides default values. For fossil fuels, WtT and TtW CO2 defaults are mandatory. CH4 and N2O can use actual measured values if certified.
- **Gases:** CO2, CH4, N2O (expressed as CO2eq)
- **GWPs used:** Currently RED II (1, 25, 298); transitioning to AR5 (1, 28, 265)
- **Scope:** Ships >5,000 GT calling at EU/EEA ports
- **Effective:** From 1 January 2025

### 6.2 IMO LCA Guidelines -- MEPC.391(81) (2024)
- **Methodology:** Well-to-Wake
- **Unit:** gCO2eq/MJ
- **Coverage:** 128 fuel/energy pathways across 14 fuel groups (but only 3 pathways have full WtW values currently)
- **Gases:** CO2, CH4, N2O
- **GWPs:** IPCC AR5 (1, 28, 265)
- **Status:** Guidelines adopted March 2024. GESAMP WG46 developing additional default factors. Full factor set expected by 2025-2026.
- **Application:** Will be used in the IMO Net-Zero Framework and future mandatory GHG pricing/intensity regulations (approved at MEPC 83, taking effect from 2028).

### 6.3 CII (Carbon Intensity Indicator) -- MEPC.354(78)
- **Methodology:** Tank-to-Wake only (CO2 only, not CH4 or N2O)
- **Emission factors:** Uses Cf values from MEPC.308(73) -- CO2 per tonne fuel
- **Unit:** Annual Efficiency Ratio (AER) = (total CO2) / (DWT * distance)
- **Rating:** A-E scale based on statistical distribution for ship category
- **Scope:** Ships >5,000 GT
- **Effective:** From 1 January 2023
- **Limitation:** CO2 only, tank-to-wake only. Does not capture methane slip or upstream emissions.

### 6.4 EU ETS for Maritime -- Directive 2003/87/EC (amended)
- **Methodology:** Tank-to-Wake (expanding to include CH4 and N2O from 2026)
- **Emission factors:** IMO default Cf values for CO2. From 2026: also CH4 and N2O.
- **Scope:** Ships >5,000 GT (from 2025: also ships 400-5,000 GT and offshore vessels)
- **Coverage:** 100% of intra-EU voyages, 50% of EU-to/from-non-EU voyages
- **Phase-in:** 40% of emissions surrendered in 2024, 70% in 2025, 100% from 2026
- **Cost:** Allowance price (currently ~EUR 60-80/t CO2)
- **Biofuels/e-fuels:** Zero CO2 emission factor if meeting RED II sustainability criteria
- **Reporting:** Via THETIS-MRV platform (EMSA)

### 6.5 IMO Net-Zero Framework (MEPC 83, adopted 2025)
- **Methodology:** Well-to-Wake
- **Takes effect:** 2028
- **Maximum biofuel WtW:** 20.80 gCO2eq/MJ (if pathway unknown)
- **Maximum RFNBO WtW (e-fuels):** 28.2 gCO2eq/MJ (FuelEU) / 19.0 gCO2eq/MJ (IMO)
- **Significance:** First global mandatory well-to-wake regulation for shipping

### Summary of which emission factors are mandatory:

| Regulation | CO2 (Cf) | CH4 | N2O | NOx | SOx | PM | WtT | Scope |
|---|---|---|---|---|---|---|---|---|
| CII | Mandatory (IMO) | No | No | No | No | No | No | TtW only |
| EU ETS | Mandatory (IMO) | From 2026 | From 2026 | No | No | No | No | TtW |
| FuelEU Maritime | Mandatory (Annex II) | Default (Annex II) | Default (Annex II) | No | No | No | Mandatory (Annex II) | WtW |
| IMO NZF (2028) | Mandatory | Mandatory | Mandatory | No | No | No | Mandatory | WtW |

---

## 7. Practical Recommendation for CETOS

### 7.1 Minimum Viable Set of Emission Factors

Given that CETOS already calculates fuel consumption in kg by fuel type, the minimum viable LCA addition requires:

**Level 1 -- Tank-to-Wake CO2 only (simplest, matches CII/EU ETS):**

```python
# CO2 conversion factors (t CO2 / t fuel) from IMO MEPC.308(73)
CO2_FACTORS = {
    "HFO": 3.114,
    "MDO": 3.206,    # CETOS uses MDO
    "LNG": 2.750,
    "MeOH": 1.375,   # CETOS uses MeOH
}
```

This is literally 4 numbers multiplied by fuel consumption in kg. Gives total CO2 in kg.

**Level 2 -- Tank-to-Wake GHG (CO2 + CH4 + N2O, matches EU ETS from 2026):**

Add CH4 and N2O factors. CH4 requires knowing the engine type (already available in CETOS as `propulsion_engine_type`):

```python
# TtW CH4 slip (fraction of fuel mass)
CH4_SLIP = {
    ("LNG", "LNG-Otto-MS"): 0.031,    # FuelEU: 3.1%
    ("LNG", "LBSI"): 0.026,           # 2.6%
    ("HFO", "SSD"): 0.00005,
    ("HFO", "MSD"): 0.00005,
    ("MDO", "SSD"): 0.00005,
    ("MDO", "MSD"): 0.00005,
    # ... etc
}

# TtW N2O (g N2O / g fuel)
N2O_FACTORS = {
    "HFO": 0.00018,
    "MDO": 0.00018,
    "LNG": 0.00011,
    "MeOH": 0.00018,
}

# GWP-100 (IPCC AR5)
GWP = {"CO2": 1, "CH4": 28, "N2O": 265}
```

**Level 3 -- Full Well-to-Wake (matches FuelEU Maritime and IMO NZF):**

Add WtT factors:

```python
# WtT emission factors (gCO2eq/MJ) from FuelEU Annex II
WTT_FACTORS = {
    "HFO": 13.5,
    "MDO": 14.4,
    "LNG": 18.5,
    "MeOH": 31.3,    # from natural gas; renewable methanol much lower
}

# Lower Calorific Values (MJ/kg) for converting fuel mass to energy
LCV = {
    "HFO": 40.2,
    "MDO": 42.7,
    "LNG": 48.0,
    "MeOH": 19.9,
}
```

**Level 4 -- Air pollutants (NOx, SOx, PM) for environmental assessment:**

Add energy-based emission factors from EMEP/EEA or IMO 4th GHG Study.
Requires engine power and load (already calculated by CETOS).

### 7.2 Where to Get These Factors (Free, Reliable, Stable)

1. **CO2 factors (Cf):** IMO MEPC.308(73) -- free, definitive, stable for decades
2. **CH4/N2O factors:** FuelEU Maritime Annex II -- free, legally binding, updated periodically
3. **WtT factors:** FuelEU Maritime Annex II -- free, legally binding for fossil fuels
4. **LCV values:** FuelEU Maritime Annex II or IMO MEPC resolutions -- free
5. **NOx/SOx/PM:** EMEP/EEA Guidebook 2023 or IMO 4th GHG Study -- free
6. **GWP values:** IPCC AR5 -- free, standard

### 7.3 Simplest Implementation Path

**Phase 1 (immediate, ~1 day of work):**
- Add CO2 conversion factors to CETOS
- New function: `estimate_co2_emissions(fuel_consumption_kg, fuel_type) -> kg_CO2`
- This enables CII calculation and basic EU ETS compliance

**Phase 2 (short-term, ~2-3 days):**
- Add CH4 slip factors (by fuel_type + engine_type combination)
- Add N2O factors
- Add GWP conversion
- New function: `estimate_ttw_ghg_emissions(fuel_consumption_kg, fuel_type, engine_type) -> dict` returning CO2, CH4, N2O in both mass and CO2eq
- This enables EU ETS compliance from 2026

**Phase 3 (medium-term, ~1 week):**
- Add WtT emission factors and LCV values
- New function: `estimate_wtw_ghg_intensity(fuel_consumption_kg, fuel_type, engine_type) -> gCO2eq_per_MJ`
- This enables FuelEU Maritime compliance calculation
- Add support for alternative fuel types (ammonia, hydrogen, biofuels) with configurable WtT factors

**Phase 4 (optional, for environmental assessment):**
- Add NOx, SOx, PM emission factors
- Add engine load dependency
- Add NOx Tier (0/I/II/III) based on engine age (CETOS already has `propulsion_engine_age`)

### 7.4 What Should Be Hardcoded vs. Configurable vs. External

| Data | Strategy | Rationale |
|---|---|---|
| CO2 factors (Cf) | **Hardcoded** | Stoichiometric. Never change. |
| LCV values | **Hardcoded** | Physical constants of fuel. |
| GWP values (AR5) | **Hardcoded with version** | Change only with IPCC reports (~10 years). Include both AR4/RED II and AR5 options. |
| WtT for fossil fuels | **Hardcoded** | FuelEU mandates specific values for fossil fuels. |
| CH4 slip by engine type | **Configurable (with defaults)** | Active area of research. FuelEU and IMO disagree on some values. Defaults from FuelEU Annex II. |
| N2O factors | **Configurable (with defaults)** | Relatively stable but may be updated. |
| WtT for alternative fuels | **Configurable (no hardcoded default)** | Varies enormously by production pathway. User must specify. |
| NOx emission factors | **Configurable (with defaults by Tier)** | Depend on engine tier which maps from `engine_age`. |
| SOx factors | **Calculated** | From fuel sulfur content (user input or default by fuel type). |
| PM factors | **Configurable (with defaults)** | Depend on fuel type and post-2020 regulations. |
| Battery/fuel cell manufacturing emissions | **External/optional** | Not part of core fuel LCA. Provide as utility if requested. |

### 7.5 CETOS-Specific Integration Points

CETOS already provides these outputs that map directly to LCA inputs:

| CETOS Output | LCA Input |
|---|---|
| `fuel_consumption_kg` (from `estimate_fuel_consumption_of_propulsion_engines`) | Multiply by Cf for CO2, by CH4_SLIP for CH4, by N2O_FACTOR for N2O |
| `propulsion_engine_fuel_type` (HFO, MDO, MeOH, LNG) | Selects correct emission factor set |
| `propulsion_engine_type` (SSD, MSD, HSD, LNG-Otto-MS, LBSI, etc.) | Selects CH4 slip factor, NOx emission factor |
| `propulsion_engine_age` (before_1984, 1984-2000, after_2000) | Maps to NOx Tier (0/I/II/III) |
| `energy_consumption_kwh` (from `estimate_energy_consumption`) | For energy-based emission factors (NOx, PM in g/kWh) |
| Battery system sizing (from `estimate_vessel_battery_system`) | For battery manufacturing LCA |
| Hydrogen system sizing (from `estimate_vessel_gas_hydrogen_system`) | For fuel cell/H2 tank manufacturing LCA |

### 7.6 Fuel Types to Add to CETOS

CETOS currently supports: HFO, MDO, MeOH, LNG

For comprehensive LCA, consider adding:
- LFO (Light Fuel Oil) -- still used on some vessels
- LPG (Propane/Butane) -- growing as marine fuel
- Ammonia (NH3) -- zero-carbon TtW, high WtT
- Hydrogen (H2) -- zero-carbon TtW (CETOS already models H2 energy systems)
- Ethanol -- biofuel option
- Bio-methanol -- distinct WtT from fossil methanol
- Bio-LNG -- distinct WtT from fossil LNG
- VLSFO (Very Low Sulfur Fuel Oil) -- post-2020 dominant fuel, similar to MDO/blend

---

## Appendix: Key Reference Values Summary

### Well-to-Wake GHG Intensity (gCO2eq/MJ) -- Fossil Fuels

| Fuel + Engine | WtT | TtW | WtW | Source |
|---|---|---|---|---|
| HFO + SSD/MSD | 13.5 | ~77.5 | ~91.0 | FuelEU baseline |
| MDO/MGO + SSD/MSD | 14.4 | ~75.3 | ~89.7 | FuelEU |
| LNG + DF-MS Otto | 18.5 | ~57.3 + CH4 slip | ~79.9 (avg) | Literature avg |
| LNG + DF-SS Otto | 18.5 | ~57.3 + CH4 slip | ~73-76 | Lower slip |
| LNG + HPDF 2-stroke | 18.5 | ~57.3 + minimal slip | ~69-72 | Lowest LNG |
| Methanol (fossil) | 31.3 | ~69.0 | ~94.4 (avg) | Literature avg |
| Methanol (green) | varies | ~69.0 | ~13.6 (avg) | Literature avg |
| Ammonia (grey) | 121.0 | 0 (CO2) | ~83-130 | WtT dominates |
| Ammonia (green) | ~0-36 | 0 (CO2) + N2O | ~0-36 | Near-zero possible |

### GWP Values (100-year)

| Gas | AR4 (RED II) | AR5 (IPCC 2013) | AR6 (IPCC 2021) |
|---|---|---|---|
| CO2 | 1 | 1 | 1 |
| CH4 | 25 | 28 | 27.0 (fossil) / 29.8 (non-fossil) |
| N2O | 298 | 265 | 273 |

---

## Sources

- [IMO Framework on Life Cycle GHG Intensity of Marine Fuels](https://www.imo.org/en/ourwork/environment/pages/lifecycle-ghg---carbon-intensity-guidelines.aspx)
- [IMO MEPC.391(81) - 2024 LCA Guidelines](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.391(81).pdf)
- [FuelEU Maritime Regulation (EU) 2023/1805](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023R1805)
- [IMO Fourth GHG Study 2020](https://www.imo.org/en/ourwork/environment/pages/fourth-imo-greenhouse-gas-study-2020.aspx)
- [ICCT: Accounting for Well-to-Wake CO2 Equivalent Emissions (2021)](https://theicct.org/publication/accounting-for-well-to-wake-carbon-dioxide-equivalent-emissions-in-maritime-transportation-climate-policies/)
- [Comparative Analysis of Alternative Fuels in a Well-to-Wake Perspective (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10884460/)
- [Well-to-Tank Carbon Intensity Variability of Fossil Marine Fuels (arXiv)](https://arxiv.org/html/2502.07201v1)
- [GREET Model (US DOE/Argonne National Lab)](https://www.energy.gov/eere/bioenergy/articles/greet-greenhouse-gases-regulated-emissions-and-energy-use-transportation)
- [ecoinvent Database](https://ecoinvent.org/)
- [OpenLCA Nexus](https://nexus.openlca.org/)
- [Brightway LCA Framework](https://brightway.dev/)
- [EMEP/EEA Guidebook 2023 - Navigation](https://www.eea.europa.eu/en/analysis/publications/emep-eea-guidebook-2023)
- [EXIOBASE](https://www.exiobase.eu/)
- [Sphera/GaBi LCA Database](https://sphera.com/)
- [DNV: Comparison of Alternative Marine Fuels](https://www.dnv.com/maritime/publications/alternative-fuel-assessment-download/)
- [Lloyd's Register: Cradle-to-Grave LNG Carrier Analysis](https://www.lr.org/en/knowledge/horizons/march-2024/from-the-cradle-to-the-grave-emissions-from-an-lngcs-life-cycle/)
- [Sustainable Ships: Emission Properties for EU ETS, FuelEU and IMO](https://www.sustainable-ships.org/stories/2025/fuel-emissions-properties)
- [py-open-IMO-CII-calculator (GitHub)](https://github.com/Etive-Mor/py-open-IMO-CII-calculator)
- [MarU - Maritime Emissions Model (GitHub)](https://github.com/Kystverket/maru)
- [poeminv - Port Emission Inventory (GitHub)](https://github.com/maritime-datasystems/poeminv)
- [MariTEAM Model](https://mariteam.indecol.no/)
- [Ocean GHG AIS-based Emissions Model (UCSB)](https://emlab-ucsb.github.io/ocean-ghg/ais_model.html)
- [IMO MEPC 83 Summary (DNV)](https://www.dnv.com/news/2025/imo-mepc-83-ghg-requirements-approved-taking-effect-from-2028/)
- [GESAMP WG46 on Marine Fuel LCA](http://www.gesamp.org/work/groups/gesamp-working-groupo-n-life-cycle-ghg-intensity-of-marine-fuels)
- [EU ETS Maritime FAQ](https://climate.ec.europa.eu/eu-action/transport-decarbonisation/reducing-emissions-shipping-sector/faq-maritime-transport-eu-emissions-trading-system-ets_en)
- [IPCC 2006 Guidelines Vol. 2 Ch. 2](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf)
- [ClassNK: IMO Guidelines on Life Cycle GHG Intensity of Marine Fuels](https://www.classnk.or.jp/hp/pdf/research/rd/2024/10_e03.pdf)
