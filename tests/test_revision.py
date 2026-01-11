from typing import Any, Dict, List, Type
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from coreason_constitution.interfaces import LLMClient
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import Critique, Law, LawCategory, LawSeverity


class MockLLMClient(LLMClient):
    def __init__(self, response: str = "Revised content"):
        self.response = response
        self.calls: List[Dict[str, Any]] = []

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        self.calls.append({"messages": messages, "model": model, "temperature": temperature})
        return self.response

    def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[BaseModel],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> Any:
        pass  # Not used in RevisionEngine


@pytest.fixture  # type: ignore
def mock_client() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture  # type: ignore
def revision_engine(mock_client: MockLLMClient) -> RevisionEngine:
    return RevisionEngine(llm_client=mock_client)


@pytest.fixture  # type: ignore
def sample_law() -> Law:
    return Law(
        id="GCP.1", category=LawCategory.DOMAIN, text="Do not hallucinate clinical data.", severity=LawSeverity.HIGH
    )


def test_revision_engine_initialization(revision_engine: RevisionEngine) -> None:
    assert revision_engine.model == "gpt-4"


def test_revise_no_violation(revision_engine: RevisionEngine, sample_law: Law) -> None:
    draft = "Valid content"
    critique = Critique(violation=False, reasoning="All good")

    result = revision_engine.revise(draft, critique, [sample_law])

    assert result == draft
    assert len(revision_engine.client.calls) == 0  # type: ignore


def test_revise_empty_draft(revision_engine: RevisionEngine, sample_law: Law) -> None:
    draft = ""
    critique = Critique(violation=True, article_id="GCP.1", reasoning="Bad")

    result = revision_engine.revise(draft, critique, [sample_law])

    assert result == ""
    assert len(revision_engine.client.calls) == 0  # type: ignore


def test_revise_with_violation(revision_engine: RevisionEngine, sample_law: Law) -> None:
    draft = "I think the dose should be 50mg."
    critique = Critique(
        violation=True, article_id="GCP.1", severity=LawSeverity.HIGH, reasoning="Speculation without evidence."
    )

    revision_engine.client.response = "According to data..."  # type: ignore

    result = revision_engine.revise(draft, critique, [sample_law])

    assert result == "According to data..."

    # Verify prompt construction
    calls = revision_engine.client.calls  # type: ignore
    assert len(calls) == 1
    messages = calls[0]["messages"]
    user_content = messages[1]["content"]

    assert "--- ORIGINAL DRAFT ---" in user_content
    assert draft in user_content
    assert "--- CRITIQUE ---" in user_content
    assert "Speculation without evidence." in user_content
    assert "--- VIOLATED LAW ---" in user_content
    assert "GCP.1: Do not hallucinate clinical data." in user_content


def test_revise_unknown_law(revision_engine: RevisionEngine) -> None:
    draft = "Bad stuff"
    critique = Critique(violation=True, article_id="UNKNOWN.1", reasoning="Something wrong")

    _ = revision_engine.revise(draft, critique, [])

    calls = revision_engine.client.calls  # type: ignore
    user_content = calls[0]["messages"][1]["content"]

    assert "Law ID UNKNOWN.1 (Text not found in provided context)" in user_content


def test_revise_llm_failure(revision_engine: RevisionEngine, sample_law: Law) -> None:
    draft = "Draft"
    critique = Critique(violation=True, article_id="GCP.1", reasoning="Bad")

    # Mock exception
    revision_engine.client.chat_completion = MagicMock(side_effect=RuntimeError("LLM Error"))  # type: ignore

    with pytest.raises(RuntimeError):
        revision_engine.revise(draft, critique, [sample_law])
