# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from coreason_economist.models import Budget, Cost, Currency, Decision, EconomicTrace, Request


def test_currency_enum() -> None:
    assert Currency.FINANCIAL.value == "USD"
    assert Currency.LATENCY.value == "MS"
    assert Currency.TOKEN_VOLUME.value == "TOKENS"


def test_decision_enum() -> None:
    # Since we used auto(), we just check they exist
    assert Decision.APPROVED is not None
    assert Decision.REJECTED is not None
    assert Decision.MODIFIED is not None


def test_budget_model() -> None:
    budget = Budget(financial_limit=0.50, latency_limit_ms=5000)
    assert budget.financial_limit == 0.50
    assert budget.latency_limit_ms == 5000
    assert budget.token_limit is None


def test_cost_model() -> None:
    cost = Cost(financial_cost=0.01, latency_ms=100, input_tokens=50, output_tokens=50)
    assert cost.total_tokens == 100
    assert cost.financial_cost == 0.01


def test_request_model() -> None:
    req = Request(request_id="123", model_name="gpt-4", input_text="Hello")
    assert req.task_type == "generation"
    assert req.metadata == {}


def test_economic_trace_model() -> None:
    est_cost = Cost(financial_cost=0.1)
    trace = EconomicTrace(trace_id="t1", request_id="r1", estimated_cost=est_cost, decision=Decision.APPROVED)
    assert trace.estimated_cost.financial_cost == 0.1
    assert trace.decision == Decision.APPROVED
    assert trace.actual_cost is None
