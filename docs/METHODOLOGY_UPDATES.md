# Auditable employment-factor updates

Original JEDI workbooks are preserved in `data/raw`. No build executes VBA,
updates external links or asks openpyxl to recalculate formulas. Saved numeric
caches, source formulas (including array formulas), settings, named ranges,
hidden sheets, external-link inventory and SHA-256 hashes are recorded in
`data/audit/jedi_source_manifest.json`. Capacity and output-total identities
are checked, but this is not proof of full Excel recalculation. If a cache is
missing/inconsistent, recalculate a preserved working copy in the intended Excel
version under an approved procedure, save it, and review the new settings/hash.

## Regeneration

Use the project's configured Python interpreter with the existing dependencies:

```sh
python scripts/extract_jedi_factors.py --write
python scripts/extract_jedi_factors.py
python scripts/audit_productivity.py
python scripts/build_employment_factors.py --require-solar-ratios
python -m pytest -q
```

The extraction script updates only the curated JEDI source rows and verified
provenance notes in `data/raw/employment_factors_input.csv`. Native workbooks
are never overwritten. `Value` and `Value_Numeric` are consistent numeric source
values after extraction. Historically rooftop `Value=9328` conflicted with
`Value_Numeric=9.328`; Python already consumed the latter. The new saved US run
gives 10.742973760097033 direct construction-period FTE-years/MW, representing
200 five-kW systems. That source refresh is distinct from correcting the old
displayed scaling error. US monetary values remain 2010 dollars; construction
year is 2024. I-JEDI uses 2024 money and 1,000 MW, normalised once to per MW. The 2024 factor anchor is a modelling convention: changing the currency year does not make all underlying technical and economic coefficients 2024 observations.

## Rooftop transfer from the supplied saved runs

Policy lives in `data/assumptions/employment_methodology.json`. The authoritative
US inputs are `data/raw/jedi-pv-model.xlsm` (200 five-kW residential systems,
1 MW DC total, fixed mount) and `data/raw/jedi-pv-model_utility_scale.xlsm`
(one 100-MW DC utility system, single-axis tracking). Both are release
PV05.20.21, United States, construction year 2024 and dollar year 2010. Each
saved result is divided once by its own total MW before forming the ratios.
Approved capacities are explicit in policy; unexpected capacities or inconsistent
saved input/summary totals fail validation. The utility run is now available.

Derive for each employment phase p
(Construction&Manufacturing or O&M) and category b (Direct, Indirect, Induced):

```
R[p,b,2024] = US_residential[p,b,2024] / US_utility[p,b,2024]
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

The selected LATAM/OECD non-agricultural productivity ratio 0.32 is a
user-approved high-level modelling assumption. The source audit in
`docs/PRODUCTIVITY_EVIDENCE.md` verifies Rutovitz's published-table arithmetic
and the OECD per-hour comparison, but does not reproduce 0.32. Archived 2023 WDI
aggregates yield 0.369767 for the whole economy and an approximate non-agricultural
ratio of 0.384924. These are diagnostics, not adopted replacements. Compute the
adopted inverse as 3.125; display approximately 3.1.
World Bank SL.GDP.PCAP.EM.KD is GDP per person employed in constant 2021 PPP
dollars. OECD productivity per hour is a plausibility check, not the same series.
LAC excluding high-income economies is a proxy for the intended LATAM region,
not a Colombia observation or a technology-specific productivity measurement.

The JSON eligibility table is explicit by source, technology and phase. Apply
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
python scripts/build_employment_factors.py --scenario low
python scripts/build_employment_factors.py --scenario high
python scripts/build_employment_factors.py --productivity-transfer none --output-dir data/processed/scenarios/source-refresh
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

Public factor retrieval APIs and required CSV columns are unchanged. Base-source
selectors remain in mappings.py; the builder resolves policy-specific sources.
The generated audit workbook's Default_Source_Mapping and the model CSV show
the actual selected sources. Source-year sparse tables remain unadjusted temporal
series; the all-source YEARLY table includes adjusted variants. Separate scenarios
must not be combined before interpolation or default selection.

Processed CSVs and packaged CSVs are byte-identical, with LF newlines.
`employment_factor_provenance.json` records repository revision, dirty state,
input/content hashes, output checksums, scenario and solar readiness. The source
revision identifies the committed inputs and generator at build time. The dirty
flag can include generated outputs awaiting their separate artifact commit; it
must not be interpreted as proof that input/code changes are uncommitted.
The consumer dependency pins the artifact commit containing the generated data.
No manifest attempts to contain the SHA of its own enclosing commit. Generated workbook
formulas require Excel recalculation; Python CSV calculations and tests are
authoritative, and no workbook formula-cache verification is claimed.

The baseline snapshot and Git preserve rollback evidence. Restore a prior
approved source revision/assumptions, regenerate, compare its checksums, and
resynchronise the consumer snapshot. Do not reset branches or overwrite native
source workbooks. No commit, push or PR publication is performed by these scripts.

Sources: NLR JEDI results https://www.nlr.gov/analysis/jedi/results ; PV release
https://www.nlr.gov/analysis/jedi/pv ; I-JEDI
https://www.nlr.gov/analysis/jedi/international ; World Bank indicator
https://data.worldbank.org/indicator/SL.GDP.PCAP.EM.KD ; local Rutovitz 2015
methodology report, Tables 1, 2, 6 and 8, pp.5, 8, 15 and 17.
