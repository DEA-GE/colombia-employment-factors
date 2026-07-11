import pandas as pd

from colombia_employment_factors import (
    DEFAULT_SOURCE_BY_TECHNOLOGY,
    get_model_employment_factors,
    get_yearly_employment_factors,
)


def test_get_yearly_employment_factors_accepts_explicit_path(tmp_path):
    path = tmp_path / "yearly.csv"
    pd.DataFrame([{"Technology": "Coal power", "Year": 2024, "Value_Numeric": 1.0}]).to_csv(
        path, index=False
    )

    result = get_yearly_employment_factors(path)

    assert result.loc[0, "Technology"] == "Coal power"


def test_get_model_employment_factors_accepts_explicit_path(tmp_path):
    path = tmp_path / "model.csv"
    pd.DataFrame([{"Technology": "Coal power", "Year": 2024, "Value_Numeric": 1.0}]).to_csv(
        path, index=False
    )

    result = get_model_employment_factors(path)

    assert result.loc[0, "Year"] == 2024


def test_default_source_mapping_is_importable():
    assert DEFAULT_SOURCE_BY_TECHNOLOGY["Offshore wind (fixed)"] == "French QBIS 2023"
    assert DEFAULT_SOURCE_BY_TECHNOLOGY["Rooftop solar PV"] == "JEDI-US"
