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

from coreason_constitution.schema import (
    ConstitutionalTrace,
    Critique,
    LawSeverity,
    TraceStatus,
)


@pytest.fixture  # type: ignore
def base_critique() -> Critique:
    return Critique(
        violation=True,
        article_id="TEST.1",
        severity=LawSeverity.HIGH,
        reasoning="Default reasoning.",
    )


def test_empty_strings_constraints() -> None:
    """Verify that empty strings raise ValidationError for required fields."""
    # Critique.reasoning
    with pytest.raises(ValidationError) as exc:
        Critique(violation=True, reasoning="")
    assert "String should have at least 1 character" in str(exc.value)

    # ConstitutionalTrace.input_draft
    critique = Critique(violation=False, reasoning="Ok.")
    with pytest.raises(ValidationError) as exc:
        ConstitutionalTrace(
            status=TraceStatus.APPROVED,
            input_draft="",  # Empty
            critique=critique,
            revised_output="Valid",
        )
    assert "String should have at least 1 character" in str(exc.value)

    # ConstitutionalTrace.revised_output
    with pytest.raises(ValidationError) as exc:
        ConstitutionalTrace(
            status=TraceStatus.APPROVED,
            input_draft="Valid",
            critique=critique,
            revised_output="",  # Empty
        )
    assert "String should have at least 1 character" in str(exc.value)

    # ConstitutionalTrace.delta (Optional but if present must be >=1 char)
    with pytest.raises(ValidationError) as exc:
        ConstitutionalTrace(
            status=TraceStatus.APPROVED,
            input_draft="Valid",
            critique=critique,
            revised_output="Valid",
            delta="",  # Empty explicitly
        )
    assert "String should have at least 1 character" in str(exc.value)


def test_unicode_handling() -> None:
    """Verify handling of Unicode characters (Emojis, Kanji, etc.)."""
    reasoning = "問題ない 🚀"
    critique = Critique(violation=False, reasoning=reasoning)
    assert critique.reasoning == reasoning

    draft = "User said: こんにちは world 🌍"
    trace = ConstitutionalTrace(
        status=TraceStatus.APPROVED,
        input_draft=draft,
        critique=critique,
        revised_output=draft,
    )
    assert trace.input_draft == draft
    json_out = trace.model_dump_json()
    assert "こんにちは" in json_out
    assert "🌍" in json_out


def test_large_payload(base_critique: Critique) -> None:
    """Verify handling of large string payloads (e.g., 100KB)."""
    large_text = "A" * 100_000  # 100KB
    trace = ConstitutionalTrace(
        status=TraceStatus.REVISED,
        input_draft=large_text,
        critique=base_critique,
        revised_output=large_text,
        delta=large_text,
    )
    assert len(trace.input_draft) == 100_000
    assert len(trace.delta or "") == 100_000

    # Sanity check serialization performance/crash
    dumped = trace.model_dump_json()
    assert len(dumped) > 200_000


def test_serialization_roundtrip(base_critique: Critique) -> None:
    """Verify full JSON serialization and deserialization roundtrip."""
    trace = ConstitutionalTrace(
        status=TraceStatus.REVISED,
        input_draft="Original text\nWith newline.",
        critique=base_critique,
        revised_output="Revised text\nWith newline.",
        delta="--- Original\n+++ Revised\n@@ -1 +1 @@\n-Original\n+Revised",
    )

    json_str = trace.model_dump_json()
    restored = ConstitutionalTrace.model_validate_json(json_str)

    assert restored.status == TraceStatus.REVISED
    assert restored.input_draft == trace.input_draft
    assert restored.critique.violation == trace.critique.violation
    assert restored.critique.severity == trace.critique.severity
    assert restored.delta == trace.delta


def test_critique_permissive_consistency() -> None:
    """
    Verify that the model allows violation=True without an article_id.
    This is an 'edge case' where the Judge might fail to cite a law,
    but we still want to capture the violation signal.
    """
    c = Critique(
        violation=True,
        article_id=None,  # Missing ID
        reasoning="Something bad happened but I don't know which law.",
    )
    assert c.violation is True
    assert c.article_id is None
