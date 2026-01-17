# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from typing import List

import pytest

from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.schema import Critique, Law, LawCategory, LawSeverity
from tests.mocks import MockLLMClient


@pytest.fixture  # type: ignore
def mock_client() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture  # type: ignore
def basic_laws() -> List[Law]:
    return [
        Law(id="U.1", category=LawCategory.UNIVERSAL, text="Do not generate hate speech."),
        Law(id="U.2", category=LawCategory.UNIVERSAL, text="Do not reveal PII."),
    ]


def test_judge_initialization(mock_client: MockLLMClient) -> None:
    judge = ConstitutionalJudge(mock_client)
    assert judge.client == mock_client
    assert judge.model == "gpt-4"


def test_evaluate_compliant_content(mock_client: MockLLMClient, basic_laws: List[Law]) -> None:
    # Setup mock for compliant response
    compliant_critique = Critique(
        violation=False,
        reasoning="Content is safe.",
    )
    # We trigger the mock based on content
    mock_client.set_structured_response("Hello world", compliant_critique)

    judge = ConstitutionalJudge(mock_client)
    result = judge.evaluate("Hello world", basic_laws)

    assert result.violation is False
    assert result.reasoning == "Content is safe."
    assert mock_client.call_count == 1

    # Check that laws were injected into prompt
    last_msg = mock_client.last_messages[1]["content"]
    assert "U.1" in last_msg
    assert "Do not generate hate speech" in last_msg


def test_evaluate_violation(mock_client: MockLLMClient, basic_laws: List[Law]) -> None:
    # Setup mock for violation
    violation_critique = Critique(
        violation=True,
        article_id="U.1",
        severity=LawSeverity.HIGH,
        reasoning="Hate speech detected.",
    )
    mock_client.set_structured_response("bad content", violation_critique)

    judge = ConstitutionalJudge(mock_client)
    result = judge.evaluate("This is bad content", basic_laws)

    assert result.violation is True
    assert result.article_id == "U.1"
    assert result.severity == LawSeverity.HIGH


def test_evaluate_empty_draft(mock_client: MockLLMClient, basic_laws: List[Law]) -> None:
    judge = ConstitutionalJudge(mock_client)
    result = judge.evaluate("   ", basic_laws)

    # Should short-circuit without calling LLM
    assert result.violation is False
    assert "empty" in result.reasoning.lower()
    assert mock_client.call_count == 0


def test_evaluate_no_laws(mock_client: MockLLMClient) -> None:
    judge = ConstitutionalJudge(mock_client)
    result = judge.evaluate("content", [])

    # Should short-circuit
    assert result.violation is False
    assert "no laws" in result.reasoning.lower()
    assert mock_client.call_count == 0


def test_llm_failure_handling(mock_client: MockLLMClient, basic_laws: List[Law]) -> None:
    # Force the mock to raise an exception by providing a trigger with no response set
    # (MockLLMClient implementation tries to instantiate response_model, which works for Critique
    # IF we don't supply args, but Critique needs args. So it might raise Validation Error or similar)

    # Actually, MockLLMClient default implementation:
    # "try: return response_model()" -> Critique needs fields, so this raises ValidationError.
    # The Judge catches Exception and returns a SYSTEM_ERROR critique.

    judge = ConstitutionalJudge(mock_client)
    result = judge.evaluate("unmocked trigger", basic_laws)

    assert result.violation is True
    assert result.article_id == "SYSTEM_ERROR"
    assert "System Error" in result.reasoning


def test_evaluate_large_payload(mock_client: MockLLMClient, basic_laws: List[Law]) -> None:
    judge = ConstitutionalJudge(mock_client)
    large_text = "word " * 5000

    expected = Critique(violation=False, reasoning="Ok")
    mock_client.set_structured_response("word", expected)

    result = judge.evaluate(large_text, basic_laws)
    assert result.violation is False
    assert mock_client.call_count == 1


def test_missing_article_id_fix(mock_client: MockLLMClient, basic_laws: List[Law]) -> None:
    # Test the case where violation=True but article_id is None
    # We construct a Critique manually that is valid Pydantic-wise (article_id optional)
    # but logically incomplete for our application logic.
    flawed_critique = Critique(violation=True, article_id=None, reasoning="Bad stuff", severity=LawSeverity.HIGH)

    mock_client.set_structured_response("flawed", flawed_critique)

    judge = ConstitutionalJudge(mock_client)
    result = judge.evaluate("flawed content", basic_laws)

    assert result.violation is True
    assert result.article_id == "UNKNOWN"
