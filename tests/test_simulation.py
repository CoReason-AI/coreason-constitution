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
from pydantic import BaseModel

from coreason_constitution.schema import Critique, LawSeverity
from coreason_constitution.simulation import SimulatedLLMClient


@pytest.fixture
def client() -> SimulatedLLMClient:
    return SimulatedLLMClient()


def test_judge_story_a_gxp(client: SimulatedLLMClient) -> None:
    """Test Story A (GxP) trigger for Judge."""
    messages = [{"role": "user", "content": "I have a hunch we should increase the dosage."}]
    critique = client.structured_output(messages, Critique, model="test")

    assert critique.violation is True
    assert critique.article_id == "GCP.4"
    assert critique.severity == LawSeverity.HIGH
    assert "hunch" in critique.reasoning


def test_judge_story_c_citation(client: SimulatedLLMClient) -> None:
    """Test Story C (Citation) trigger for Judge."""
    messages = [{"role": "user", "content": "As seen in Study NCT99999, results are promising."}]
    critique = client.structured_output(messages, Critique, model="test")

    assert critique.violation is True
    assert critique.article_id == "REF.1"
    assert critique.severity == LawSeverity.MEDIUM
    assert "NCT99999" in critique.reasoning


def test_judge_happy_path(client: SimulatedLLMClient) -> None:
    """Test safe default for Judge."""
    messages = [{"role": "user", "content": "The sky is blue."}]
    critique = client.structured_output(messages, Critique, model="test")

    assert critique.violation is False
    assert critique.article_id is None


def test_judge_invalid_model(client: SimulatedLLMClient) -> None:
    """Test error raised when non-Critique model is requested."""

    class OtherModel(BaseModel):
        field: str

    messages = [{"role": "user", "content": "test"}]
    with pytest.raises(NotImplementedError):
        client.structured_output(messages, OtherModel, model="test")


def test_revisor_story_a_gxp(client: SimulatedLLMClient) -> None:
    """Test Story A (GxP) trigger for Revisor."""
    messages = [{"role": "user", "content": "--- ORIGINAL DRAFT ---\nI have a hunch...\n\n--- CRITIQUE ---\n..."}]
    revision = client.chat_completion(messages, model="test")

    assert "dosage change is not supported without further trial evidence" in revision


def test_revisor_story_c_citation(client: SimulatedLLMClient) -> None:
    """Test Story C (Citation) trigger for Revisor."""
    messages = [{"role": "user", "content": "--- ORIGINAL DRAFT ---\nStudy NCT99999...\n\n--- CRITIQUE ---\n..."}]
    revision = client.chat_completion(messages, model="test")

    assert "citation needed" in revision


def test_revisor_fallback_extraction(client: SimulatedLLMClient) -> None:
    """Test fallback mechanism extracts original draft if no trigger found."""
    draft_text = "This is a safe draft."
    messages = [{"role": "user", "content": f"--- ORIGINAL DRAFT ---\n{draft_text}\n\n--- CRITIQUE ---\n..."}]
    revision = client.chat_completion(messages, model="test")

    assert revision == draft_text


def test_revisor_fallback_extraction_failure(client: SimulatedLLMClient) -> None:
    """Test fallback returns generic message if extraction fails or format is weird."""
    # Case where header exists but structure is broken (e.g., no CRITIQUE section)
    messages = [{"role": "user", "content": "--- ORIGINAL DRAFT ---\nBroken content without critique section"}]
    revision = client.chat_completion(messages, model="test")

    # It should fall through to the generic message because '--- CRITIQUE ---' is missing
    assert revision == "Simulated Revision: Content revised for compliance."


# --- Edge Cases & Complex Scenarios ---


def test_trigger_case_insensitivity(client: SimulatedLLMClient) -> None:
    """Test that 'HUNCH' triggers Story A just like 'hunch'."""
    messages = [{"role": "user", "content": "I have a HUGE HUNCH about this."}]
    critique = client.structured_output(messages, Critique, model="test")

    assert critique.violation is True
    assert critique.article_id == "GCP.4"


def test_trigger_precedence(client: SimulatedLLMClient) -> None:
    """
    Test behavior when multiple triggers are present.
    Current implementation checks 'hunch' first.
    """
    messages = [{"role": "user", "content": "I have a hunch about Study NCT99999."}]
    critique = client.structured_output(messages, Critique, model="test")

    # Should trigger the first one checked (GCP.4 / Hunch)
    assert critique.violation is True
    assert critique.article_id == "GCP.4"


def test_extraction_markers_swapped(client: SimulatedLLMClient) -> None:
    """Test fallback when CRITIQUE marker appears before ORIGINAL DRAFT marker."""
    # This results in end < start, so slicing [start:end] returns empty string.
    # The code checks start != -1 and end != -1.
    messages = [{"role": "user", "content": "--- CRITIQUE ---\n...\n\n--- ORIGINAL DRAFT ---\nSome draft"}]
    revision = client.chat_completion(messages, model="test")

    # Since slicing returns empty string, it might return empty string or fall through?
    # Actually, if it returns empty string, the code returns it.
    # Let's verify what we expect.
    # Ideally it falls back to generic message if extraction yields nothing useful?
    # But current code returns `user_content[start:end].strip()`.
    # If end < start, result is "".
    # Empty string is returned.
    assert revision == ""


def test_missing_user_role(client: SimulatedLLMClient) -> None:
    """Test behavior when no user message is present."""
    messages = [{"role": "system", "content": "System prompt only"}]
    critique = client.structured_output(messages, Critique, model="test")

    # Should extract empty string -> No trigger -> Happy Path
    assert critique.violation is False


def test_complex_full_compliance_cycle(client: SimulatedLLMClient) -> None:
    """
    Simulate a full Judge -> Revisor -> Judge cycle for Story A.
    1. Judge flags 'hunch'.
    2. Revisor fixes it (removes 'hunch').
    3. Judge evaluates fixed text (no 'hunch') -> Compliant.
    """
    # 1. Initial Draft
    draft = "I have a hunch regarding the dosage."
    messages_1 = [{"role": "user", "content": draft}]

    critique_1 = client.structured_output(messages_1, Critique, model="test")
    assert critique_1.violation is True
    assert critique_1.article_id == "GCP.4"

    # 2. Revision
    # Construct prompt like RevisionEngine does
    revision_prompt = f"--- ORIGINAL DRAFT ---\n{draft}\n\n--- CRITIQUE ---\n{critique_1.model_dump_json()}"
    messages_2 = [{"role": "user", "content": revision_prompt}]

    revised_text = client.chat_completion(messages_2, model="test")
    # Verify the simulated revisor replaced the content
    assert "dosage change is not supported" in revised_text
    assert "hunch" not in revised_text.lower()

    # 3. Final Judge Check
    messages_3 = [{"role": "user", "content": revised_text}]
    critique_2 = client.structured_output(messages_3, Critique, model="test")

    # Should be compliant now because 'hunch' is gone
    assert critique_2.violation is False
    assert critique_2.article_id is None
