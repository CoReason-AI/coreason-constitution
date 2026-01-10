# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import pytest
from pydantic import ValidationError
from coreason_economist.models import Budget, Cost

def test_budget_negative_validation() -> None:
    """Test that Budget raises ValidationError for negative values."""
    with pytest.raises(ValidationError):
        Budget(financial_limit=-1.0)

    with pytest.raises(ValidationError):
        Budget(latency_limit_ms=-100)

    with pytest.raises(ValidationError):
        Budget(token_limit=-5)

def test_cost_negative_validation() -> None:
    """Test that Cost raises ValidationError for negative values."""
    with pytest.raises(ValidationError):
        Cost(financial_cost=-0.01)

    with pytest.raises(ValidationError):
        Cost(latency_ms=-1)

    with pytest.raises(ValidationError):
        Cost(input_tokens=-10)

    with pytest.raises(ValidationError):
        Cost(output_tokens=-10)

def test_budget_zero_values() -> None:
    """Test that zero values are accepted (boundary condition)."""
    budget = Budget(financial_limit=0.0, latency_limit_ms=0, token_limit=0)
    assert budget.financial_limit == 0.0
    assert budget.latency_limit_ms == 0
    assert budget.token_limit == 0

def test_cost_zero_values() -> None:
    """Test that zero values are accepted (boundary condition)."""
    cost = Cost(financial_cost=0.0, latency_ms=0, input_tokens=0, output_tokens=0)
    assert cost.financial_cost == 0.0
    assert cost.latency_ms == 0
    assert cost.input_tokens == 0
    assert cost.output_tokens == 0

def test_extreme_values() -> None:
    """Test handling of large values."""
    large_int = 10**12
    large_float = 1.0 * (10**9)

    budget = Budget(token_limit=large_int, financial_limit=large_float)
    assert budget.token_limit == large_int
    assert budget.financial_limit == large_float

    cost = Cost(input_tokens=large_int)
    assert cost.input_tokens == large_int
