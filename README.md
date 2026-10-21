# Colombia Employment Factors

Model-agnostic employment factors and technology assumptions for Colombia's power
sector, with annual factors through 2055. The package supports ex-post analysis;
model-specific mappings and capacity conversions belong in downstream workflows.

## Install and use

```sh
pip install .
# Maintainer environment (no separate requirements.txt):
pip install -e ".[build,dev]"
```

```python
from colombia_employment_factors import (
    get_model_employment_factors,
    get_technology_assumption,
)

factors = get_model_employment_factors()
# Optional sensitivity: selective LATAM productivity transfer (1 / 0.32).
latam_factors = get_model_employment_factors(productivity_transfer=True)
solar = factors[
    (factors["Technology"] == "Utility-scale solar PV")
    & (factors["Year"] == 2030)
    & (factors["Factor_Type"] == "Construction&Manufacturing")
    & (factors["Job_Type"] == "Direct")
]
assumption = get_technology_assumption("Utility-scale solar PV")
```

Productivity transfer is **off by default**. This changes the previous model
default; pass `productivity_transfer=True` to select the optional 3.125 adjustment.
Both tables are bundled with the installed package, so consumers need no checkout
or rebuild. The default retains source-specific regional factors, solar transfers,
and temporal projections; it omits the additional LATAM productivity multiplier.

