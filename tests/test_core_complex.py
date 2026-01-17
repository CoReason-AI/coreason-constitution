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

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import (
    Critique,
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


def test_oscillation_failure(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Scenario: The revision fixes one violation but creates another, oscillating between them.
    The system should eventually exhaust max_retries and fail closed.
    """
    input_prompt = "Make a plan"
    draft_response = "Plan A"

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []

    # Sequence of Judge responses:
    # 1. Initial: Violation A
    # 2. Iter 1 Check: Violation B (Fixed A, broke B)
    # 3. Iter 2 Check: Violation A (Fixed B, broke A)
    # 4. Iter 3 Check: Violation B (Fixed A, broke B) -> Max retries hit

    critique_A = Critique(violation=True, reasoning="Violates A", article_id="A", severity=LawSeverity.HIGH)
    critique_B = Critique(violation=True, reasoning="Violates B", article_id="B", severity=LawSeverity.HIGH)

    mock_judge.evaluate.side_effect = [critique_A, critique_B, critique_A, critique_B]

    # Revisions just return dummy strings
    mock_revision.revise.side_effect = ["Draft B", "Draft A", "Draft B"]

    trace = system.run_compliance_cycle(input_prompt, draft_response, max_retries=3)

    assert trace.status == TraceStatus.BLOCKED
    assert trace.critique.violation is True
    assert trace.critique.article_id == "A"  # Should preserve INITIAL violation
    assert "Safety Protocol Exception" in trace.revised_output
    assert len(trace.history) == 3


def test_max_retries_zero(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
) -> None:
    """
    Scenario: max_retries is set to 0. System should immediately refuse if initial violation detected.
    """
    input_prompt = "Test"
    draft_response = "Bad"

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []

    mock_judge.evaluate.return_value = Critique(violation=True, reasoning="Bad", article_id="L1")

    trace = system.run_compliance_cycle(input_prompt, draft_response, max_retries=0)

    assert trace.status == TraceStatus.BLOCKED
    assert trace.critique.violation is True
    assert "Safety Protocol Exception" in trace.revised_output
    assert len(trace.history) == 0


def test_empty_revision_handling(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Scenario: RevisionEngine returns an empty string.
    System should catch this before TraceIteration validation and fail closed.
    """
    input_prompt = "Test"
    draft_response = "Bad"

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []

    mock_judge.evaluate.return_value = Critique(violation=True, reasoning="Bad", article_id="L1")
    mock_revision.revise.return_value = ""  # Empty string

    trace = system.run_compliance_cycle(input_prompt, draft_response)

    assert trace.status == TraceStatus.BLOCKED
    assert trace.critique.violation is True
    assert "Safety Protocol Exception" in trace.revised_output
    # It fails on the first attempt, so history should be empty or maybe partial?
    # In my implementation, I break BEFORE creating TraceIteration.
    assert len(trace.history) == 0


def test_trace_history_fidelity(
    system: ConstitutionalSystem,
    mock_sentinel: Mock,
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Verify that history correctly records the inputs and outputs of each step.
    """
    input_prompt = "Test"
    draft_response = "Draft 0"

    mock_sentinel.check.return_value = None
    mock_archive.get_laws.return_value = []

    # 1. Initial: Violation
    # 2. Iter 1: Violation
    # 3. Iter 2: Compliant
    c1 = Critique(violation=True, reasoning="V1", article_id="L1")
    c2 = Critique(violation=True, reasoning="V2", article_id="L1")
    c3 = Critique(violation=False, reasoning="OK", article_id=None)

    mock_judge.evaluate.side_effect = [c1, c2, c3]

    mock_revision.revise.side_effect = ["Draft 1", "Draft 2"]

    trace = system.run_compliance_cycle(input_prompt, draft_response, max_retries=5)

    assert trace.status == TraceStatus.REVISED
    assert trace.revised_output == "Draft 2"
    assert len(trace.history) == 2

    # Check Iteration 1
    assert trace.history[0].input_draft == "Draft 0"
    assert trace.history[0].critique == c1
    assert trace.history[0].revised_output == "Draft 1"

    # Check Iteration 2
    assert trace.history[1].input_draft == "Draft 1"
    assert trace.history[1].critique == c2
    assert trace.history[1].revised_output == "Draft 2"
