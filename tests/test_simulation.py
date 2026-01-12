import pytest
from pydantic import BaseModel

from coreason_constitution.schema import Critique, LawSeverity
from coreason_constitution.simulation import SimulatedLLMClient


@pytest.fixture  # type: ignore
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