Both model tables use **Rutovitz 2025 direct rooftop ratios**: construction
4.19/1.61 (about 2.602) and O&M 0.13/0.09 (about 1.444), applied to the Colombian
I-JEDI utility anchors. The construction-only ratio is a documented proxy for
the combined direct construction/manufacturing phase. Indirect and induced
rooftop factors retain US-JEDI ratios. See the [methodology](docs/methodology.md#rooftop-transfer-rutovitz-direct-ratios-and-us-jedi-wider-impacts)
for boundaries and numerical results. No total-manufacturing ratio option is provided.

Public interfaces:

- `get_model_employment_factors(path=None, *, productivity_transfer=False)`:
  annual selected defaults; `True` selects the optional LATAM-adjusted table.
  An explicit `path` takes precedence and loads that CSV as-is, regardless of the flag.
- `get_yearly_employment_factors(path=None)`: annual alternative sources and variants.
- `get_employment_factors(path=None)`: sparse source observations and projections,
  including fuel factors; this is not the annual model-default table.
- `get_technology_assumptions(path=None)` and
  `get_technology_assumption(technology, path=None)`.
- `project_employment_factors(employment_factors, capex_opex_ratios=None)`.
- `DEFAULT_SOURCE_BY_TECHNOLOGY`: resolved packaged source choices.

`DEFAULT_SOURCE_BY_TECHNOLOGY` describes the unadjusted default. Use the returned
table's `Source` column for the selected variant. The all-source yearly API still
includes labelled adjusted alternatives; it is not the selected model-default table.

The projection function alone does not run the complete methodology. Supply
catalogue ratios explicitly when using it independently; omission retains its
existing constant-ratio behavior.

## Units and model integration

Construction factors in `job-yr/MW` multiply **new capacity in MW** to give total
job-years. O&M factors in `job/MW` multiply **operating capacity in MW** to give
annual jobs. Construction-time assumptions support allocation of job-years over
construction periods. Do not sum combined construction/manufacturing with its
separate components or sum alternative source series.

Transmission includes factors per km, mile, and million USD. Preserve these
units and use matching activity data; they are not factors per MW. Direct,
Indirect, and Induced remain separate categories.

`colombia_employment_factors.adapters.osemosys.calculate_capacity_jobs` is a thin
join/multiplication adapter. Select the appropriate factor type and job type,
provide a technology mapping, and convert model activity units before calling it.
It does not infer new versus operating capacity, convert units, or allocate jobs
over construction years. OSeMOSYS PR #174's exact consumer contracts were not
accessible during refactoring; the Python API and existing CSV columns remain.

## Rebuild

```sh
python scripts/build_employment_factors.py --require-solar-ratios
```

This offline command reads manual inputs, saved JEDI caches, catalogue row
selections, and methodology policy; it writes the five canonical CSVs (including
both model choices) and
`employment_factor_provenance.json` directly to
`src/colombia_employment_factors/data/`. It also regenerates the catalogue ratio
audit CSV. Source workbooks are never recalculated or modified. The strict flag
requires the matched utility PV run; without it the documented frozen rooftop
fallback remains available.

```sh
# Isolated central export, including an optional three-sheet review workbook:
python scripts/build_employment_factors.py --require-solar-ratios --output-dir output/review --audit-workbook
# Scenario publication: model-default CSV and provenance only:
python scripts/build_employment_factors.py --productivity-transfer selective --scenario low
python scripts/build_employment_factors.py --productivity-transfer selective --scenario high
python scripts/build_employment_factors.py --productivity-transfer selective
# Former US-JEDI direct ratios, exported separately for comparison:
python scripts/build_employment_factors.py --solar-ratio-method us-jedi --require-solar-ratios
# Full tables for research or consumers of earlier scenario exports:
python scripts/build_employment_factors.py --productivity-transfer selective --scenario low --all-tables --output-dir output/low-review
```

The default build uses `--productivity-transfer none` and bundles the optional
central adjusted table alongside the default. Explicit `selective` builds export
to `data/processed/scenarios/<scenario>-catalogue-selective/` by default.
The `source-refresh/` export is refreshed to match the current no-transfer
model-default CSV; consumers can use the packaged default instead.

Scenario directories are isolated. `--all-tables` includes sparse, annual
all-source, and assumption tables; `--audit-workbook` produces values-only
`Model_Default_2024_2055`, `Technology_Assumptions`, and `Methods_Provenance`
sheets. Change authoritative inputs and rebuild to change results. The workbook
is not an independent calculation model. Use a fresh export directory when
switching export options; the builder does not delete previous exports.

`python scripts/audit_productivity.py` separately reproduces evidence from the
frozen WDI snapshot. Only its explicit `--fetch` option accesses the network.
Neither operation changes the adopted productivity policy.

## Data contracts and ownership

| Location | Role |
| --- | --- |
| `data/raw/*.xlsm`, `docs/sources/` | Preserved source workbooks and publications |
| `data/curated/employment_factors_input.csv` | Manual factors, original reported values, and source notes |
| `data/curated/catalogue_rows.csv` | Approved catalogue cell selections; no copied cost values |
| `data/assumptions/employment_methodology.json` | Productivity eligibility, scenarios, workbook settings, fallback policy |
| `src/colombia_employment_factors/data/` | Sole central dataset publication and provenance |
| `data/processed/scenarios/` | Selected annual scenario outputs and provenance |
| `data/audit/` | Generated catalogue ratios, frozen baseline, WDI snapshot and evidence |
| `docs/archive/` | Historical presentation and chart workbook, not current calculations |

The central files retain their existing names and schemas:

| File | Coverage and purpose |
| --- | --- |
| `employment_factors_with_2030_2050.csv` | Historical 2015/2022/2024 observations and sparse 2030/2050 projections |
| `employment_factors_yearly_2024_2055.csv` | Annual factors by source, technology, factor type, job type, and unit |
| `employment_factors_model_default_2024_2055.csv` | Annual selected defaults for 21 technologies, without additional productivity transfer |
| `employment_factors_model_latam_productivity_2024_2055.csv` | Optional selective LATAM productivity transfer, ratio 0.32 |
| `technology_assumptions_2024.csv` | Lifetimes and construction times with individual source years and exceptions |

Factor keys are `Source`, `Technology`, `Factor_Type`, `Job_Type`, `Unit`, and
`Year`; the calculation value is `Value_Numeric`. Original sparse `Value` can
retain a source-reported quantity before normalization (notably QBIS FTE/GW).
Legacy columns remain for compatibility. Values after 2050 are held constant
through 2055. Unknown lifetimes/construction times remain missing.

**Path migration:** former central `data/processed/<filename>` files now live
only in package `data/`; prefer the retrieval API or request an explicit export.
The former `data/raw/employment_factors_input.csv` is now the manual-only curated
CSV. The separate JEDI manifest is embedded as `jedi_sources` in provenance.
Scenario source tables and workbooks can be regenerated with the options above.
The old extraction and presentation-generation scripts have been retired.

Provenance records input hashes, output checksums, Git revision/dirty state,
resolved source choices, solar transfer evidence, and scenario settings. A
scenario's input hashes identify the shared sources needed to regenerate its
omitted intermediate tables. Git metadata may differ across builds; numeric
CSV results must reproduce from the same input content.
Central provenance describes the unadjusted default at the top level and the
optional adjusted table under `optional_productivity_model`, with checksums for both.

See [methodology and references](docs/methodology.md) for scientific assumptions,
source-selection rules and exceptions, and [productivity evidence](docs/PRODUCTIVITY_EVIDENCE.md)
for the distinction between the optional 0.32 assumption and empirical diagnostics.
