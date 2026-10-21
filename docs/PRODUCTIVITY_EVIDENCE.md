# Productivity evidence and the retained study assumption

The package now defaults to **no additional productivity transfer**. The ratios
below remain optional sensitivity assumptions, selected with
`get_model_employment_factors(productivity_transfer=True)` for the central case.
This audit documents the evidence for that optional transfer.

The study retains an optional central ratio of **0.32**, inverse **3.125**, and low/central/high
employment-intensity ratios **0.33/0.32/0.30**. These are explicit user-approved
screening assumptions, not confidence limits or reproduced 2023 observations.
The supplied chat establishes the intended rationale, but its numerical derivation
does not follow from the primary-source observations retrieved for this audit.
The policy still excludes I-JEDI Colombia and its derived rooftop PV factors.

## What was verified

| Comparison | Ratio | Inverse | Interpretation |
| --- | ---: | ---: | --- |
| Rutovitz Table 8, 2012 non-agricultural published levels | 55,200 / 187,600 = 0.294243 | 3.398551 | Consistent with displayed 0.29 and Table 6's 2015 multiplier 3.4 |
| OECD LEO 2024, 2023 productivity per hour | 0.33 | Not used | Different measure and country averaging; plausibility comparison only |
| WDI 2023, whole-economy GDP per worker, LAC/OED | 0.369767 | 2.704408 | Reproduced from the archived current-release aggregates |
| WDI 2023, approximate non-agricultural aggregate diagnostic | 0.384924 | 2.597917 | Reproducible approximation, not an adopted replacement |
| Adopted study assumption | **0.32** | **3.125** | Retained by decision; not relabelled as an empirical estimate |

Rutovitz et al. (2015), printed pp.15-17, describes the regional proxy method.
Table 8 gives Latin America and OECD non-agricultural productivity of 55,200 and
187,600 in 2005 PPP international dollars per worker. Dividing those published
levels reproduces the rounded ratio and reciprocal. Inverting the already-rounded
0.29 instead gives 3.448276; this rounding difference is not an inconsistency.
This verifies published-table arithmetic, not the underlying KILM/IEA data or the
original agricultural correction. The regional coverage is also not established
as identical to today's WDI aggregates.

