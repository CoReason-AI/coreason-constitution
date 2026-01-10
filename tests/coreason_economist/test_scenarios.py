# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from coreason_economist.models import Budget, Cost, EconomicTrace, Decision

def check_budget(cost: Cost, budget: Budget) -> bool:
    """
    Simulation of budget checking logic using the models.
    Returns True if cost is within budget, False otherwise.
    """
    if budget.financial_limit is not None and cost.financial_cost > budget.financial_limit:
        return False
    if budget.latency_limit_ms is not None and cost.latency_ms > budget.latency_limit_ms:
        return False
    if budget.token_limit is not None and cost.total_tokens > budget.token_limit:
        return False
    return True

def test_budget_comparison_scenario() -> None:
    """
    Test a scenario where we evaluate if a request cost fits within a budget.
    This validates the models expose necessary fields for logic implementation.
    """
    # Case 1: Within limits
    budget = Budget(financial_limit=1.0, token_limit=1000)
    cost = Cost(financial_cost=0.5, input_tokens=500, output_tokens=100) # total 600
    assert check_budget(cost, budget) is True

    # Case 2: Exceeds financial
    expensive_cost = Cost(financial_cost=1.5)
    assert check_budget(expensive_cost, budget) is False

    # Case 3: Exceeds tokens
    verbose_cost = Cost(input_tokens=800, output_tokens=300) # total 1100
    assert check_budget(verbose_cost, budget) is False

def test_trace_serialization_scenario() -> None:
    """
    Test creating a full trace and dumping it to dict/json.
    Simulates observability logging.
    """
    cost = Cost(financial_cost=0.02, latency_ms=150, input_tokens=100, output_tokens=50)
    trace = EconomicTrace(
        trace_id="trace-001",
        request_id="req-abc",
        estimated_cost=cost,
        actual_cost=cost,
        decision=Decision.APPROVED,
        voc_score=0.95,
        reason="Good value"
    )

    data = trace.model_dump()
    assert data["trace_id"] == "trace-001"
    assert data["estimated_cost"]["financial_cost"] == 0.02
    assert data["decision"] == Decision.APPROVED
    assert data["voc_score"] == 0.95
