# Solar PV factor update

The model-ready rooftop series now uses six matched US residential/utility ratios
anchored to I-JEDI Colombia utility PV. The official user-supplied US workbooks
are preserved unchanged: `data/raw/jedi-pv-model.xlsm` (1 MW DC residential
portfolio) and `data/raw/jedi-pv-model_utility_scale.xlsm` (one 100 MW DC utility
plant). Both use construction year 2024, dollar year 2010, and release PV05.20.21.

The utility denominator is its total employment **divided by 100 MW**; the
residential numerator is its total employment divided by 1 MW. The 2024
Colombian rooftop factor is their dimensionless ratio times the corresponding
Colombian utility factor. The following values are rounded for display; extraction
and transfer use the full saved precision.

| Phase | Category | US residential / utility per-MW ratio | Previous rooftop default | New Colombian rooftop default |
| --- | --- | ---: | ---: | ---: |
| Construction&Manufacturing | Direct | 3.274402 | 9.328000 | 32.644879 |
| Construction&Manufacturing | Indirect | 5.565874 | 10.800000 | 35.420852 |
| Construction&Manufacturing | Induced | 5.264293 | 10.000000 | 33.513271 |
| O&M | Direct | 1.602847 | 0.300000 | 0.154656 |
| O&M | Indirect | 1.687663 | 0.105000 | 0.111976 |
| O&M | Induced | 1.647584 | 0.101000 | 0.082084 |

Construction&Manufacturing units are FTE-years/MW; O&M units are annual FTE/MW.
The previous rooftop values came from the frozen published fallback. The increase
in construction factors reflects a change from that series to a Colombia-anchored
relative transfer; it is not a measured increase in labour demand over time.
All non-rooftop model-default rows, including utility PV, are unchanged by this
update. No additional regional productivity multiplier is applied to these PV rows.

Rooftop construction subsequently follows residential catalogue CAPEX ratios;
O&M follows residential OPEX ratios. For example, the direct factors are:

| Year | Construction&Manufacturing, FTE-years/MW | O&M, annual FTE/MW |
| --- | ---: | ---: |
| 2024 | 32.644879 | 0.154656 |
| 2030 | 22.517617 | 0.132822 |
| 2050 | 15.120518 | 0.111898 |
| 2055 | 15.120518 | 0.111898 |

These are cost-scaled projections, not measured labour-productivity forecasts.
Existing interpolation and the post-2050 hold are retained. The low/high and
source-refresh scenarios are regenerated using the same six PV transfer ratios.

## Consumption and evidence

Use `get_model_employment_factors()` for the selected annual 2024-2055 defaults,
filtering `Technology == "Rooftop solar PV"` or `"Utility-scale solar PV"`.
The more general source-table API retains multiple sources and should not be
summed across sources. Construction factors multiply new capacity to give total
job-years; O&M factors multiply operating capacity to give annual FTE. Allocate
construction job-years across construction years if annual jobs are required.
Do not add the combined phase to separate construction/manufacturing phases.

Processed and packaged CSVs are identical. A model with a separately installed
copy or pinned dependency must update that copy/revision before seeing the new
data; this task changes this repository, not an external consumer installation.

- [Methodology and regeneration](METHODOLOGY_UPDATES.md) documents source-boundary
  approximations, the capacity-basis transfer assumption and dollar-year limitations.
- `data/audit/jedi_source_manifest.json` records source hashes, input settings,
  formula references and saved numeric caches.
- `data/processed/employment_factor_provenance.json` records all six ratios and
  anchors, output checksums, and `solar_transfer_ready: true`.
- [Productivity evidence](PRODUCTIVITY_EVIDENCE.md) explains why 0.32 remains a
  study assumption and why it is not applied again to Colombian solar factors.

Validation: 44 tests passed; the strict `--require-solar-ratios` rebuild reproduced
all four CSV artifacts byte-for-byte. Native workbook caches were checked for
capacity/result consistency; no claim of full Excel recalculation is made.
