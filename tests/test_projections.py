import pandas as pd
import pytest

from colombia_employment_factors.projections import project_employment_factors


def test_project_employment_factors_adds_learning_curve_rows():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2025",
                "Technology": "Battery storage (distributed)",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2024,
                "Value": 4.44,
                "Value_Numeric": 4.44,
            }
        ]
    )

    projected = project_employment_factors(source)
    row_2030 = projected[projected["Year"] == 2030].iloc[0]

    assert len(projected) == 3
    assert row_2030["Method_Applied"] == "Learning curve from cumulative capacity ratio"
    assert row_2030["Mapped_Catalogue_Tech"] == "Battery storage"
    assert row_2030["Projected_Value"] == pytest.approx(3.3405472979883593)


def test_project_employment_factors_does_not_project_2024_o_and_m_rows():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2025",
                "Technology": "Battery storage (distributed)",
                "Factor_Type": "O&M",
                "Job_Type": "Direct",
                "Unit": "jobs/MW",
                "Year": 2024,
                "Value": 0.11,
                "Value_Numeric": 0.11,
            }
        ]
    )

    projected = project_employment_factors(source)

    assert len(projected) == 1
    assert set(projected["Year"]) == {2024}


def test_project_employment_factors_adds_rutovitz_decline_row():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2015",
                "Technology": "Utility-scale solar PV",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2015,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            }
        ]
    )

    projected = project_employment_factors(source)
    row_2030 = projected[projected["Year"] == 2030].iloc[0]

    assert len(projected) == 2
    assert row_2030["Method_Applied"] == "Rutovitz Table 9 decline to 2030"
    assert row_2030["Rutovitz_2030_Factor"] == pytest.approx(0.59)
    assert row_2030["Projected_Value"] == pytest.approx(5.9)


def test_project_employment_factors_adds_rutovitz_o_and_m_decline_row():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2015",
                "Technology": "Utility-scale solar PV",
                "Factor_Type": "O&M",
                "Job_Type": "Direct",
                "Unit": "jobs/MW",
                "Year": 2015,
                "Value": 1.0,
                "Value_Numeric": 1.0,
            }
        ]
    )

    projected = project_employment_factors(source)
    row_2030 = projected[projected["Year"] == 2030].iloc[0]

    assert len(projected) == 2
    assert row_2030["Method_Applied"] == "Rutovitz Table 9 decline to 2030"
    assert row_2030["Projected_Value"] == pytest.approx(0.59)


def test_project_employment_factors_skips_rutovitz_fuel_and_projects_zero_declines():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2015",
                "Technology": "Utility-scale solar PV",
                "Factor_Type": "Fuel",
                "Job_Type": "Direct",
                "Unit": "jobs/PJ",
                "Year": 2015,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            },
            {
                "Source": "Rutovitz 2015",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2015,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            },
        ]
    )

    projected = project_employment_factors(source)
    row_2030 = projected[projected["Year"] == 2030].iloc[0]

    assert len(projected) == 3
    assert row_2030["Technology"] == "Coal power"
    assert row_2030["Rutovitz_2030_Factor"] == pytest.approx(1.0)
    assert row_2030["Projected_Value"] == pytest.approx(10.0)
