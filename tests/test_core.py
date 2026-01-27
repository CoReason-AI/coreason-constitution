from typing import Any

# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution
from unittest.mock import Mock, create_autospec

import pytest
from coreason_identity.models import UserContext

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
    TraceStatus,
)
from coreason_constitution.sentinel import Sentinel


@pytest.fixture  # type: ignore
def mock_archive() -> Any:
    return create_autospec(LegislativeArchive, instance=True)


@pytest.fixture  # type: ignore
def mock_sentinel() -> Any:
    return create_autospec(Sentinel, instance=True)


@pytest.fixture  # type: ignore
def mock_judge() -> Any:
    return create_autospec(ConstitutionalJudge, instance=True)


@pytest.fixture  # type: ignore
def mock_revision() -> Any:
    return create_autospec(RevisionEngine, instance=True)


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
    mock_sentinel.check.assert_called_once_with(input_prompt, user_context=None)

    assert trace.status == TraceStatus.BLOCKED
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
    mock_archive.get_references.return_value = []
    mock_judge.evaluate.return_value = Critique(violation=False, reasoning="Compliant", article_id=None)

    trace = system.run_compliance_cycle(input_prompt, draft_response, context_tags=["test"])

    # Verify Logic
    mock_sentinel.check.assert_called_once_with(input_prompt, user_context=None)
    mock_archive.get_laws.assert_called_once_with(context_tags=["test"])
    mock_judge.evaluate.assert_called_once_with(draft_response, laws, [], user_context=None)
    mock_revision.revise.assert_not_called()

    assert trace.status == TraceStatus.APPROVED
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

    critique_1 = Critique(violation=True, reasoning="Lying is bad", article_id="L1", severity=LawSeverity.HIGH)
    critique_2 = Critique(violation=False, reasoning="Good", article_id=None)

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = laws

    # Judge call 1: Violation
    # Judge call 2: Compliant
    mock_judge.evaluate.side_effect = [critique_1, critique_2]

    mock_revision.revise.return_value = revised_response

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # Verify Logic
    # Judge called twice: initial, then post-revision
    assert mock_judge.evaluate.call_count == 2
    mock_revision.revise.assert_called_once_with(draft_response, critique_1, laws)

    assert trace.status == TraceStatus.REVISED
    assert trace.critique.violation is True
    assert trace.revised_output == revised_response
    # Check that delta is generated and contains diff
    assert trace.delta is not None
    assert "--- original" in trace.delta
    assert "+++ revised" in trace.delta
    assert "-The sky is green" in trace.delta
    assert "+The sky is blue" in trace.delta

    # Verify History
    assert len(trace.history) == 1
    assert trace.history[0].input_draft == draft_response
    assert trace.history[0].revised_output == revised_response


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
    assert trace.status == TraceStatus.BLOCKED
    assert trace.critique.violation is True
    assert "Safety Protocol Exception" in trace.revised_output
    assert trace.delta is None  # Hard refusal = no diff


def test_edge_case_empty_security_exception(system: ConstitutionalSystem, mock_sentinel: Mock) -> None:
    """
    Edge Case: Sentinel raises SecurityException with an empty string.
    """
    mock_sentinel.check.side_effect = SecurityException("")

    trace = system.run_compliance_cycle("Bad input", "Draft")

    assert trace.status == TraceStatus.BLOCKED
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

    assert trace.status == TraceStatus.APPROVED
    assert trace.input_draft == draft_response
    assert trace.revised_output == draft_response


