"""Projection logic for employment-factor tables."""

from __future__ import annotations

import pandas as pd

from colombia_employment_factors.learning import apply_learning_curve
from colombia_employment_factors.mappings import (
    CAPACITY_RATIOS,
    CAPEX_RATIOS,
    PROJECTED_FACTOR_TYPES,
    PROJECTION_YEARS,
    RUTOVITZ_DECLINE_FACTORS,
    RUTOVITZ_PROJECTED_FACTOR_TYPES,
    TECH_CATALOGUE_MAPPINGS,
)


def _numeric_value(row: pd.Series) -> float:
    return pd.to_numeric(row.get("Value_Numeric", row.get("Value")), errors="coerce")


def _original_row(row: pd.Series, value: float) -> dict:
    year = row["Year"]
    return {
        **row.to_dict(),
        "Method_Applied": "Original",
        "Mapped_Rutovitz_Tech": "",
        "Rutovitz_2030_Factor": "",
        "Mapped_Catalogue_Tech": "",
        "Learning_Rate": "",
        "Projection_Input": "",
        "Base_Year": year,
        "Projected_Year": year,
        "Projected_Value": value,
    }


def _rutovitz_2030_row(row: pd.Series, value: float) -> dict | None:
    factor_type = row["Factor_Type"] if pd.notna(row["Factor_Type"]) else ""
    technology = row["Technology"]
    if (
        row["Source"] != "Rutovitz 2015"
        or factor_type not in RUTOVITZ_PROJECTED_FACTOR_TYPES
        or technology not in RUTOVITZ_DECLINE_FACTORS
    ):
        return None

    mapped_tech, decline = RUTOVITZ_DECLINE_FACTORS[technology]
    multiplier = 1 - decline
    projected_value = value * multiplier
    return {
        **row.to_dict(),
        "Year": 2030,
        "Value": projected_value,
        "Value_Numeric": projected_value,
        "Method_Applied": "Rutovitz Table 9 decline to 2030",
        "Mapped_Rutovitz_Tech": mapped_tech,
        "Rutovitz_2030_Factor": multiplier,
        "Mapped_Catalogue_Tech": "",
        "Learning_Rate": "",
        "Projection_Input": "Rutovitz Table 9 Latin America 2030",
        "Base_Year": row["Year"],
        "Projected_Year": 2030,
        "Projected_Value": projected_value,
    }


def _projected_2024_rows(row: pd.Series, value: float) -> list[dict]:
    factor_type = row["Factor_Type"] if pd.notna(row["Factor_Type"]) else ""
    technology = row["Technology"]
    if row["Year"] != 2024 or factor_type not in PROJECTED_FACTOR_TYPES:
        return []
    if technology not in TECH_CATALOGUE_MAPPINGS:
        return []

    mapped_tech, learning_rate, method = TECH_CATALOGUE_MAPPINGS[technology]
    projected_rows = []

    if method == "capacity_ratio" and learning_rate is not None:
        for year in PROJECTION_YEARS:
            ratio = CAPACITY_RATIOS[year].get(mapped_tech)
            if ratio is None:
                continue
            projected_value = apply_learning_curve(value, ratio, learning_rate)
            projected_rows.append(
                {
                    **row.to_dict(),
                    "Year": year,
                    "Value": projected_value,
                    "Value_Numeric": projected_value,
                    "Method_Applied": "Learning curve from cumulative capacity ratio",
                    "Mapped_Rutovitz_Tech": "",
                    "Rutovitz_2030_Factor": "",
                    "Mapped_Catalogue_Tech": mapped_tech,
                    "Learning_Rate": learning_rate,
                    "Projection_Input": f"STEPS capacity ratio={ratio}",
                    "Base_Year": row["Year"],
                    "Projected_Year": year,
                    "Projected_Value": projected_value,
                }
            )
    elif method == "capex_ratio":
        for year in PROJECTION_YEARS:
            ratio = CAPEX_RATIOS[year].get(mapped_tech)
            if ratio is None:
                continue
            projected_rows.append(_capex_row(row, value, year, ratio, mapped_tech, "CAPEX ratio fallback"))
    elif method == "capex_ratio_proxy":
        for year in PROJECTION_YEARS:
            ratio = CAPEX_RATIOS[year]["Oil proxy"]
            projected_rows.append(
                _capex_row(row, value, year, ratio, mapped_tech, "CAPEX ratio proxy from gas", proxy=True)
            )

    return projected_rows


def _capex_row(
    row: pd.Series,
    value: float,
    year: int,
    ratio: float,
    mapped_tech: str,
    method: str,
    proxy: bool = False,
) -> dict:
    projected_value = value * ratio
    label = "Proxy CAPEX" if proxy else "CAPEX"
    return {
        **row.to_dict(),
        "Year": year,
        "Value": projected_value,
        "Value_Numeric": projected_value,
        "Method_Applied": method,
        "Mapped_Rutovitz_Tech": "",
        "Rutovitz_2030_Factor": "",
        "Mapped_Catalogue_Tech": mapped_tech,
        "Learning_Rate": "",
        "Projection_Input": f"{label} {year}/2024={ratio}",
        "Base_Year": row["Year"],
        "Projected_Year": year,
        "Projected_Value": projected_value,
    }


def project_employment_factors(employment_factors: pd.DataFrame) -> pd.DataFrame:
    """Return original and projected employment-factor rows."""
    df = employment_factors.copy()
    if "Value_Numeric" not in df.columns:
        df["Value_Numeric"] = pd.to_numeric(df["Value"], errors="coerce")
    else:
        df["Value_Numeric"] = pd.to_numeric(df["Value_Numeric"], errors="coerce")

    rows = []
    for _, row in df.iterrows():
        value = _numeric_value(row)
        if pd.isna(value):
            continue

        rows.append(_original_row(row, value))

        rutovitz_row = _rutovitz_2030_row(row, value)
        if rutovitz_row is not None:
            rows.append(rutovitz_row)

        rows.extend(_projected_2024_rows(row, value))

    output = pd.DataFrame(rows)
    return output.sort_values(
        ["Technology", "Factor_Type", "Job_Type", "Source", "Projected_Year"]
    ).reset_index(drop=True)
