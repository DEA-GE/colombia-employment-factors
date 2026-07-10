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
from colombia_employment_factors import get_employment_factors

factors = get_employment_factors()
solar_2030 = factors[
    (factors["Technology"] == "Solar PV")
    & (factors["Year"] == 2030)
]
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
use CAPEX ratios; O&M factors use OPEX ratios. The projection is sequential:

```text
EF_2030 = EF_2024 * ratio_2030_2024
EF_2050 = EF_2030 * ratio_2050_2030
```

For Rutovitz 2015 rows already projected to 2030, the package applies the same
CAPEX/OPEX `2050/2030` transition from the 2030 value:

```text
EF_2050 = EF_2030 * ratio_2050_2030
```

Technologies without a matching catalogue ratio row, such as transmission,
solar thermal (CSP), and ocean, are projected as constant values. Offshore wind
(floating) has no 2024 ratio in the catalogue table, so its 2030 value is held
constant from 2024 and its 2050 value uses the available `2050/2030` ratio.

The audit file
`data/audit/capex_opex_ratios_2024_2030_2050.csv` records the CAPEX and fixed
O&M values extracted from `docs/sources/datos_cuantitativos_EN.xlsx` for each
technology sheet, excluding `Guide&Cover` and `Index`. It includes the selected
source row labels and row numbers, a normalized technology name without sheet
numbering, the 2024, 2030, and 2050 values, and the transition ratios
`2030/2024` and `2050/2030`. This table is the catalogue-ratio input used for
the 2030 and 2050 employment-factor projection method.

## Repository Layout

```text
src/colombia_employment_factors/   installable Python package
scripts/                           maintainer scripts for rebuilding outputs
data/raw/                          source employment-factor tables
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
