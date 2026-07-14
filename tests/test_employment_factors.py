import pandas as pd

from colombia_employment_factors import (
    DEFAULT_SOURCE_BY_TECHNOLOGY,
    get_model_employment_factors,
    get_technology_assumption,
    get_technology_assumptions,
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


def test_get_technology_assumptions_accepts_explicit_path(tmp_path):
    path = tmp_path / "assumptions.csv"
    pd.DataFrame(
        [
            {
                "Technology": "Onshore wind",
                "lifetime_years": 27,
                "construction_time_years": 1.5,
            }
        ]
    ).to_csv(path, index=False)

    result = get_technology_assumptions(path)

    assert result.loc[0, "Technology"] == "Onshore wind"


def test_get_technology_assumption_returns_packaged_catalogue_values():
    assumption = get_technology_assumption("Utility-scale solar PV")

    assert assumption["lifetime_years"] == 27
    assert assumption["lifetime_source_year"] == 2024
    assert assumption["construction_time_years"] == 0.5
    assert assumption["construction_time_source_year"] == 2024
    assert assumption["technology_sheet"] == "2.d. Utility scale PV(tracking)"


def test_get_technology_assumption_uses_rutovitz_construction_time_fallback():
    assumption = get_technology_assumption("Solar thermal (CSP)")

    assert pd.isna(assumption["lifetime_years"])
    assert assumption["construction_time_years"] == 2
    assert assumption["construction_time_source_year"] == 2015
    assert assumption["construction_time_source"] == "Rutovitz 2015 Table 1"
    assert "Rutovitz 2015 Table 1" in assumption["notes"]


def test_get_technology_assumption_uses_2030_floating_offshore_construction_time():
    assumption = get_technology_assumption("Offshore wind (floating)")

    assert assumption["lifetime_years"] == 30
    assert assumption["lifetime_source_year"] == 2030
    assert assumption["construction_time_years"] == 2.5
    assert assumption["construction_time_source_year"] == 2030


def test_get_technology_assumption_documents_missing_transmission_values():
    assumption = get_technology_assumption("Transmission (single circuit)")

    assert pd.isna(assumption["lifetime_years"])
    assert pd.isna(assumption["construction_time_years"])
    assert "No matching Technology Catalogue or Rutovitz 2015 Table 1" in assumption["notes"]


def test_get_technology_assumption_raises_for_unknown_technology():
    try:
        get_technology_assumption("Unknown technology")
    except KeyError as error:
        assert "Unknown technology" in str(error)
    else:
        raise AssertionError("Expected KeyError")
