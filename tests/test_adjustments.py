from pathlib import Path

import pandas as pd
import pytest

from colombia_employment_factors.adjustments import (
    LEGACY_ROOFTOP_SOURCE, PRODUCTIVITY_SUFFIX, ROOFTOP_SOURCE,
    apply_productivity_adjustments, derive_rooftop, load_policy,
    retain_published_rooftop, validate_factors,
)
from colombia_employment_factors.jedi import extract_jedi_sources, extract_us_jedi, refresh_curated_sources, sha256
from colombia_employment_factors.projections import project_employment_factors
from colombia_employment_factors.yearly import build_yearly_employment_factors

ROOT = Path(__file__).resolve().parents[1]


def policy():
    return load_policy(ROOT / "data/assumptions/employment_methodology.json")


def test_original_workbook_caches_and_capacity_normalisation():
    frame, manifest = extract_jedi_sources(ROOT, policy())
    assert manifest["us_residential"]["capacity_mw"] == 1
    assert manifest["us_residential"]["settings"]["B19"] == 200
    assert manifest["us_residential"]["settings"]["B24"] == 2010
    roof = frame[(frame.Source == "JEDI-US") & (frame.Factor_Type == "Construction&Manufacturing") & (frame.Job_Type == "Direct") & (frame.Technology == "Rooftop solar PV")]
    assert roof.Value_Numeric.iloc[0] == pytest.approx(10.742973760097033)
    anchor = frame[(frame.Source == "I-JEDI") & (frame.Technology == "Utility-scale solar PV") & (frame.Factor_Type == "O&M") & (frame.Job_Type == "Direct")]
    assert anchor.Value_Numeric.iloc[0] == pytest.approx(96.48835409544742 / 1000)
    utility = manifest["us_utility"]
    assert utility["capacity_mw"] == 100
    assert utility["settings"]["B18"] == 100000
    assert utility["settings"]["B19"] == 1
    assert utility["settings"]["B24"] == 2010
    for result in utility["results"]:
        assert result["factor_per_mw"] == pytest.approx(result["cached_jobs"] / 100)
    # Prevent dividing by total jobs (or by MW twice) when capacities differ.
    _, ratios = derive_rooftop(frame)
    for result, roof_result, ratio in zip(utility["results"], manifest["us_residential"]["results"], ratios):
        expected_ratio = roof_result["cached_jobs"] / (result["cached_jobs"] / 100)
        assert ratio["ratio"] == pytest.approx(expected_ratio)
        assert ratio["colombia_rooftop"] == pytest.approx(expected_ratio * ratio["colombia_utility_anchor"])


def test_utility_capacity_must_match_approved_policy():
    with pytest.raises(ValueError, match="approved 1 MW"):
        extract_us_jedi(ROOT / policy()["jedi_workbooks"]["us_utility"], ROOT, "Utility", expected_capacity_mw=1)


def test_missing_utility_still_has_documented_fallback():
    p = policy()
    p["jedi_workbooks"]["us_utility"] = "data/raw/nonexistent-test-utility.xlsm"
    frame, manifest = extract_jedi_sources(ROOT, p)
    assert "settings" not in manifest["us_utility"]
    assert not ((frame.Source == "JEDI-US") & (frame.Technology == "Utility-scale solar PV")).any()


def test_curated_source_refresh_preserves_unrelated_rows_and_is_idempotent():
    source = pd.read_csv(ROOT / "data/raw/employment_factors_input.csv")
    extracted, _ = extract_jedi_sources(ROOT, policy())
    updated = refresh_curated_sources(source, extracted)
    pd.testing.assert_frame_equal(updated, refresh_curated_sources(updated, extracted))
    pd.testing.assert_frame_equal(source[source.Source == "Rutovitz 2015"], updated[updated.Source == "Rutovitz 2015"])


def solar_fixture():
    rows = []
    for phase, roof, util, anchor in [("Construction&Manufacturing", 12, 4, 10), ("O&M", .3, .2, .1)]:
        for i, category in enumerate(["Direct", "Indirect", "Induced"], 1):
            for source, technology, value in [("JEDI-US", "Rooftop solar PV", roof*i), ("JEDI-US", "Utility-scale solar PV", util), ("I-JEDI", "Utility-scale solar PV", anchor)]:
                rows.append(dict(Source=source, Technology=technology, Factor_Type=phase, Job_Type=category,
                    Unit="job/MW" if phase == "O&M" else "job-yr/MW", Year=2024, Value=value, Value_Numeric=value))
    return pd.DataFrame(rows)


def test_six_independent_ratios_and_colombian_anchor():
    output, audit = derive_rooftop(solar_fixture())
    derived = output[output.Source == ROOFTOP_SOURCE]
    assert len(audit) == len(derived) == 6
    assert list(derived.Value_Numeric) == pytest.approx([30, 60, 90, .15, .30, .45])
    with pytest.raises(ValueError, match="already applied"):
        derive_rooftop(output)


@pytest.mark.parametrize("failure", ["missing", "zero", "duplicate", "units", "nan"])
def test_transfer_rejects_unsupported_inputs(failure):
    source = solar_fixture()
    if failure == "missing":
        source = source.drop(index=1)
    elif failure == "zero":
        source.loc[1, "Value_Numeric"] = 0
    elif failure == "duplicate":
        source = pd.concat([source, source.iloc[[1]]], ignore_index=True)
    elif failure == "units":
        source.loc[1, "Unit"] = "job-yr/GW"
    else:
        source.loc[1, "Value_Numeric"] = float("nan")
    with pytest.raises(ValueError):
        derive_rooftop(source)


