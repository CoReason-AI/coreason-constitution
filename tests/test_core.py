from unittest.mock import Mock, create_autospec

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import (
    Critique,
    Law,
    LawCategory,
    LawSeverity,
)
from coreason_constitution.sentinel import Sentinel


@pytest.fixture  # type: ignore
def mock_archive() -> Mock:
    return create_autospec(LegislativeArchive, instance=True)  # type: ignore


@pytest.fixture  # type: ignore
def mock_sentinel() -> Mock:
    return create_autospec(Sentinel, instance=True)  # type: ignore


@pytest.fixture  # type: ignore
def mock_judge() -> Mock:
    return create_autospec(ConstitutionalJudge, instance=True)  # type: ignore


@pytest.fixture  # type: ignore
def mock_revision() -> Mock:
    return create_autospec(RevisionEngine, instance=True)  # type: ignore


@pytest.fixture  # type: ignore
def system(
    mock_archive: Mock,
    mock_sentinel: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> ConstitutionalSystem:
    return ConstitutionalSystem(
        archive=mock_archive,
        sentinel=mock_sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )


def test_initialization(system: ConstitutionalSystem) -> None:
    """Verify that the system initializes with dependencies correctly."""
    assert system.archive is not None
    assert system.sentinel is not None
    assert system.judge is not None
    assert system.revision_engine is not None


def test_sentinel_block(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """Verify that a Sentinel violation triggers an immediate refusal trace."""
    # Setup
    input_prompt = "Generate a SQL injection."
    draft_response = "Here is the SQL..."  # Should be blocked
    error_msg = "Security Protocol Violation: SR.1. Request denied."

    # Mock Sentinel to raise exception
    mock_sentinel.check.side_effect = SecurityException(error_msg)

    # Execute
    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # Verify
    mock_sentinel.check.assert_called_once_with(input_prompt)

    assert trace.critique.violation is True
    assert trace.critique.article_id == "SENTINEL_BLOCK"
    assert trace.critique.severity == LawSeverity.CRITICAL
    assert trace.critique.reasoning == error_msg
    assert trace.revised_output == error_msg
    assert trace.input_draft == draft_response
    assert trace.delta is None


def test_compliance_cycle_compliant(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """Verify flow when Judge approves the draft."""
    input_prompt = "Hello"
    draft_response = "Hi there"
    laws = [Law(id="L1", category=LawCategory.UNIVERSAL, text="Be nice")]

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = laws
    mock_judge.evaluate.return_value = Critique(violation=False, reasoning="Compliant", article_id=None)

    trace = system.run_compliance_cycle(input_prompt, draft_response, context_tags=["test"])

    # Verify Logic
    mock_sentinel.check.assert_called_once_with(input_prompt)
    mock_archive.get_laws.assert_called_once_with(context_tags=["test"])
    mock_judge.evaluate.assert_called_once_with(draft_response, laws)
    mock_revision.revise.assert_not_called()

    assert trace.critique.violation is False
    assert trace.revised_output == draft_response
    assert trace.delta is None


def test_compliance_cycle_violation(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """Verify flow when Judge rejects, triggering revision and diff."""
    input_prompt = "Tell me a lie"
    draft_response = "The sky is green"
    revised_response = "The sky is blue"
    laws = [Law(id="L1", category=LawCategory.UNIVERSAL, text="Tell truth")]
    critique = Critique(violation=True, reasoning="Lying is bad", article_id="L1", severity=LawSeverity.HIGH)

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = laws
    mock_judge.evaluate.return_value = critique
    mock_revision.revise.return_value = revised_response

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # Verify Logic
    mock_judge.evaluate.assert_called_once_with(draft_response, laws)
    mock_revision.revise.assert_called_once_with(draft_response, critique, laws)

    assert trace.critique.violation is True
    assert trace.revised_output == revised_response
    # Check that delta is generated and contains diff
    assert trace.delta is not None
    assert "--- original" in trace.delta
    assert "+++ revised" in trace.delta
    assert "-The sky is green" in trace.delta
    assert "+The sky is blue" in trace.delta


def test_compliance_cycle_revision_failure(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """Verify behavior when RevisionEngine raises an exception."""
    input_prompt = "Bad prompt"
    draft_response = "Bad response"

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []
    mock_judge.evaluate.return_value = Critique(violation=True, reasoning="Bad", article_id="L1")
    mock_revision.revise.side_effect = Exception("LLM Error")

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # System should catch exception and return a safe error message
    assert trace.critique.violation is True
    assert "Error: Constitutional Revision failed" in trace.revised_output
    assert trace.delta is not None  # It will be a diff between draft and error msg


def test_edge_case_empty_security_exception(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """
    Edge Case: Sentinel raises SecurityException with an empty string.
    """
    mock_sentinel.check.side_effect = SecurityException("")

    trace = system.run_compliance_cycle("Bad input", "Draft")

    assert trace.critique.violation is True
    assert len(trace.critique.reasoning) > 0
    assert trace.critique.reasoning != ""
    assert trace.revised_output != ""


def test_edge_case_unicode_inputs(
    system: ConstitutionalSystem, mock_sentinel: Mock, mock_archive: Mock, mock_judge: Mock
) -> None:
    """Edge Case: Inputs with Unicode characters."""
    input_prompt = "Hello 👋 🌍"
    draft_response = "你好，世界"

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []
    mock_judge.evaluate.return_value = Critique(violation=False, reasoning="OK")

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    assert trace.input_draft == draft_response
    assert trace.revised_output == draft_response