def test_compliance_cycle_complex_context_filtering(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
) -> None:
    """
    Verify that context tags are correctly passed to LegislativeArchive,
    and the resulting subset of laws is passed to the Judge.
    """
    input_prompt = "Test"
    draft_response = "Draft"
    context_tags = ["tenant:A", "region:EU"]

    # Setup: Archive returns a specific subset of laws
    filtered_laws = [Law(id="GCP.1", category=LawCategory.DOMAIN, text="GCP Rule", tags=["region:EU"])]
    mock_archive.get_laws.return_value = filtered_laws
    mock_archive.get_references.return_value = []
    mock_sentinel.check.return_value = None
    mock_judge.evaluate.return_value = Critique(violation=False, reasoning="OK")

    system.run_compliance_cycle(input_prompt, draft_response, context_tags=context_tags)

    # Verify correct tags passed to Archive
    mock_archive.get_laws.assert_called_once_with(context_tags=context_tags)
    # Verify the filtered laws (and ONLY them) passed to Judge
    mock_judge.evaluate.assert_called_once_with(draft_response, filtered_laws, [], user_context=None)


def test_compliance_cycle_max_retries_exceeded(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Verify that if RevisionEngine keeps failing (loop exhaustion),
    the system returns a Hard Refusal.
    """
    input_prompt = "Maybe bad"
    draft_response = "Dubious content"
    laws: list[Law] = []

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = laws

    # Judge ALWAYS says violation
    violation = Critique(violation=True, reasoning="Still bad", article_id="L2")
    mock_judge.evaluate.return_value = violation

    # Revision returns "Tried my best" but Judge still rejects it
    mock_revision.revise.return_value = "Tried my best"

    trace = system.run_compliance_cycle(input_prompt, draft_response, max_retries=3)

    assert trace.status == TraceStatus.BLOCKED
    assert trace.critique.violation is True
    assert "Safety Protocol Exception" in trace.revised_output
    assert trace.delta is None

    # Judge called: 1 (Initial) + 3 (Loops) = 4
    assert mock_judge.evaluate.call_count == 4
    # Revision called: 3 times
    assert mock_revision.revise.call_count == 3
    # History length: 3
    assert len(trace.history) == 3


def test_compliance_cycle_judge_hallucinated_id(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Verify system robustness when Judge cites a Law ID that doesn't exist in the provided laws.
    """
    input_prompt = "Test"
    draft_response = "Draft"
    laws = [Law(id="EXISTING.1", category=LawCategory.UNIVERSAL, text="Real Law")]

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = laws

    # Judge returns unknown ID
    critique_1 = Critique(violation=True, reasoning="Violation", article_id="HALLUCINATED.99")
    critique_2 = Critique(violation=False, reasoning="Fixed", article_id=None)

    mock_judge.evaluate.side_effect = [critique_1, critique_2]
    mock_revision.revise.return_value = "Revised"

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # Verify laws and critique passed to RevisionEngine
    mock_revision.revise.assert_called_once()
    call_args = mock_revision.revise.call_args
    # args: (draft, critique, laws)
    assert call_args[0][1].article_id == "HALLUCINATED.99"
    assert call_args[0][2] == laws

    assert trace.revised_output == "Revised"


def test_archive_failure_propagates(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
) -> None:
    """
    Verify that if LegislativeArchive raises an exception (e.g. database/disk error),
    it propagates up (fail-closed / system error) rather than being swallowed.
    """
    mock_sentinel.check.return_value = None
    mock_archive.get_laws.side_effect = ValueError("Corrupt Archive")

    with pytest.raises(ValueError, match="Corrupt Archive"):
        system.run_compliance_cycle("Input", "Draft")


def test_compliance_cycle_with_user_context(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
) -> None:
    """Verify that user_context is passed down to Sentinel and Judge."""
    input_prompt = "Prompt"
    draft_response = "Draft"
    user_context = UserContext(user_id="u1", email="u1@example.com", groups=["admin"])

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []
    mock_archive.get_references.return_value = []
    mock_judge.evaluate.return_value = Critique(violation=False, reasoning="OK")

    system.run_compliance_cycle(input_prompt, draft_response, user_context=user_context)

    mock_sentinel.check.assert_called_once_with(input_prompt, user_context=user_context)
    mock_judge.evaluate.assert_called_once_with(draft_response, [], [], user_context=user_context)
