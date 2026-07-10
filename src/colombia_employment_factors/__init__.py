"""Employment-factor data and projections for Colombia power-sector models."""

from colombia_employment_factors.employment_factors import get_employment_factors
from colombia_employment_factors.projections import project_employment_factors

__all__ = [
    "get_employment_factors",
    "project_employment_factors",
]
