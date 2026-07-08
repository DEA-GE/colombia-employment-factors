"""Learning-curve formulas used for employment-factor projections."""

from __future__ import annotations

import math


def learning_multiplier(capacity_ratio: float, learning_rate: float) -> float:
    """Return the multiplier implied by a learning rate and capacity ratio.

    This implements:

        capacity_ratio ** (LN(1 - learning_rate) / LN(2))

    which is equivalent to:

        capacity_ratio ** log2(1 - learning_rate)
    """
    if capacity_ratio <= 0:
        raise ValueError("capacity_ratio must be positive")
    if not 0 <= learning_rate < 1:
        raise ValueError("learning_rate must be greater than or equal to 0 and less than 1")
    return float(capacity_ratio ** math.log2(1 - learning_rate))


def apply_learning_curve(
    base_value: float,
    capacity_ratio: float,
    learning_rate: float,
) -> float:
    """Project a base employment factor using the learning-curve multiplier."""
    return float(base_value * learning_multiplier(capacity_ratio, learning_rate))
