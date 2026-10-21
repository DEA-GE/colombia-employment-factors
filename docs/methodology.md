# Employment-factor methodology

The production command and file contracts are documented in [README](../README.md).
Manual numeric records and original-source notes live in
`data/curated/employment_factors_input.csv`. The build adds 36 JEDI workbook
records in memory, without writing extracted values back into curated inputs.
Native workbooks and PDFs are preserved unchanged.

`data/curated/catalogue_rows.csv` records the 26 approved sheet/name mappings and
CAPEX/OPEX row numbers and labels. Extraction checks those labels and sheet
coverage, reads saved values in C:E, and derives dimensionless ratios. Original
cost units remain in row labels, including storage CAPEX per MWh. The historical
first-column year convention is retained (the unused biogas sheet labels it 2023).
Technology assumptions use the same workbook read and the existing fallback rules.

The calculation order is source assembly, rooftop transfer, sparse projection,
combined factors, annual interpolation, selective productivity variants, and
default selection. Preserve this order: productivity adjustment recomputes combined
factors using adjusted construction and the existing unscaled manufacturing share.

## Method Summary

For Rutovitz 2015 construction, manufacturing, and O&M rows, the package applies
the Latin America 2030 decline factors from Rutovitz Table 9, excluding fuel rows
and treating dashes in Table 9 as a 0% decline factor. The applied formula is:

```text
EF_2030 = EF_2015 * (1 - decline_factor_2030)
```

Coal and nuclear use a 1.00 multiplier where Table 9 has a dash. Python implements all calculations; optional Excel exports contain values only.

For non-Rutovitz-2015 rows with a 2024 base year, the package applies CAPEX/OPEX
transition ratios derived from the preserved catalogue. The same ratios are
recorded in `data/audit/capex_opex_ratios_2024_2030_2050.csv`.
Construction, manufacturing, and combined construction-and-manufacturing factors
use CAPEX ratios; O&M factors use OPEX ratios. Corrected QBIS offshore wind rows
use a 2022 base year; for simplicity, the same Technology Catalogue
`2030/2024` ratio is applied to these 2022 base values. The projection is
sequential:

```text
EF_2030 = EF_base * ratio_2030_2024
EF_2050 = EF_2030 * ratio_2050_2030
```

For Rutovitz 2015 rows already projected to 2030, the package applies the same
CAPEX/OPEX `2050/2030` transition from the 2030 value:

```text
EF_2050 = EF_2030 * ratio_2050_2030
```

Technologies without a matching catalogue ratio row, such as transmission,
solar thermal (CSP), and ocean, are projected as constant values. Offshore wind
(floating) has no `2030/2024` ratio in the catalogue table, so its 2030 value is
held constant from the available base year and its 2050 value uses the available
`2050/2030` ratio.

After sparse projection and before yearly interpolation, the pipeline derives
`Construction&Manufacturing` rows for Rutovitz sources that report construction
and manufacturing separately:

```text
Rutovitz 2015: Construction&Manufacturing = Construction + local_share * Manufacturing
Rutovitz 2015 renewables: Construction&Manufacturing = Construction + 0.5 * Manufacturing
Rutovitz 2025: Construction&Manufacturing = Construction + Manufacturing
```

For Rutovitz 2015, the local manufacturing share follows Table 17 of the 2015
methodology report. Fossil fuel, biomass, hydro, and nuclear technologies use a
100% manufacturing share because the report assumes manufacturing occurs within
the region for those technologies. Renewable technologies covered by Table 17
use a 0.5 local manufacturing factor, equivalent to a 50% local manufacturing
share and corresponding to the Latin America 2010 entry. This `0.5` factor is
applied to geothermal, ocean, offshore wind, onshore wind, rooftop solar PV,
solar thermal (CSP), and utility-scale solar PV when present in the Rutovitz
2015 source.

For Rutovitz 2025, the curated manufacturing values are the report's total
manufacturing factors, so the combined value sums construction and manufacturing
without applying a local manufacturing share. Local/onshore manufacturing shares
could be derived from Rutovitz 2025 Table 3 by dividing the Australian/onshore
manufacturing value by the total manufacturing value; Table 4 provides a more
detailed comparison of current factors and previous sources.

