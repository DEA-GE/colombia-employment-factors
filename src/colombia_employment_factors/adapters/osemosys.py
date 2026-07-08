"""Helpers for applying employment factors to OSeMOSYS-style outputs."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

DEFAULT_TECHNOLOGY_COLUMNS = ("TECHNOLOGY", "Technology", "technology")
DEFAULT_YEAR_COLUMNS = ("YEAR", "Year", "year")
DEFAULT_CAPACITY_COLUMNS = ("NewCapacity", "new_capacity", "VALUE", "Value", "value")


def _first_present(columns: pd.Index, candidates: tuple[str, ...], explicit: str | None) -> str:
    if explicit is not None:
        if explicit not in columns:
            raise KeyError(f"Column not found: {explicit}")
        return explicit
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise KeyError(f"None of these columns were found: {', '.join(candidates)}")


def calculate_capacity_jobs(
    capacity_results: pd.DataFrame,
    employment_factors: pd.DataFrame,
    *,
    technology_mapping: Mapping[str, str] | None = None,
    technology_column: str | None = None,
    year_column: str | None = None,
    capacity_column: str | None = None,
    factor_type: str | None = None,
    job_type: str | None = None,
    source: str | None = None,
    value_column: str = "Value_Numeric",
) -> pd.DataFrame:
    """Multiply OSeMOSYS capacity results by matching employment factors.

    Parameters
    ----------
    capacity_results:
        DataFrame containing at least technology, year, and capacity columns.
    employment_factors:
        Long-format employment-factor table from this package.
    technology_mapping:
        Optional mapping from OSeMOSYS technology names to employment-factor
        technology names. If omitted, names are matched directly.
    factor_type, job_type, source:
        Optional filters applied to the employment-factor table before merging.
    value_column:
        Employment-factor numeric column to use. Defaults to ``Value_Numeric``.
    """
    tech_col = _first_present(capacity_results.columns, DEFAULT_TECHNOLOGY_COLUMNS, technology_column)
    year_col = _first_present(capacity_results.columns, DEFAULT_YEAR_COLUMNS, year_column)
    cap_col = _first_present(capacity_results.columns, DEFAULT_CAPACITY_COLUMNS, capacity_column)

    factors = employment_factors.copy()
    for column, value in {
        "Factor_Type": factor_type,
        "Job_Type": job_type,
        "Source": source,
    }.items():
        if value is not None:
            factors = factors[factors[column] == value]

    results = capacity_results.copy()
    results["_employment_factor_technology"] = results[tech_col]
    if technology_mapping is not None:
        results["_employment_factor_technology"] = results["_employment_factor_technology"].map(
            lambda technology: technology_mapping.get(technology, technology)
        )

    merged = results.merge(
        factors,
        left_on=["_employment_factor_technology", year_col],
        right_on=["Technology", "Year"],
        how="left",
        suffixes=("_model", "_factor"),
    )
    merged["Employment"] = merged[cap_col] * pd.to_numeric(merged[value_column], errors="coerce")
    merged = merged.rename(
        columns={
            tech_col: "Model_Technology",
            year_col: "Model_Year",
            cap_col: "Model_Capacity",
        }
    )
    return merged.drop(columns=["_employment_factor_technology"])
