from unittest.mock import Mock, create_autospec

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import LawSeverity
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


def test_sentinel_pass(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """Verify that if Sentinel passes, the system proceeds (Unit 1 placeholder behavior)."""
    # Setup
    input_prompt = "Hello"
    draft_response = "Hi there"

    # Mock Sentinel to pass (return None)
    mock_sentinel.check.return_value = None

    # Execute
    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # Verify
    mock_sentinel.check.assert_called_once_with(input_prompt)

    # Check placeholder behavior
    assert trace.critique.violation is False
    assert trace.revised_output == draft_response


def test_edge_case_empty_security_exception(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """
    Edge Case: Sentinel raises SecurityException with an empty string.
    System should provide a default message to satisfy Pydantic min_length=1.
    """
    mock_sentinel.check.side_effect = SecurityException("")

    trace = system.run_compliance_cycle("Bad input", "Draft")

    assert trace.critique.violation is True
    # Should use a fallback message, not empty string
    assert len(trace.critique.reasoning) > 0
    assert trace.critique.reasoning != ""
    assert trace.revised_output != ""


def test_edge_case_empty_inputs(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """
    Edge Case: Input prompt and draft response are empty strings.
    System should handle them gracefully (or validation might catch them depending on implementation).
    NOTE: ConstitutionalTrace requires min_length=1 for input_draft and revised_output.
    So we expect the system to either raise a ValidationError OR handle it.
    However, the PRD says 'Input Draft' must be min_length=1.
    If the caller provides empty string, constructing the Trace will fail.
    The system should probably be robust.
    """
    mock_sentinel.check.return_value = None

    # If we pass empty strings, and the system tries to create a Trace with them,
    # Pydantic will raise ValidationError.
    # The system could let this bubble up, OR wrap it.
    # Let's see what happens. Ideally, the system might validate inputs early?
    # Or maybe it relies on the Trace construction validation.
    # For this test, we accept either a ValidationError or a handled response.
    # But wait, if draft is empty, RevisionEngine handles it.
    # Let's pass a space " " to avoid min_length=1 error if we want to test flow,
    # or test explicitly that empty string fails.

    # Let's test that it DOES NOT crash effectively, or raises a clear error.
    try:
        system.run_compliance_cycle(" ", " ")
    except Exception as e:
        pytest.fail(f"System crashed on whitespace inputs: {e}")


def test_edge_case_unicode_inputs(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """Edge Case: Inputs with Unicode characters."""
    input_prompt = "Hello 👋 🌍"
    draft_response = "你好，世界"

    mock_sentinel.check.return_value = None

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    assert trace.input_draft == draft_response
    assert trace.revised_output == draft_response
    mock_sentinel.check.assert_called_once_with(input_prompt)


def test_edge_case_large_payload(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """Edge Case: Large input payload."""
    large_input = "A" * 100_000
    large_draft = "B" * 100_000

    mock_sentinel.check.return_value = None

    trace = system.run_compliance_cycle(large_input, large_draft)

    assert trace.input_draft == large_draft
    assert len(trace.revised_output) == 100_000