The generated audit file
`data/audit/capex_opex_ratios_2024_2030_2050.csv` records the CAPEX and fixed
O&M values extracted from `docs/sources/datos_cuantitativos_EN.xlsx` for each
technology sheet, excluding `Guide&Cover` and `Index`. It includes the selected
source row labels and row numbers, a normalized technology name without sheet
numbering, the 2024, 2030, and 2050 values, and the transition ratios
`2030/2024` and `2050/2030`. The builder derives this table directly from the preserved catalogue using
`data/curated/catalogue_rows.csv`, then uses its ratios in memory. The CSV is
a generated audit record, never a manually maintained production input.

### QBIS offshore wind factors

QBIS 2020 and QBIS 2023 offshore wind factors are treated as direct jobs only.
QBIS 2020 reports direct FTE in Table 5 and calculates indirect and induced
effects separately in Tables 6-7. QBIS 2023 reports the fixed and floating model
configuration as direct labour input in Figures 2.3-2.4 and Tables 2.1-2.2,
then adds indirect FTE separately in Chapter 3 using an input-output model.

For construction and manufacturing, QBIS FTE/GW values are cumulative labour
input over project phases and are therefore comparable to job-years/MW. The
curated factors exclude decommissioning and O&M:

- QBIS 2020 fixed-bottom generic offshore wind:
  `(574 + 2655 + 2820 + 781) / 1000 = 6.83 job-yr/MW`.
- QBIS 2023 fixed-bottom offshore wind:
  `(131 + 2666 + 2608 + 996) / 1000 = 6.401 job-yr/MW`.
- QBIS 2023 floating offshore wind:
  `(208 + 4210 + 8348 + 1702) / 1000 = 14.468 job-yr/MW`.

QBIS O&M values are reported as lifetime FTE/GW over 25 years, so they are
annualized to job/MW before use:

- QBIS 2020: `1907 / 1000 / 25 = 0.0763 job/MW`.
- QBIS 2023 fixed-bottom: `2640 / 1000 / 25 = 0.1056 job/MW`.
- QBIS 2023 floating: `6041 / 1000 / 25 = 0.2416 job/MW`.

### Yearly 2024-2055 tables

The sparse original/projection table is expanded to a yearly all-source table at
`src/colombia_employment_factors/data/employment_factors_yearly_2024_2055.csv`. It includes eligible
FTE factor types only: construction, manufacturing, combined
construction-and-manufacturing, and O&M. Fuel rows are excluded from the yearly
FTE table.

For each source, technology, factor type, job type, and unit, missing years are
filled by linear interpolation between known datapoints:

- Rutovitz 2015 rows use the 2015 source value and the 2030 projected value to
  interpolate 2024-2029.
- Other projected rows interpolate from their available base year, usually 2024
  and for corrected QBIS rows 2022, to 2030.
- Rows interpolate from 2030 to 2050 using the projected 2050 value.
- Values from 2051 through 2055 are held constant at the 2050 value because the
  Technology Catalogue ratio table ends in 2050.

The model-ready table at
`src/colombia_employment_factors/data/employment_factors_model_default_2024_2055.csv` filters the
yearly all-source table to one default source per technology. This is the table
intended for direct retrieval by model workflows such as OSeMOSYS post-processing.

### Technology lifetime and construction-time assumptions

The package includes
`src/colombia_employment_factors/data/technology_assumptions_2024.csv`, so other
Python libraries can retrieve lifetime and construction-time assumptions by the
same technology names used in the employment-factor tables.

The table is generated from `docs/sources/datos_cuantitativos_EN.xlsx`. For each
technology, the default rule is to use the 2024 `Technical lifetime (years)` and
`Construction time (years)` values from the mapped Colombian Technology
Catalogue sheet. The table records the source sheet, row numbers, and source
year for each metric.

Documented exceptions:

- `Offshore wind (floating)` has no 2024 catalogue lifetime or construction
  time. The table uses the 2030 catalogue values, including the requested 2030
  construction time of 2.5 years.
- `Ocean` and `Solar thermal (CSP)` have no matching catalogue sheet. Their
  construction times use Rutovitz 2015 Table 1: 2 years for ocean and 2 years
  for solar thermal. Their lifetimes are left blank because Table 1 does not
  provide technical lifetime assumptions.
- Transmission technologies have no matching Colombian Technology Catalogue row
  and no construction-time row in Rutovitz 2015 Table 1. Their lifetime and
  construction-time values are therefore left blank and flagged in the `notes`
  column.