def test_productivity_does_not_scale_manufacturing_or_already_latam_om():
    p = policy()
    p["productivity_eligibility"] = [r for r in p["productivity_eligibility"] if r["technology"] == "Hydro (large)"]
    rows = []
    for phase, value, unit in [("Construction", 8, "job-yr/MW"), ("Manufacturing", 4, "job-yr/MW"), ("Construction&Manufacturing", 12, "job-yr/MW"), ("O&M", .6, "job/MW")]:
        rows.append(dict(Source="Rutovitz 2015", Technology="Hydro (large)", Factor_Type=phase, Job_Type="Direct", Unit=unit, Year=2024, Value=value, Value_Numeric=value, Projected_Value=value, Method_Applied="fixture", Projection_Input=""))
    original = pd.DataFrame(rows)
    output, _ = apply_productivity_adjustments(original, p, "central")
    adjusted = output[output.Source.str.endswith(PRODUCTIVITY_SUFFIX)].set_index("Factor_Type")
    assert adjusted.loc["Construction", "Value_Numeric"] == 25
    assert adjusted.loc["Manufacturing", "Value_Numeric"] == 4
    assert adjusted.loc["Construction&Manufacturing", "Value_Numeric"] == 29
    assert adjusted.loc["O&M", "Value_Numeric"] == .6
    pd.testing.assert_frame_equal(output.iloc[:len(original)].reset_index(drop=True), original, check_dtype=False)
    with pytest.raises(ValueError, match="already applied"):
        apply_productivity_adjustments(output, p, "central")
    low, _ = apply_productivity_adjustments(original, p, "low")
    high, _ = apply_productivity_adjustments(original, p, "high")
    assert low.Value_Numeric.iloc[4] < output.Value_Numeric.iloc[4] < high.Value_Numeric.iloc[4]


def test_frozen_baseline_and_complete_rooftop_fallback():
    p = policy()
    path = ROOT / p["published_baseline"]
    assert sha256(path) == p["published_baseline_sha256"]
    baseline = pd.read_csv(path)
    output = retain_published_rooftop(baseline.iloc[:0], baseline)
    assert set(output.Source) == {LEGACY_ROOFTOP_SOURCE}
    assert len(output) == 192
    assert output.Value_Numeric.tolist() == baseline.loc[baseline.Technology == "Rooftop solar PV", "Value_Numeric"].tolist()
    with pytest.raises(ValueError, match="Incomplete"):
        retain_published_rooftop(baseline.iloc[:0], baseline.iloc[:0])


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
def test_factor_validation_rejects_invalid_numbers(value):
    source = solar_fixture()
    source.loc[0, "Value_Numeric"] = value
    with pytest.raises(ValueError, match="finite"):
        validate_factors(source)


def test_model_validation_rejects_duplicate_source_variants():
    source = solar_fixture()
    with pytest.raises(ValueError):
        validate_factors(source, model=True)


def test_rooftop_anchor_is_reproduced_then_uses_its_own_temporal_mapping():
    source, _ = derive_rooftop(solar_fixture())
    ratios = pd.DataFrame([
        dict(technology_name=name, capex_ratio_2030_over_2024=capex, capex_ratio_2050_over_2030=1,
             opex_ratio_2030_over_2024=opex, opex_ratio_2050_over_2030=1)
        for name, capex, opex in [("Utility scale PV(tracking)", .5, .9), ("Residential PV (rooftop)", .8, 1.1)]
    ])
    yearly = build_yearly_employment_factors(project_employment_factors(source, ratios))
    roof = yearly[(yearly.Source == ROOFTOP_SOURCE) & (yearly.Factor_Type == "Construction&Manufacturing") & (yearly.Job_Type == "Direct")].set_index("Year")
    assert roof.loc[2024, "Value_Numeric"] == 30
    assert roof.loc[2030, "Value_Numeric"] == pytest.approx(24)
    assert roof.loc[2055, "Value_Numeric"] == pytest.approx(24)
    # Relative ratios are not forced constant after independently justified mappings.
    utility = yearly[(yearly.Source == "I-JEDI") & (yearly.Factor_Type == "Construction&Manufacturing") & (yearly.Job_Type == "Direct")].set_index("Year")
    assert roof.loc[2030, "Value_Numeric"] / utility.loc[2030, "Value_Numeric"] == pytest.approx(4.8)


def test_duplicate_source_year_is_not_silently_interpolated_away():
    frame = solar_fixture()
    with pytest.raises(ValueError, match="Duplicate source/year"):
        build_yearly_employment_factors(pd.concat([frame, frame.iloc[[0]]], ignore_index=True))


def test_already_latam_policy_and_reversed_scenarios_are_rejected(tmp_path):
    import json
    p = policy()
    p["productivity_eligibility"].append(dict(source="Rutovitz 2015", technology="Hydro (large)", phase="O&M", evidence="erroneous duplicate regional adjustment"))
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="Already-LATAM"):
        load_policy(path)
    p = policy()
    p["productivity_ratios"]["low"] = .25
    path.write_text(json.dumps(p))
    with pytest.raises(ValueError, match="inverse ordering"):
        load_policy(path)


def test_fractional_source_year_is_not_accepted():
    source = solar_fixture()
    source["Year"] = 2024.5
    with pytest.raises(ValueError, match="finite integers"):
        validate_factors(source)
