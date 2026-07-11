import pandas as pd
import pytest

from colombia_employment_factors.yearly import (
    build_default_model_employment_factors,
    build_yearly_employment_factors,
)


def test_build_yearly_employment_factors_interpolates_and_holds_2050_constant():
    sparse = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2015",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2015,
                "Value": 10.0,
                "Value_Numeric": 10.0,
                "Method_Applied": "Original",
                "Projected_Year": 2015,
                "Projected_Value": 10.0,
            },
            {
                "Source": "Rutovitz 2015",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2030,
                "Value": 20.0,
                "Value_Numeric": 20.0,
                "Method_Applied": "Projected",
                "Projected_Year": 2030,
                "Projected_Value": 20.0,
            },
            {
                "Source": "Rutovitz 2015",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2050,
                "Value": 30.0,
                "Value_Numeric": 30.0,
                "Method_Applied": "Projected",
                "Projected_Year": 2050,
                "Projected_Value": 30.0,
            },
        ]
    )

    yearly = build_yearly_employment_factors(sparse)

    assert yearly["Year"].min() == 2024
    assert yearly["Year"].max() == 2055
    assert yearly.loc[yearly["Year"] == 2024, "Value_Numeric"].iloc[0] == pytest.approx(16.0)
    assert yearly.loc[yearly["Year"] == 2040, "Value_Numeric"].iloc[0] == pytest.approx(25.0)
    assert yearly.loc[yearly["Year"] == 2055, "Value_Numeric"].iloc[0] == pytest.approx(30.0)


def test_build_default_model_employment_factors_selects_one_source_per_technology():
    yearly = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2015",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2024,
                "Value_Numeric": 1.0,
            },
            {
                "Source": "Rutovitz 2025",
                "Technology": "Coal power",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2024,
                "Value_Numeric": 2.0,
            },
        ]
    )

    model = build_default_model_employment_factors(yearly, {"Coal power": "Rutovitz 2015"})

    assert len(model) == 1
    assert model["Source"].iloc[0] == "Rutovitz 2015"
    assert model["Default_Source"].iloc[0] == "Rutovitz 2015"
