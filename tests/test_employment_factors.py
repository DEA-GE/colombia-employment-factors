import pandas as pd
import pytest
import json
import hashlib
from pathlib import Path

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


@pytest.mark.parametrize("productivity_transfer", [False, True])
def test_get_model_employment_factors_accepts_explicit_path(tmp_path, productivity_transfer):
    path = tmp_path / "model.csv"
    pd.DataFrame([{"Technology": "Coal power", "Year": 2024, "Value_Numeric": 1.0}]).to_csv(
        path, index=False
    )

    result = get_model_employment_factors(path, productivity_transfer=productivity_transfer)

    assert result.loc[0, "Year"] == 2024
    assert result.loc[0, "Value_Numeric"] == 1.0


def test_model_productivity_transfer_is_opt_in():
    default = get_model_employment_factors()
    pd.testing.assert_frame_equal(default, get_model_employment_factors(productivity_transfer=False))
    adjusted = get_model_employment_factors(productivity_transfer=True)
    keys = ["Technology", "Factor_Type", "Job_Type", "Unit", "Year"]
    assert default[keys].equals(adjusted[keys])
    assert not default.Source.str.contains("LATAM productivity proxy", regex=False).any()
    battery = (default.Technology == "Battery storage (distributed)") & (default.Factor_Type == "Construction") & (default.Year == 2024)
    assert default.loc[battery, "Value_Numeric"].item() == pytest.approx(4.44)
    assert adjusted.loc[battery, "Value_Numeric"].item() == pytest.approx(4.44 / 0.32)
    # Colombia-calibrated factors are identical in both bundled choices.
    solar = default.Technology.isin(["Utility-scale solar PV", "Rooftop solar PV"])
    pd.testing.assert_frame_equal(default[solar], adjusted[solar])


def test_default_source_mapping_is_importable():
    model = get_model_employment_factors()
    selected = model[["Technology", "Source"]].drop_duplicates()
    assert DEFAULT_SOURCE_BY_TECHNOLOGY == dict(zip(selected.Technology, selected.Source))
    assert DEFAULT_SOURCE_BY_TECHNOLOGY["Nuclear"] == "Rutovitz 2015"


def test_packaged_rooftop_defaults_use_six_transferred_ratios():
    root = Path(__file__).resolve().parents[1]
    provenance = json.loads((root / "src/colombia_employment_factors/data/employment_factor_provenance.json").read_text())
    assert provenance["solar_transfer_ready"] is True
    assert len(provenance["solar_ratios"]) == 6
    assert provenance["productivity_transfer"] == "none"
    assert provenance["productivity_ratio"] == 1.0
    assert provenance["optional_productivity_model"]["productivity_ratio"] == 0.32
    model = get_model_employment_factors()
    roof = model[model.Technology == "Rooftop solar PV"]
    assert len(roof) == 32 * 6
    assert set(roof.Source) == {"I-JEDI Colombia + Rutovitz 2025 direct / US-JEDI indirect-induced PV ratios"}
    assert provenance["solar_ratio_method"] == "rutovitz-direct"
    for ratio in provenance["solar_ratios"]:
        actual = roof[(roof.Year == 2024) & (roof.Factor_Type == ratio["phase"]) & (roof.Job_Type == ratio["category"])]
        assert len(actual) == 1
        assert actual.Value_Numeric.iloc[0] == pytest.approx(ratio["colombia_rooftop"], rel=1e-10)
        if ratio["category"] == "Direct":
            expected = 4.19 / 1.61 if ratio["phase"] == "Construction&Manufacturing" else .13 / .09
            assert ratio["ratio"] == pytest.approx(expected)
            assert ratio["ratio_source"] == "Rutovitz 2025"
        else:
            assert ratio["ratio_source"] == "JEDI-US"
    for name, expected in provenance["output_sha256"].items():
        packaged = (root / "src/colombia_employment_factors/data" / name).read_bytes()
        assert hashlib.sha256(packaged).hexdigest() == expected


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
