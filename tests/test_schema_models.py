# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from coreason_constitution.schema import (
    ConstitutionalTrace,
    Critique,
    LawSeverity,
    TraceStatus,
)


@pytest.fixture  # type: ignore
def critique_valid() -> Dict[str, Any]:
    return {
        "violation": True,
        "article_id": "GCP.4",
        "severity": "High",
        "reasoning": "Clinical trial data must be referenced accurately.",
    }


def test_critique_validation(critique_valid: Dict[str, Any]) -> None:
    c = Critique(**critique_valid)
    assert c.violation is True
    assert c.article_id == "GCP.4"
    assert c.severity == LawSeverity.HIGH
    assert "referenced accurately" in c.reasoning


def test_critique_no_violation() -> None:
    c = Critique(
        violation=False,
        reasoning="All good.",
    )
    assert c.violation is False
    assert c.article_id is None
    # Default severity should be Low or irrelevant when no violation,
    # but the model defaults to LOW.
    assert c.severity == LawSeverity.LOW


def test_critique_missing_required() -> None:
    # "reasoning" is a required field. If missing, it should raise ValidationError.
    with pytest.raises(ValidationError):
        # We need to create a Critique missing 'reasoning'.
        # Since 'reasoning' is required, calling Critique(violation=True) is a type error in static analysis,
        # but at runtime pydantic raises ValidationError.
        Critique(violation=True)  # type: ignore[call-arg]


def test_trace_model() -> None:
    critique = Critique(violation=True, article_id="U1", severity=LawSeverity.CRITICAL, reasoning="Bad.")
    trace = ConstitutionalTrace(
        status=TraceStatus.REVISED,
        input_draft="Bad draft",
        critique=critique,
        revised_output="Good draft",
        delta="--- +++ diff",
    )
    assert trace.status == TraceStatus.REVISED
    assert trace.input_draft == "Bad draft"
    assert trace.critique.violation is True
    assert trace.delta == "--- +++ diff"


def test_trace_optional_delta() -> None:
    critique = Critique(violation=False, reasoning="Ok.")
    trace = ConstitutionalTrace(
        status=TraceStatus.APPROVED,
        input_draft="Good draft",
        critique=critique,
        revised_output="Good draft",
        # delta is optional
    )
    assert trace.status == TraceStatus.APPROVED
    assert trace.delta is None
