# Colombia Employment Factors

Model-agnostic employment factors and learning-curve methodology for Colombia's
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
- applying technology-learning multipliers to construction and manufacturing
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

For Rutovitz 2015 construction and manufacturing rows, the package applies the
Latin America 2030 decline factors from Rutovitz Table 9.

For 2024-source construction, manufacturing, and combined
construction-and-manufacturing rows, the package applies the learning-curve
relationship:

```text
projected_factor = base_factor * capacity_ratio ** log2(1 - learning_rate)
```

This is equivalent to the spreadsheet form:

```text
projected_factor = base_factor * capacity_ratio ^ (LN(1 - learning_rate) / LN(2))
```

Where catalogue learning-rate inputs are unavailable, documented CAPEX-ratio
fallbacks are used and flagged in the output metadata.

## Repository Layout

```text
src/colombia_employment_factors/   installable Python package
scripts/                           maintainer scripts for rebuilding outputs
data/raw/                          source employment-factor tables
data/processed/                    generated model-ready employment factors
data/audit/                        Excel audit workbooks
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