Example retrieval from another Python package:

```python
from colombia_employment_factors import (
    get_model_employment_factors,
    get_technology_assumption,
)

technology = "Utility-scale solar PV"
factors = get_model_employment_factors()
assumption = get_technology_assumption(technology)

cm_2024 = factors[
    (factors["Technology"] == technology)
    & (factors["Factor_Type"] == "Construction&Manufacturing")
    & (factors["Year"] == 2024)
].copy()

cm_2024["annualized_fte_per_mw"] = (
    cm_2024["Value_Numeric"] / assumption["construction_time_years"]
)
```

Default source choices are defined in
`colombia_employment_factors.mappings.DEFAULT_SOURCE_BY_TECHNOLOGY`:

- QBIS 2023 for fixed and floating offshore wind.
- Rutovitz 2025 for storage technologies and available transmission rows.
- I-JEDI for direct, indirect, and induced renewable rows for biomass,
  geothermal, onshore wind, and utility-scale solar PV.
- Rooftop factors anchored to I-JEDI Colombia: Rutovitz 2025 ratios for Direct, matched US-JEDI ratios for Indirect and Induced. If the US utility run is absent, the checksum-locked published rooftop baseline is explicitly retained.
- Rutovitz 2015 for the remaining technologies.

`Transmission (single circuit)` retains the established JEDI-US default. A
Rutovitz 2025 construction factor of 0.7 job-yr/km is present in the manual
inputs; the previous absence-based rationale was incorrect. Changing this
selection requires a separate decision because units and category coverage differ.


## Source boundaries and transfer policy

Original JEDI workbooks are preserved in `data/raw`. No build executes VBA,
updates external links or asks openpyxl to recalculate formulas. Saved numeric
caches, source formulas (including array formulas), settings, named ranges,
hidden sheets, external-link inventory and SHA-256 hashes are recorded in
the `jedi_sources` section of `employment_factor_provenance.json`. Capacity and output-total identities
are checked, but this is not proof of full Excel recalculation. If a cache is
missing/inconsistent, recalculate a preserved working copy in the intended Excel
version under an approved procedure, save it, and review the new settings/hash.

## Rooftop transfer: Rutovitz direct ratios and US-JEDI wider impacts

The central `solar_ratio_method` is `rutovitz-direct`. Rutovitz et al. (2025),
Table 3, p.4, supplies the direct ratios from the 2024 rows in
`data/curated/employment_factors_input.csv`:

- Construction: rooftop 4.19 / utility 1.61 = **2.60248447205**.
- O&M: rooftop 0.13 / utility 0.09 = **1.44444444444**.

The displayed 2.602 and 1.444 are rounded descriptions; calculations use the
fractions above. The construction-only ratio is explicitly a proxy for I-JEDI's
combined **Direct Construction&Manufacturing** anchor. It does not create a
construction/manufacturing split or add global manufacturing employment.
No construction-plus-total-manufacturing ratio or sensitivity is implemented.
The Australian rooftop mix and employment boundary are approximations for
Colombia, and the ratio is not a Colombia-specific observation.

Rutovitz does not supply equivalent indirect/induced ratios. Those four factors
retain the matched US-JEDI method below. Thus the selected rooftop source label
explicitly identifies Rutovitz direct / US-JEDI indirect-induced ratios. Provenance
records each ratio's source, input phase, numerator, denominator and boundary
assumption, plus a hash of the preserved Rutovitz paper. The former all-US-JEDI
method remains available via `--solar-ratio-method us-jedi` as an isolated comparison.

Policy lives in `data/assumptions/employment_methodology.json`. The authoritative
US inputs are `data/raw/jedi-pv-model.xlsm` (200 five-kW residential systems,
1 MW DC total, fixed mount) and `data/raw/jedi-pv-model_utility_scale.xlsm`
(one 100-MW DC utility system, single-axis tracking). Both are release
PV05.20.21, United States, construction year 2024 and dollar year 2010. Each
saved result is divided once by its own total MW before forming the ratios.
Approved capacities are explicit in policy; unexpected capacities or inconsistent
saved input/summary totals fail validation. The utility run is now available.

For each employment phase p (Construction&Manufacturing or O&M), define:

