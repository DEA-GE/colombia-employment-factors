from pathlib import Path

import pandas as pd
import pytest

from colombia_employment_factors.catalogue import read_catalogue

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "docs/sources/datos_cuantitativos_EN.xlsx"
SELECTIONS = ROOT / "data/curated/catalogue_rows.csv"


def test_catalogue_extraction_preserves_published_ratios_and_assumptions():
    ratios, assumptions = read_catalogue(WORKBOOK, SELECTIONS)
    published = pd.read_csv(ROOT / "data/audit/capex_opex_ratios_2024_2030_2050.csv")
    pd.testing.assert_frame_equal(ratios, published, rtol=1e-14, atol=1e-14)
    expected = pd.read_csv(ROOT / "src/colombia_employment_factors/data/technology_assumptions_2024.csv")
    pd.testing.assert_frame_equal(assumptions.fillna(""), expected.fillna(""), check_dtype=False)
    floating = assumptions.set_index("Technology").loc["Offshore wind (floating)"]
    assert floating.construction_time_source_year == 2030
    assert floating.construction_time_years == 2.5
    assert len(ratios) == 26


def test_catalogue_rejects_stale_row_selections(tmp_path):
    selections = pd.read_csv(SELECTIONS)
    selections.loc[0, "capex_row_used"] = "Wrong cost boundary"
    path = tmp_path / "catalogue_rows.csv"
    selections.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Catalogue row changed"):
        read_catalogue(WORKBOOK, path)
