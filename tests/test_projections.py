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


def test_project_employment_factors_adds_rutovitz_decline_row():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2015",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2015,
                "Value": 11.2,
                "Value_Numeric": 11.2,
            }
        ]
    )

    projected = project_employment_factors(source)
    row_2030 = projected[projected["Year"] == 2030].iloc[0]

    assert len(projected) == 2
    assert row_2030["Method_Applied"] == "Rutovitz Table 9 decline to 2030"
    assert row_2030["Projected_Value"] == pytest.approx(8.4)
