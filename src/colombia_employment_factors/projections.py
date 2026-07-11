"""Projection logic for employment-factor tables."""

from __future__ import annotations

import pandas as pd

from colombia_employment_factors.mappings import (
    CAPEX_OPEX_TECH_MAPPINGS,
    RUTOVITZ_DECLINE_FACTORS,
    RUTOVITZ_PROJECTED_FACTOR_TYPES,
)

RATIO_PROJECTED_FACTOR_TYPES = ("Construction", "Manufacturing", "Construction&Manufacturing", "O&M")
QBIS_RATIO_BASE_SOURCES = ("Danish QBIS 2020", "French QBIS 2023")


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


def _projected_row(
    row: pd.Series,
    value: float,
    year: int,
    method: str,
    mapped_rutovitz_tech: str = "",
    rutovitz_factor: float | str = "",
    mapped_catalogue_tech: str = "",
    projection_input: str = "",
    base_year: int | None = None,
) -> dict:
    return {
        **row.to_dict(),
        "Year": year,
        "Value": value,
        "Value_Numeric": value,
        "Method_Applied": method,
        "Mapped_Rutovitz_Tech": mapped_rutovitz_tech,
        "Rutovitz_2030_Factor": rutovitz_factor,
        "Mapped_Catalogue_Tech": mapped_catalogue_tech,
        "Learning_Rate": "",
        "Projection_Input": projection_input,
        "Base_Year": row["Year"] if base_year is None else base_year,
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
    return _projected_row(
        row,
        projected_value,
        2030,
        "Rutovitz Table 9 decline to 2030",
        mapped_rutovitz_tech=mapped_tech,
        rutovitz_factor=multiplier,
        projection_input="Rutovitz Table 9 Latin America 2030",
        base_year=row["Year"],
    )


def _ratio_lookup(capex_opex_ratios: pd.DataFrame | None) -> dict[str, dict[str, float]]:
    if capex_opex_ratios is None:
        return {}

    required_columns = {
        "technology_name",
        "capex_ratio_2030_over_2024",
        "capex_ratio_2050_over_2030",
        "opex_ratio_2030_over_2024",
        "opex_ratio_2050_over_2030",
    }
    missing = required_columns - set(capex_opex_ratios.columns)
    if missing:
        raise ValueError(f"Missing CAPEX/OPEX ratio columns: {sorted(missing)}")

    ratios = capex_opex_ratios.copy()
    for column in required_columns - {"technology_name"}:
        ratios[column] = pd.to_numeric(ratios[column], errors="coerce")

    return {
        row["technology_name"]: {
            "capex_2030_2024": row["capex_ratio_2030_over_2024"],
            "capex_2050_2030": row["capex_ratio_2050_over_2030"],
            "opex_2030_2024": row["opex_ratio_2030_over_2024"],
            "opex_2050_2030": row["opex_ratio_2050_over_2030"],
        }
        for _, row in ratios.iterrows()
    }


def _ratio_kind(factor_type: str) -> str:
    return "opex" if factor_type == "O&M" else "capex"


def _ratio_value(
    technology: str,
    factor_type: str,
    transition: str,
    ratios_by_technology: dict[str, dict[str, float]],
) -> tuple[str, float, str]:
    mapped = CAPEX_OPEX_TECH_MAPPINGS.get(technology)
    if mapped is None:
        return "", 1.0, "constant_missing_mapping"

    mapped_tech, mapping_type, _ = mapped
    if mapping_type == "unmapped_constant" or not mapped_tech:
        return mapped_tech, 1.0, mapping_type

    ratio_kind = _ratio_kind(factor_type)
    ratio = ratios_by_technology.get(mapped_tech, {}).get(f"{ratio_kind}_{transition}")
    if pd.isna(ratio):
        if mapping_type == "partial":
            return mapped_tech, 1.0, mapping_type
        return mapped_tech, 1.0, "constant_missing_ratio"

    return mapped_tech, float(ratio), mapping_type


def _ratio_method(mapping_type: str) -> str:
    if mapping_type == "unmapped_constant":
        return "Constant projection for unmapped catalogue ratio"
    if mapping_type in ("partial", "constant_missing_ratio"):
        return "CAPEX/OPEX ratio projection with constant bridge"
    if mapping_type == "proxy":
        return "CAPEX/OPEX ratio projection using proxy mapping"
    return "CAPEX/OPEX ratio projection"


def _ratio_projection_input(factor_type: str, transition: str, ratio: float, mapping_type: str) -> str:
    ratio_label = "OPEX" if _ratio_kind(factor_type) == "opex" else "CAPEX"
    if mapping_type in ("unmapped_constant", "constant_missing_mapping"):
        return "No catalogue ratio mapping; value held constant"
    if mapping_type in ("partial", "constant_missing_ratio") and ratio == 1.0:
        return f"{ratio_label} {transition.replace('_', '/')} unavailable; value held constant"
    return f"{ratio_label} {transition.replace('_', '/')}={ratio}"


def _is_ratio_base_row(row: pd.Series, factor_type: str) -> bool:
    if factor_type not in RATIO_PROJECTED_FACTOR_TYPES:
        return False
    if row["Year"] == 2024:
        return True
    return row["Year"] == 2022 and row["Source"] in QBIS_RATIO_BASE_SOURCES


def _projected_ratio_rows(
    row: pd.Series,
    value: float,
    ratios_by_technology: dict[str, dict[str, float]],
) -> list[dict]:
    factor_type = row["Factor_Type"] if pd.notna(row["Factor_Type"]) else ""
    technology = row["Technology"]
    if not _is_ratio_base_row(row, factor_type):
        return []
    if technology not in CAPEX_OPEX_TECH_MAPPINGS:
        return []

    mapped_tech, ratio_2030, mapping_type_2030 = _ratio_value(
        technology, factor_type, "2030_2024", ratios_by_technology
    )
    projection_input_2030 = _ratio_projection_input(factor_type, "2030_2024", ratio_2030, mapping_type_2030)
    if row["Year"] == 2022:
        projection_input_2030 = f"{projection_input_2030}; applied to 2022 QBIS base value"

    value_2030 = value * ratio_2030
    row_2030 = _projected_row(
        row,
        value_2030,
        2030,
        _ratio_method(mapping_type_2030),
        mapped_catalogue_tech=mapped_tech,
        projection_input=projection_input_2030,
        base_year=row["Year"],
    )

    _, ratio_2050, mapping_type_2050 = _ratio_value(
        technology, factor_type, "2050_2030", ratios_by_technology
    )
    value_2050 = value_2030 * ratio_2050
    row_2050 = _projected_row(
        row,
        value_2050,
        2050,
        _ratio_method(mapping_type_2050),
        mapped_catalogue_tech=mapped_tech,
        projection_input=_ratio_projection_input(factor_type, "2050_2030", ratio_2050, mapping_type_2050),
        base_year=2030,
    )
    return [row_2030, row_2050]


def _rutovitz_2050_ratio_row(
    row_2030: dict,
    ratios_by_technology: dict[str, dict[str, float]],
) -> dict:
    row = pd.Series(row_2030)
    factor_type = row["Factor_Type"] if pd.notna(row["Factor_Type"]) else ""
    technology = row["Technology"]
    mapped_tech, ratio, mapping_type = _ratio_value(technology, factor_type, "2050_2030", ratios_by_technology)
    value_2050 = _numeric_value(row) * ratio
    return _projected_row(
        row,
        value_2050,
        2050,
        _ratio_method(mapping_type),
        mapped_rutovitz_tech=row.get("Mapped_Rutovitz_Tech", ""),
        mapped_catalogue_tech=mapped_tech,
        projection_input=_ratio_projection_input(factor_type, "2050_2030", ratio, mapping_type),
        base_year=2030,
    )


def project_employment_factors(
    employment_factors: pd.DataFrame,
    capex_opex_ratios: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return original and projected employment-factor rows."""
    df = employment_factors.copy()
    if "Value_Numeric" not in df.columns:
        df["Value_Numeric"] = pd.to_numeric(df["Value"], errors="coerce")
    else:
        df["Value_Numeric"] = pd.to_numeric(df["Value_Numeric"], errors="coerce")

    ratios_by_technology = _ratio_lookup(capex_opex_ratios)
    rows = []
    for _, row in df.iterrows():
        value = _numeric_value(row)
        if pd.isna(value):
            continue

        rows.append(_original_row(row, value))

        rutovitz_row = _rutovitz_2030_row(row, value)
        if rutovitz_row is not None:
            rows.append(rutovitz_row)
            rows.append(_rutovitz_2050_ratio_row(rutovitz_row, ratios_by_technology))

        rows.extend(_projected_ratio_rows(row, value, ratios_by_technology))

    output = pd.DataFrame(rows)
    return output.sort_values(
        ["Technology", "Factor_Type", "Job_Type", "Source", "Projected_Year"]
    ).reset_index(drop=True)