```
R[Construction&Manufacturing,Direct,2024] = Rutovitz_rooftop_Construction / Rutovitz_utility_Construction
R[O&M,Direct,2024] = Rutovitz_rooftop_OM / Rutovitz_utility_OM
R[p,b,2024] = US_residential[p,b,2024] / US_utility[p,b,2024]  # b = Indirect or Induced
CO_rooftop[p,b,2024] = R[p,b,2024] * I_JEDI_CO_utility[p,b,2024]
```

The dimensions are FTE-years/MW for construction-period labour and annual
FTE/MW for O&M. Divide residential totals by 1 MW and utility totals by 100 MW;
the kW-to-MW conversion applies to capacity, not again to the employment factor.
The ratio transfer adopts the I-JEDI anchor capacity basis without an extra
DC/AC multiplier; this is a documented assumption, not a verified equivalence
of technology-specific inverter loading ratios. Residential portfolios do not
establish commercial/industrial rooftop factors.

The rebuilt model default selects the transferred Colombian rooftop series.
The checksum-locked `data/audit/baseline_model_default_23b7f592.csv` remains as
rollback evidence and a documented fallback if the utility input is absent.
Use `--require-solar-ratios` to prohibit fallback in release checks; CI now does so.
Absolute US factors remain available as source series.

The shared 2010 dollar year is a user-approved convention for the relative
comparison, not proof that all default costs are in 2010 prices. The workbooks
record 2019 in `Multipliers!D2`; `Deflators!F7` depends on the dollar selector,
and `Deflators!C45` documents projected inflation for 2021-2040. Changing only
the construction-year label does not establish contemporary labour productivity.
Both saved files have `ProjectData!B26=N` (view/edit project costs); their saved
results are authoritative, but we do not claim every detailed cost is an untouched
default. The audit records base-cost formulas, monetary convention, deflator,
settings and file hashes. No native workbook is changed or recalculated.
A 2024-dollar ratio sensitivity has not been run; it requires two separately
recalculated copies and cannot be inferred by editing cached values.

Keep simple source categories: US on-site labour/services -> Direct; supply
chain -> Indirect; induced -> Induced. I-JEDI Direct reflects expenditures
across industries and is not identical to US on-site Direct. Relative transfer
between these categories is an approximation. Indirect is not Manufacturing.
Keep the combined phase authoritative where a clean split is unavailable;
do not add C, M and C&M together. US manufacturing subtotal zero is a run
assumption, not zero global manufacturing employment. Construction results are
one-year labour equivalents, not peak headcount or recurring annual jobs.

## Productivity policy

The package defaults to **no additional productivity transfer** (multiplier 1.0).
The 0.32 LATAM/OECD non-agricultural productivity ratio is retained only as an
optional sensitivity: `get_model_employment_factors(productivity_transfer=True)`.
The default was changed because of concern that the extra multiplier overstates
employment in the targeted technologies; this does not establish a replacement
empirical productivity estimate.

The optional ratio is a high-level modelling assumption. The source audit in
`PRODUCTIVITY_EVIDENCE.md` verifies Rutovitz's published-table arithmetic
and the OECD per-hour comparison, but does not reproduce 0.32. Archived 2023 WDI
aggregates yield 0.369767 for the whole economy and an approximate non-agricultural
ratio of 0.384924. These are diagnostics, not adopted replacements. Compute the
optional inverse as 3.125; display approximately 3.1.
World Bank SL.GDP.PCAP.EM.KD is GDP per person employed in constant 2021 PPP
dollars. OECD productivity per hour is a plausibility check, not the same series.
LAC excluding high-income economies is a proxy for the intended LATAM region,
not a Colombia observation or a technology-specific productivity measurement.

The JSON eligibility table is explicit by source, technology and phase. When enabled, apply
the inverse once to eligible direct construction or O&M factors AFTER yearly
interpolation, retaining the original source series alongside labelled regional
variants. The recent proxy is fixed across 2024-2055, not represented as a 2015
observation. Do not multiply I-JEDI Colombia, its derived rooftop factors,
already-LATAM values, nuclear O&M, bioenergy, indirect/induced employment or
global manufacturing totals. Unknown provenance stays unadjusted. Australian
and French labour factors are OECD proxies, not OECD averages. The policy is
an approved transfer assumption; it does not establish causal sector-level
productivity differences.

