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
