import pandas as pd
import pytest

from colombia_employment_factors.projections import project_employment_factors


def _ratio_table():
    return pd.DataFrame(
        [
            {
                "technology_name": "Utility-scale Lithium-ion",
                "capex_ratio_2030_over_2024": 0.6,
                "capex_ratio_2050_over_2030": 0.7,
                "opex_ratio_2030_over_2024": 0.8,
                "opex_ratio_2050_over_2030": 0.9,
            },
            {
                "technology_name": "Utility scale PV(tracking)",
                "capex_ratio_2030_over_2024": 0.69,
                "capex_ratio_2050_over_2030": 0.67,
                "opex_ratio_2030_over_2024": 0.85,
                "opex_ratio_2050_over_2030": 0.86,
            },
            {
                "technology_name": "Wind offshore floating",
                "capex_ratio_2030_over_2024": None,
                "capex_ratio_2050_over_2030": 0.522971,
                "opex_ratio_2030_over_2024": None,
                "opex_ratio_2050_over_2030": 0.520737,
            },
        ]
    )


def test_project_employment_factors_adds_capex_ratio_rows():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2025",
                "Technology": "Battery storage (grid)",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2024,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            }
        ]
    )

    projected = project_employment_factors(source, _ratio_table())
    row_2030 = projected[projected["Year"] == 2030].iloc[0]
    row_2050 = projected[projected["Year"] == 2050].iloc[0]

    assert len(projected) == 3
    assert row_2030["Method_Applied"] == "CAPEX/OPEX ratio projection"
    assert row_2030["Mapped_Catalogue_Tech"] == "Utility-scale Lithium-ion"
    assert row_2030["Projected_Value"] == pytest.approx(6.0)
    assert row_2050["Base_Year"] == 2030
    assert row_2050["Projected_Value"] == pytest.approx(4.2)


def test_project_employment_factors_adds_opex_ratio_rows_for_o_and_m():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2025",
                "Technology": "Battery storage (grid)",
                "Factor_Type": "O&M",
                "Job_Type": "Direct",
                "Unit": "jobs/MW",
                "Year": 2024,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            }
        ]
    )

    projected = project_employment_factors(source, _ratio_table())
    row_2030 = projected[projected["Year"] == 2030].iloc[0]
    row_2050 = projected[projected["Year"] == 2050].iloc[0]

    assert len(projected) == 3
    assert row_2030["Projected_Value"] == pytest.approx(8.0)
    assert row_2050["Projected_Value"] == pytest.approx(7.2)


def test_project_employment_factors_uses_constant_bridge_for_partial_floating_wind():
    source = pd.DataFrame(
        [
            {
                "Source": "French QBIS 2023",
                "Technology": "Offshore wind (floating)",
                "Factor_Type": "Construction&Manufacturing",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2024,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            }
        ]
    )

    projected = project_employment_factors(source, _ratio_table())
    row_2030 = projected[projected["Year"] == 2030].iloc[0]
    row_2050 = projected[projected["Year"] == 2050].iloc[0]

    assert row_2030["Projected_Value"] == pytest.approx(10.0)
    assert row_2030["Method_Applied"] == "CAPEX/OPEX ratio projection with constant bridge"
    assert row_2050["Projected_Value"] == pytest.approx(5.22971)


def test_project_employment_factors_applies_2030_2024_ratio_to_qbis_2022_rows():
    source = pd.DataFrame(
        [
            {
                "Source": "French QBIS 2023",
                "Technology": "Offshore wind (fixed)",
                "Factor_Type": "Construction&Manufacturing",
                "Job_Type": "Direct",
                "Unit": "job-yr/MW",
                "Year": 2022,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            }
        ]
    )

    ratio_table = pd.DataFrame(
        [
            {
                "technology_name": "Wind Offshore fixed bottom",
                "capex_ratio_2030_over_2024": 0.8,
                "capex_ratio_2050_over_2030": 0.75,
                "opex_ratio_2030_over_2024": 0.9,
                "opex_ratio_2050_over_2030": 0.85,
            }
        ]
    )

    projected = project_employment_factors(source, ratio_table)
    row_2030 = projected[projected["Year"] == 2030].iloc[0]
    row_2050 = projected[projected["Year"] == 2050].iloc[0]

    assert len(projected) == 3
    assert row_2030["Base_Year"] == 2022
    assert "applied to 2022 QBIS base value" in row_2030["Projection_Input"]
    assert row_2030["Projected_Value"] == pytest.approx(8.0)
    assert row_2050["Base_Year"] == 2030
    assert row_2050["Projected_Value"] == pytest.approx(6.0)


def test_project_employment_factors_holds_unmapped_technologies_constant():
    source = pd.DataFrame(
        [
            {
                "Source": "Rutovitz 2025",
                "Technology": "Transmission (single circuit)",
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Unit": "job-yr/km",
                "Year": 2024,
                "Value": 10.0,
                "Value_Numeric": 10.0,
            }
        ]
    )

    projected = project_employment_factors(source, _ratio_table())

    assert list(projected["Year"]) == [2024, 2030, 2050]
    assert projected.loc[projected["Year"] == 2030, "Projected_Value"].iloc[0] == pytest.approx(10.0)
    assert projected.loc[projected["Year"] == 2050, "Projected_Value"].iloc[0] == pytest.approx(10.0)


def test_project_employment_factors_adds_rutovitz_decline_and_2050_ratio_rows():
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

    projected = project_employment_factors(source, _ratio_table())
    row_2030 = projected[projected["Year"] == 2030].iloc[0]
    row_2050 = projected[projected["Year"] == 2050].iloc[0]

    assert len(projected) == 3
    assert row_2030["Method_Applied"] == "Rutovitz Table 9 decline to 2030"
    assert row_2030["Rutovitz_2030_Factor"] == pytest.approx(0.59)
    assert row_2030["Projected_Value"] == pytest.approx(5.9)
    assert row_2050["Base_Year"] == 2030
    assert row_2050["Projected_Value"] == pytest.approx(3.953)


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

    projected = project_employment_factors(source, _ratio_table())
    row_2030 = projected[projected["Year"] == 2030].iloc[0]

    assert len(projected) == 4
    assert row_2030["Technology"] == "Coal power"
    assert row_2030["Rutovitz_2030_Factor"] == pytest.approx(1.0)
    assert row_2030["Projected_Value"] == pytest.approx(10.0)
