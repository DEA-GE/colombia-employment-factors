"""Read and query packaged employment-factor tables."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pandas as pd

DEFAULT_PROCESSED_FILE = "employment_factors_with_2030_2050.csv"
DEFAULT_YEARLY_FILE = "employment_factors_yearly_2024_2055.csv"
DEFAULT_MODEL_FILE = "employment_factors_model_default_2024_2055.csv"


def _default_data_path() -> Path:
    return resources.files("colombia_employment_factors.data").joinpath(DEFAULT_PROCESSED_FILE)


def get_employment_factors(path: str | Path | None = None) -> pd.DataFrame:
    """Return the processed employment-factor table.

    Parameters
    ----------
    path:
        Optional explicit CSV path. If omitted, the processed CSV packaged with
        this project is used.
    """
    data_path = Path(path) if path is not None else _default_data_path()
    return pd.read_csv(data_path)


def get_yearly_employment_factors(path: str | Path | None = None) -> pd.DataFrame:
    """Return the all-source yearly employment-factor table for 2024-2055."""
    data_path = (
        Path(path)
        if path is not None
        else resources.files("colombia_employment_factors.data").joinpath(DEFAULT_YEARLY_FILE)
    )
    return pd.read_csv(data_path)


def get_model_employment_factors(path: str | Path | None = None) -> pd.DataFrame:
    """Return the model-ready default-source yearly employment-factor table."""
    data_path = (
        Path(path)
        if path is not None
        else resources.files("colombia_employment_factors.data").joinpath(DEFAULT_MODEL_FILE)
    )
    return pd.read_csv(data_path)


def filter_employment_factors(
    factors: pd.DataFrame,
    technology: str | None = None,
    year: int | None = None,
    factor_type: str | None = None,
    job_type: str | None = None,
    source: str | None = None,
) -> pd.DataFrame:
    """Filter an employment-factor table by common dimensions."""
    filtered = factors
    filters = {
        "Technology": technology,
        "Year": year,
        "Factor_Type": factor_type,
        "Job_Type": job_type,
        "Source": source,
    }
    for column, value in filters.items():
        if value is not None:
            filtered = filtered[filtered[column] == value]
    return filtered.reset_index(drop=True)
