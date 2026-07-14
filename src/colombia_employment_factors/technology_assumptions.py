"""Read packaged technology lifetime and construction-time assumptions."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pandas as pd

DEFAULT_TECHNOLOGY_ASSUMPTIONS_FILE = "technology_assumptions_2024.csv"


def _default_assumptions_path() -> Path:
    return resources.files("colombia_employment_factors.data").joinpath(
        DEFAULT_TECHNOLOGY_ASSUMPTIONS_FILE
    )


def get_technology_assumptions(path: str | Path | None = None) -> pd.DataFrame:
    """Return technology lifetime and construction-time assumptions.

    The packaged table is keyed by the package's employment-factor technology
    names. Values are selected from the 2024 Colombian Technology Catalogue
    workbook where available. Explicit fallback rows document cases where a
    2024 catalogue value is not available, such as Rutovitz 2015 Table 1
    construction times for ocean and solar thermal (CSP).

    Parameters
    ----------
    path:
        Optional explicit CSV path. If omitted, the packaged assumptions CSV is
        used.

    Returns
    -------
    pandas.DataFrame
        Columns include ``Technology``, ``lifetime_years``,
        ``construction_time_years``, source-year columns, source workbook/sheet
        columns, and notes describing fallback choices.
    """
    data_path = Path(path) if path is not None else _default_assumptions_path()
    return pd.read_csv(data_path)


def get_technology_assumption(
    technology: str,
    path: str | Path | None = None,
) -> pd.Series:
    """Return one technology's lifetime and construction-time assumptions.

    Parameters
    ----------
    technology:
        Employment-factor technology name, for example ``"Onshore wind"`` or
        ``"Utility-scale solar PV"``.
    path:
        Optional explicit CSV path. If omitted, the packaged assumptions CSV is
        used.

    Raises
    ------
    KeyError
        If ``technology`` is not present in the assumptions table.
    """
    assumptions = get_technology_assumptions(path)
    matches = assumptions[assumptions["Technology"] == technology]
    if matches.empty:
        raise KeyError(f"No technology assumptions found for {technology!r}")
    return matches.iloc[0]