Coal construction/O&M match OECD Table 1 (Rutovitz 2015, p.5), despite the old
CSV regional note. Large hydro combines OECD construction 7.4 with LATAM O&M
0.6 (Table 2 p.8); adjust only its construction. Manufacturing localisation is
not changed: recompute C&M using adjusted C and the existing, unscaled M share.
The historical LATAM manufacturing share is regional, not evidence of Colombian
domestic content. This work does not make all legacy totals strictly domestic.
Mixed QBIS construction/manufacturing is not scaled; operational direct labour
is eligible. Keep localisation uncertainty separate from productivity.

Low/central/high employment-intensity screening cases use productivity ratios
0.33/0.32/0.30, i.e. multipliers 3.030303/3.125/3.333333. These are not confidence
limits. Generate isolated scenario outputs without changing packaged defaults:

```sh
python scripts/build_employment_factors.py --productivity-transfer selective --scenario low
python scripts/build_employment_factors.py --productivity-transfer selective --scenario high
python scripts/build_employment_factors.py --productivity-transfer selective
```

## Temporal projections and nuclear

Keep existing Rutovitz decline, catalogue CAPEX/OPEX proxies, interpolation,
constant missing-technology bridges and the post-2050 hold through 2055. Cost
declines are not measured labour-learning rates. Solar ratios are transferred
at 2024 and each technology subsequently follows its own catalogue mapping;
future rooftop/utility ratios can change. With verified US utility input,
`--solar-projection constant-relative` provides an isolated sensitivity based
on the same current-year Colombian utility factors. No ranking is enforced.

Nuclear factors remain unchanged. The model currently has one generic nuclear
mapping, not verified separate large-reactor/SMR mappings. A future SMR factor
requires reactor design, module/site MWe, staffing boundary, FOAK/NOAK and
localisation evidence. Site staffing/MWe and construction FTE-years/MWe are
different quantities; no percentage uplift is invented here.

## Outputs, compatibility and rollback

Required CSV columns and explicit-path loading are unchanged. Model retrieval
now defaults to no transfer and accepts the keyword-only `productivity_transfer`
flag to opt into the bundled adjusted table. Base-source
selectors remain in mappings.py; the builder resolves policy-specific sources.
The provenance `default_sources` mapping and model CSV show the actual selected sources. Source-year sparse tables remain unadjusted temporal
series; the all-source YEARLY table includes adjusted variants. Separate scenarios
must not be combined before interpolation or default selection.

The five central CSVs are stored once under package `data/`, with LF newlines.
`employment_factors_model_default_2024_2055.csv` has no additional productivity
transfer; `employment_factors_model_latam_productivity_2024_2055.csv` retains the
selective 0.32 variant. A normal build generates both. The historical
`source-refresh` comparison is superseded for consumer use by the packaged default.
`employment_factor_provenance.json` records repository revision, dirty state,
input/content hashes, output checksums, scenario and solar readiness. Top-level
settings describe the default; `optional_productivity_model` records the adjusted
table's filename, ratio, multiplier and selected sources. The source
revision identifies the committed inputs and generator at build time. The dirty
flag can include generated outputs awaiting their separate artifact commit; it
must not be interpreted as proof that input/code changes are uncommitted.
The consumer dependency pins the artifact commit containing the generated data.
No manifest attempts to contain the SHA of its own enclosing commit. Optional generated workbooks contain values only and require no Excel recalculation.
Native source workbooks still rely on their preserved caches, whose limitations are described above.

The baseline snapshot and Git preserve rollback evidence. Restore a prior
approved source revision/assumptions, regenerate, compare its checksums, and
resynchronise the consumer snapshot. Do not reset branches or overwrite native
source workbooks. No commit, push or PR publication is performed by these scripts.

Sources: NLR JEDI results https://www.nlr.gov/analysis/jedi/results ; PV release
https://www.nlr.gov/analysis/jedi/pv ; I-JEDI
https://www.nlr.gov/analysis/jedi/international ; World Bank indicator
https://data.worldbank.org/indicator/SL.GDP.PCAP.EM.KD ; local Rutovitz 2015
methodology report, Tables 1, 2, 6 and 8, pp.5, 8, 15 and 17.

## Solar PV transfer: numerical reference

