"""Scientific boundaries and semantic classification of the PCH/SMR additions."""
from pathlib import Path

import pandas as pd
import pytest

from colombia_employment_factors import get_model_employment_factors, get_yearly_employment_factors, get_technology_assumption
from colombia_employment_factors.mappings import PCH_SOURCE, SMR_SOURCE
from colombia_employment_factors.projections import add_construction_manufacturing_rows

ROOT = Path(__file__).resolve().parents[1]


def test_reported_and_calibrated_source_observations_remain_separate():
    raw = pd.read_csv(ROOT / "data/curated/employment_factors_input.csv")
    for source, technology, expected in [
        ("Rutovitz 2015", "Hydro (small)", [15.8, 10.9, 4.9]),
        (PCH_SOURCE, "Hydro (small)", [7.36, 2.3, .8]),
        ("Rutovitz 2015", "Nuclear", [19.6, 1.3, 1.15]),
        (SMR_SOURCE, "SMR", [11.8, 1.3, .6]),
    ]:
        rows = raw[(raw.Source == source) & (raw.Technology == technology)].set_index("Factor_Type")
        assert rows.loc[["Construction", "Manufacturing", "O&M"], "Value_Numeric"].tolist() == pytest.approx(expected)


@pytest.mark.parametrize("productivity_transfer", [False, True])
def test_selected_pch_is_effective_calibration_without_second_productivity_adjustment(productivity_transfer):
    model = get_model_employment_factors(productivity_transfer=productivity_transfer)
    pch = model[model.Technology == "Hydro (small)"]
    assert set(pch.Source) == {PCH_SOURCE}
    assert set(pch.Year) == set(range(2024, 2056))
    base = pch[pch.Year == 2024].set_index("Factor_Type").Value_Numeric
    assert base["O&M"] == pytest.approx(.8)
    assert base["Construction&Manufacturing"] == pytest.approx(9.66)
    assert base["Construction&Manufacturing"] == pytest.approx(base.Construction + base.Manufacturing)
    # Retain catalogue OPEX scaling after the calibrated reference year.
    assert pch.loc[(pch.Year == 2055) & (pch.Factor_Type == "O&M"), "Value_Numeric"].item() == pytest.approx(.8 * 66000 / 66500)


def test_smr_is_distinct_constant_proxy_with_explicit_2030_timing():
    model = get_model_employment_factors()
    smr = model[model.Technology == "SMR"]
    assert set(smr.Source) == {SMR_SOURCE}
    for phase, value in [("Construction", 11.8), ("Manufacturing", 1.3), ("Construction&Manufacturing", 13.1), ("O&M", .6)]:
        series = smr[smr.Factor_Type == phase]
        assert len(series) == 32
        assert series.Value_Numeric.tolist() == pytest.approx([value] * 32)
    assert "Nuclear" in set(model.Technology)
    assumption = get_technology_assumption("SMR")
    assert assumption.lifetime_years == 40
    assert assumption.construction_time_years == 8
    assert assumption.lifetime_source_year == assumption.construction_time_source_year == 2030
    assert assumption.technology_sheet == "13.b. Nuclear SMR"
    assert "D10" in assumption.notes and "D11" in assumption.notes


def test_legacy_sources_and_unique_phase_accounting_survive():
    yearly = get_yearly_employment_factors()
    legacy = yearly[(yearly.Source == "Rutovitz 2015") & (yearly.Technology == "Hydro (small)")]
    assert legacy.loc[(legacy.Year == 2024) & (legacy.Factor_Type == "O&M"), "Value_Numeric"].item() == pytest.approx(5.1058)
    keys = ["Source", "Technology", "Factor_Type", "Job_Type", "Unit", "Year"]
    assert not yearly.duplicated(keys).any()
    # Re-running combination must not add another C&M row.
    combined = add_construction_manufacturing_rows(yearly)
    assert len(combined) == len(yearly)
