# Colombia Employment Factors

Model-agnostic employment factors and CAPEX/OPEX ratio methodology for Colombia's
power sector.

This repository packages employment-factor data and projection methods so they
can be reused by capacity-expansion models such as OSeMOSYS, TIMES-MARKAL, LEAP,
or other energy-system tools. The main use case is ex-post jobs analysis:
capacity results from an energy model are multiplied by technology-specific
employment factors by year, factor type, and job type.

## Purpose

The repository keeps labour-impact assumptions outside the core optimization
model. This makes the employment methodology versioned, auditable, and reusable
without coupling it to one OSeMOSYS implementation or one model-data workflow.

The package supports:

- reading curated employment-factor tables;
- applying Rutovitz Table 9 and CAPEX/OPEX ratio multipliers to eligible
  employment factors;
- documenting mappings between employment-factor technologies, Rutovitz Table 9
  decline factors, and the Colombian Technology Catalogue;
- providing adapters for model-specific result formats such as OSeMOSYS.

## Installation

For local development:

```bash
pip install -e .
```

For use from another repository, such as `Osemosys_UPME`, install directly from
GitHub once the repository is published:

```bash
pip install git+https://github.com/<org>/colombia-employment-factors.git
```

The runtime dependencies are also listed in `requirements.txt`.

## Basic Usage

```python
from colombia_employment_factors import get_employment_factors, get_model_employment_factors

factors = get_employment_factors()
solar_2030 = factors[
    (factors["Technology"] == "Solar PV")
    & (factors["Year"] == 2030)
]

model_factors = get_model_employment_factors()
```

For OSeMOSYS-style post-processing:

```python
from colombia_employment_factors import get_employment_factors
from colombia_employment_factors.adapters.osemosys import calculate_capacity_jobs

factors = get_employment_factors()
jobs = calculate_capacity_jobs(osemosys_capacity_results, factors)
```

## Method Summary

For Rutovitz 2015 construction, manufacturing, and O&M rows, the package applies
the Latin America 2030 decline factors from Rutovitz Table 9, excluding fuel rows
and treating dashes in Table 9 as a 0% decline factor. The applied formula is:

```text
EF_2030 = EF_2015 * (1 - decline_factor_2030)
```

The audit workbook mirrors this in `Mappings_Rutovitz` and uses formulas in
`Employment_Outputs` for the corresponding Rutovitz 2015 rows projected to 2030.
Coal and nuclear use a 1.00 multiplier because Table 9 has a dash for the Latin
America decline factor.

For non-Rutovitz-2015 rows with a 2024 base year, the package applies CAPEX/OPEX
transition ratios from `data/audit/capex_opex_ratios_2024_2030_2050.csv`.
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

The audit file
`data/audit/capex_opex_ratios_2024_2030_2050.csv` records the CAPEX and fixed
O&M values extracted from `docs/sources/datos_cuantitativos_EN.xlsx` for each
technology sheet, excluding `Guide&Cover` and `Index`. It includes the selected
source row labels and row numbers, a normalized technology name without sheet
numbering, the 2024, 2030, and 2050 values, and the transition ratios
`2030/2024` and `2050/2030`. This table is the catalogue-ratio input used for
the 2030 and 2050 employment-factor projection method.

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
`data/processed/employment_factors_yearly_2024_2055.csv`. It includes eligible
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
`data/processed/employment_factors_model_default_2024_2055.csv` filters the
yearly all-source table to one default source per technology. This is the table
intended for direct retrieval by model workflows such as OSeMOSYS post-processing.

Default source choices are defined in
`colombia_employment_factors.mappings.DEFAULT_SOURCE_BY_TECHNOLOGY`:

- QBIS 2023 for fixed and floating offshore wind.
- Rutovitz 2025 for storage technologies and available transmission rows.
- I-JEDI for direct, indirect, and induced renewable rows for biomass,
  geothermal, onshore wind, and utility-scale solar PV.
- JEDI-US for rooftop solar PV.
- Rutovitz 2015 for the remaining technologies.

`Transmission (single circuit)` falls back to JEDI-US because the raw table does
not include a Rutovitz 2025 factor for that specific technology.

## Repository Layout

```text
src/colombia_employment_factors/   installable Python package
scripts/                           maintainer scripts for rebuilding outputs
data/raw/employment_factors_input.csv
                                   curated source employment-factor inputs
data/processed/                    generated model-ready employment factors
data/audit/                        audit workbooks and derived ratio tables
docs/sources/                      source PDFs and catalogue spreadsheets
tests/                             unit tests for formulas and adapters
```

## Sources

The current data workflow uses employment factors and mappings derived from:

- Rutovitz et al. 2015, including Table 9 regional decline factors;
- Colombian Technology Catalogue inputs;
- JEDI/I-JEDI and updated Rutovitz employment-factor rows where available.

Users should cite the original data sources alongside this repository when using
the outputs in reports or model documentation.