The model-ready rooftop series uses Rutovitz direct ratios and US-JEDI indirect
and induced ratios, anchored to I-JEDI Colombia utility PV. The supplied US workbooks
are preserved unchanged: `data/raw/jedi-pv-model.xlsm` (1 MW DC residential
portfolio) and `data/raw/jedi-pv-model_utility_scale.xlsm` (one 100 MW DC utility
plant). Both use construction year 2024, dollar year 2010, and release PV05.20.21.

For US-derived ratios, the utility denominator is total employment divided by
100 MW and the residential numerator is total employment divided by 1 MW.
Rutovitz inputs are already per MW. Each 2024 Colombian rooftop factor is the
selected dimensionless ratio times the corresponding Colombian utility factor.
Values below are rounded for display; the previous column is the all-US-JEDI
transfer, not the older frozen fallback.

| Phase | Category | Selected rooftop / utility ratio | Previous US-transfer default | Current Colombian rooftop default |
| --- | --- | ---: | ---: | ---: |
| Construction&Manufacturing | Direct | 2.602484 | 32.644879 | 25.946048 |
| Construction&Manufacturing | Indirect | 5.565874 | 35.420852 | 35.420852 |
| Construction&Manufacturing | Induced | 5.264293 | 33.513271 | 33.513271 |
| O&M | Direct | 1.444444 | 0.154656 | 0.139372 |
| O&M | Indirect | 1.687663 | 0.111976 | 0.111976 |
| O&M | Induced | 1.647584 | 0.082084 | 0.082084 |

Construction&Manufacturing units are FTE-years/MW; O&M units are annual FTE/MW.
Relative to the previous US-ratio transfer, direct construction/manufacturing
falls 20.52% and direct O&M falls 9.88%. This is a methodology change, not an
observed change in labour demand. The central case has no additional productivity
transfer; the optional 3.125 sensitivity applies only to eligible non-PV labour
components. Both model choices use these same rooftop factors.

Rooftop construction subsequently follows residential catalogue CAPEX ratios;
O&M follows residential OPEX ratios. For example, the direct factors are:

| Year | Construction&Manufacturing, FTE-years/MW | O&M, annual FTE/MW |
| --- | ---: | ---: |
| 2024 | 25.946048 | 0.139372 |
| 2030 | 17.896932 | 0.119696 |
| 2050 | 12.017741 | 0.100840 |
| 2055 | 12.017741 | 0.100840 |

These are cost-scaled projections, not measured labour-productivity forecasts.
Existing interpolation and the post-2050 hold are retained. The low/high and
source-refresh scenarios are regenerated using the same six PV transfer ratios.


## References

The current data workflow uses employment factors, technology mappings, and
projection ratios derived from the following sources. Users should cite the
original data sources alongside this repository when using the outputs in reports
or model documentation.

Danish Energy Agency, Ministry of Mines and Energy, Mining and Energy Planning
Unit, & Emergente. (2025). *Colombian Technology Catalogue quantitative data*
[Data workbook].

Danish Energy Agency, Ministry of Mines and Energy, Mining and Energy Planning
Unit, & Emergente. (2025). *Colombian Technology Catalogue for power generation
and storage technologies 2025*.

National Laboratory of the Rockies. (n.d.). *International Jobs and Economic
Development Impacts (I-JEDI) model*. Retrieved July 13, 2026, from
https://www.nlr.gov/analysis/jedi/international

National Laboratory of the Rockies. (n.d.). *Jobs and Economic Development
Impact (JEDI) models*. Retrieved July 13, 2026, from
https://www.nlr.gov/analysis/jedi

QBIS. (2020). *Socio-economic impact study of offshore wind: Final technical
report*. Danish Shipping, Wind Denmark, and Danish Energy.

QBIS. (2023). *Employment impacts of 40 GW offshore wind in France by 2050:
Technical report*. Ministry of Foreign Affairs of Denmark.

Ramboll & Danish Energy Agency. (2023). *Job creation in a new industry:
Learnings from Denmark's offshore wind journey*.

Rutovitz, J., Dominish, E., & Downes, J. (2015). *Calculating global energy
sector jobs: 2015 methodology update*. Institute for Sustainable Futures,
University of Technology Sydney.

Rutovitz, J., Langdon, R., Briggs, C., Mey, F., Dominish, E., & Nagrath, K.
(2025). Updated employment factors and occupational shares for the energy
transition. *Renewable and Sustainable Energy Reviews, 212*, 115339.
https://doi.org/10.1016/j.rser.2025.115339
