"""Yearly employment-factor tables for model use."""

from __future__ import annotations

import pandas as pd

from colombia_employment_factors.mappings import DEFAULT_SOURCE_BY_TECHNOLOGY, DEFAULT_SOURCE_NOTES

YEARLY_FACTOR_TYPES = ("Construction", "Manufacturing", "Construction&Manufacturing", "O&M")
YEARLY_START = 2024
YEARLY_END = 2055


def _interpolate_group(group: pd.DataFrame, years: range) -> pd.DataFrame:
    group = group.sort_values("Year").copy()
    group = group.drop_duplicates(subset=["Year"], keep="last")
    index = pd.Index(range(min(int(group["Year"].min()), YEARLY_START), YEARLY_END + 1), name="Year")
    values = pd.Series(group["Value_Numeric"].to_numpy(), index=group["Year"].astype(int))
    yearly = values.reindex(index).interpolate(method="linear")
    if 2050 in yearly.index and pd.notna(yearly.loc[2050]):
        yearly.loc[2051:YEARLY_END] = yearly.loc[2050]

    template = group.iloc[-1].to_dict()
    known_rows = {int(row["Year"]): row.to_dict() for _, row in group.iterrows()}
    rows = []
    for year in years:
        value = yearly.loc[year] if year in yearly.index else pd.NA
        if pd.isna(value):
            continue
        row_template = known_rows.get(year, template)
        rows.append(
            {
                **row_template,
                "Year": year,
                "Value": float(value),
                "Value_Numeric": float(value),
                "Method_Applied": row_template.get("Method_Applied", "Known datapoint")
                if year in known_rows
                else "Linear interpolation",
                "Interpolation_Method": (
                    "Known datapoint"
                    if year in known_rows
                    else "Linear interpolation to 2050; held constant after 2050"
                    if year > 2050
                    else "Linear interpolation between known datapoints"
                ),
                "Projected_Year": year,
                "Projected_Value": float(value),
            }
        )
    return pd.DataFrame(rows)


def build_yearly_employment_factors(
    projected_factors: pd.DataFrame,
    *,
    start_year: int = YEARLY_START,
    end_year: int = YEARLY_END,
) -> pd.DataFrame:
    """Return all-source yearly employment factors from sparse projected factors."""
    df = projected_factors.copy()
    df = df[df["Factor_Type"].isin(YEARLY_FACTOR_TYPES)]
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Value_Numeric"] = pd.to_numeric(df["Value_Numeric"], errors="coerce")
    df = df.dropna(subset=["Year", "Value_Numeric"])
    df["Year"] = df["Year"].astype(int)

    key_columns = ["Source", "Technology", "Factor_Type", "Job_Type", "Unit"]
    years = range(start_year, end_year + 1)
    yearly_groups = [
        _interpolate_group(group, years)
        for _, group in df.groupby(key_columns, dropna=False, sort=False)
    ]
    if not yearly_groups:
        return pd.DataFrame(columns=list(df.columns) + ["Interpolation_Method"])

    output = pd.concat(yearly_groups, ignore_index=True)
    return output.sort_values(
        ["Technology", "Factor_Type", "Job_Type", "Source", "Year"]
    ).reset_index(drop=True)


def build_default_model_employment_factors(
    yearly_factors: pd.DataFrame,
    default_sources: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return model-ready yearly factors using one default source per technology."""
    default_sources = DEFAULT_SOURCE_BY_TECHNOLOGY if default_sources is None else default_sources
    rows = []
    for technology, source in default_sources.items():
        selected = yearly_factors[
            (yearly_factors["Technology"] == technology)
            & (yearly_factors["Source"] == source)
        ].copy()
        if selected.empty:
            continue
        selected["Default_Source"] = source
        selected["Default_Source_Note"] = DEFAULT_SOURCE_NOTES.get(technology, "")
        rows.append(selected)

    if not rows:
        return yearly_factors.iloc[0:0].copy()

    output = pd.concat(rows, ignore_index=True)
    return output.sort_values(
        ["Technology", "Factor_Type", "Job_Type", "Year"]
    ).reset_index(drop=True)
