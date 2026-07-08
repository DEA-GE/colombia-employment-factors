import math

import pytest

from colombia_employment_factors.learning import learning_multiplier


def test_learning_multiplier_matches_excel_formula():
    capacity_ratio = 6.5
    learning_rate = 0.10

    expected = capacity_ratio ** (math.log(1 - learning_rate) / math.log(2))

    assert learning_multiplier(capacity_ratio, learning_rate) == pytest.approx(expected)


def test_learning_multiplier_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        learning_multiplier(0, 0.10)

    with pytest.raises(ValueError):
        learning_multiplier(2, 1.0)
