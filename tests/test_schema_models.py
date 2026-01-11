from typing import Any, Dict

import pytest
from pydantic import ValidationError

from coreason_constitution.schema import ConstitutionalTrace, Critique, LawSeverity


@pytest.fixture  # type: ignore[misc]
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
        input_draft="Bad draft",
        critique=critique,
        revised_output="Good draft",
        delta="--- +++ diff",
    )
    assert trace.input_draft == "Bad draft"
    assert trace.critique.violation is True
    assert trace.delta == "--- +++ diff"


def test_trace_optional_delta() -> None:
    critique = Critique(violation=False, reasoning="Ok.")
    trace = ConstitutionalTrace(
        input_draft="Good draft",
        critique=critique,
        revised_output="Good draft",
        # delta is optional
    )
    assert trace.delta is None