OECD LEO 2024, overview Figure 1, reports a 2023 per-hour ratio of 33%. Its LAC
comparison is a simple average of 16 economies: Argentina, Bolivia, Brazil, Chile,
Colombia, Costa Rica, Dominican Republic, Ecuador, Guatemala, Jamaica, Mexico,
Paraguay, Peru, Trinidad and Tobago, Uruguay, and Venezuela. Its OECD comparison
averages 38 members. The underlying source is The Conference Board (2024).
This does not establish a non-agricultural per-worker ratio, and it is not the
same population or weighting as LAC excluding high-income economies.
[Source: OECD overview, Figure 1](https://www.oecd.org/en/publications/latin-american-economic-outlook-2024_c437947f-en/full-report/overview_b80bea0f.html).

## Reproducible WDI diagnostic

The frozen API responses in `data/audit/productivity_wdi_2023.json` contain all six
observations below, URLs, retrieval time, WDI release metadata and response hashes.
All observations are for **2023**; the API release is **2026-10-08**. These revised
data cannot reconstruct the unknown data vintage used in the supplied chat.

| Input | LAC: Latin America & Caribbean excluding high income | OED: OECD members |
| --- | ---: | ---: |
| GDP per person employed, constant 2021 PPP dollars (`SL.GDP.PCAP.EM.KD`) | 40,959.822623 | 110,772.084912 |
| Agriculture, forestry and fishing value added, % GDP (`NV.AGR.TOTL.ZS`) | 7.052275 | 1.437156 |
| Agricultural employment, % total (`SL.AGR.EMPL.ZS`) | 13.463788 | 4.474510 |
| Agriculture-exclusion correction | 1.074091 | 1.031796 |
| Approximate non-agricultural productivity | 43,994.557389 | 114,294.223571 |

For each group, with shares expressed as fractions:

```text
P_nonag = P_all * (1 - agriculture_GDP_share) / (1 - agriculture_employment_share)
ratio = P_nonag_LAC / P_nonag_OED
```

This removes agriculture from both output and employment in both comparison
groups. We use the publisher's regional aggregates; underlying country membership,
missing-data coverage and weights are inherited from WDI, not independently
reconstructed. In particular, aggregate agriculture shares and PPP productivity
need not use identical coverage or valuation weights. Applying nominal sector
shares to PPP GDP is a proxy, not a sector-specific PPP estimate. Consequently
**0.384924 is a diagnostic**, not a harmonised country-level result. A replacement
policy would need explicit membership and consistent country-level aggregation.
The direction of the ratio's change after excluding agriculture depends on the
correction in both regions; it cannot be assumed in advance.

Run the audit offline from the saved observations:

```sh
python scripts/audit_productivity.py
```

The generated `data/audit/productivity_evidence.json` records the calculation,
historical table check, source hash, limitations and adopted policy. An intentional
data refresh uses `--fetch`; normal factor builds and tests require no network.
Neither audit mode changes the adopted ratios. The factor provenance includes
hashes of both evidence files and explicitly records the assumption status.

## Implications for this high-level study

The current WDI diagnostic does **not** substantiate the chat's claimed
0.30-0.33 per-worker range or its derivation of 0.32 after excluding agriculture.
Retaining 0.32 is a transparent study choice. Compared with the diagnostic inverse
of about 2.598, its multiplier 3.125 implies roughly 20% more employment in the
eligible components; this is a comparison of assumptions, not a measured bias.
Existing sensitivity settings are retained, including 0.33 rather than the chat's
later suggestion of 0.34. No causal power-sector productivity relationship is
established by these macroeconomic proxies.

PPP rebasing is not just inflation adjustment. The ICP 2021 release includes new
2021 results and revised 2017 results; it does not itself supply the claimed
non-agricultural ratio. Compare numerator and denominator within the same series
and vintage rather than comparing absolute 2005-PPP and 2021-PPP levels.
[Source: World Bank ICP data](https://www.worldbank.org/en/programs/icp/data).

## References

- Rutovitz, J., Dominish, E., & Downes, J. (2015). *Calculating global energy sector jobs: 2015 methodology update*. Institute for Sustainable Futures, University of Technology Sydney. [Preserved report](sources/Rutovitzetal2015Calculatingglobalenergysectorjobsmethodology.pdf), Tables 6 and 8, printed pp.15 and 17.
- OECD, CAF, & European Commission. (2024). *Latin American economic outlook 2024: Financing sustainable development*. OECD Publishing. https://doi.org/10.1787/c437947f-en
- World Bank. (n.d.). *GDP per person employed (constant 2021 PPP $)* [Data set, SL.GDP.PCAP.EM.KD]. World Development Indicators. https://data.worldbank.org/indicator/SL.GDP.PCAP.EM.KD
- World Bank. (n.d.). *Agriculture, forestry, and fishing, value added (% of GDP)* [Data set, NV.AGR.TOTL.ZS]. World Development Indicators. https://data.worldbank.org/indicator/NV.AGR.TOTL.ZS
- World Bank. (n.d.). *Employment in agriculture (% of total employment) (modeled ILO estimate)* [Data set, SL.AGR.EMPL.ZS; underlying ILO modelled estimates]. World Development Indicators. https://data.worldbank.org/indicator/SL.AGR.EMPL.ZS
- World Bank. (2024, May 30). *Global purchasing power parities data released for 2021*. https://www.worldbank.org/en/news/press-release/2024/05/30/global-purchasing-power-parities-data-released-for-2021

Exact API retrieval timestamps are preserved in the snapshot, rather than relying
on these live pages to retain the same observation values.
