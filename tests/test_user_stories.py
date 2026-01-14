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
    Law,
    LawCategory,
    LawSeverity,
    SentinelRule,
    TraceStatus,
)
from coreason_constitution.sentinel import Sentinel


@pytest.fixture  # type: ignore
def mock_archive() -> Mock:
    return create_autospec(LegislativeArchive, instance=True)  # type: ignore


@pytest.fixture  # type: ignore
def mock_judge() -> Mock:
    return create_autospec(ConstitutionalJudge, instance=True)  # type: ignore


@pytest.fixture  # type: ignore
def mock_revision() -> Mock:
    return create_autospec(RevisionEngine, instance=True)  # type: ignore


def test_story_a_active_correction(
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Story A: The "Active Correction" (GxP Compliance)
    Trigger: cortex drafts a response recommending a dosage change based on a "hunch."
    Critique: The Judge scans the draft against "Article 4: Evidence-Based Claims." It flags the "hunch" as a violation.
    Revision: The Revision Engine rewrites the paragraph...
    Result: User sees a compliant, safe answer.
    """
    # 1. Setup Components
    # We use a real Sentinel for completeness, though irrelevant for this story (no red lines)
    sentinel = Sentinel(rules=[])

    system = ConstitutionalSystem(
        archive=mock_archive,
        sentinel=sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )

    # 2. Setup Data
    input_prompt = "What dosage should we give?"
    draft_response = "I have a hunch we should double the dosage."

    # Law definition
    gxp_law = Law(
        id="Article 4",
        category=LawCategory.DOMAIN,
        text="All clinical recommendations must be based on evidence, not speculation.",
        severity=LawSeverity.HIGH,
    )
    mock_archive.get_laws.return_value = [gxp_law]

    # 3. Setup Mocks Sequence
    # First Evaluation: Violation
    critique_fail = Critique(
        violation=True,
        article_id="Article 4",
        severity=LawSeverity.HIGH,
        reasoning="The draft relies on a 'hunch' which violates Article 4.",
    )

    # Second Evaluation (after revision): Compliant
    critique_pass = Critique(violation=False, reasoning="Compliant.", article_id=None)

    mock_judge.evaluate.side_effect = [critique_fail, critique_pass]

    # Revision
    revised_text = "Based on current data, a dosage change is not supported without further trial evidence."
    mock_revision.revise.return_value = revised_text

    # 4. Execute
    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # 5. Verify
    assert trace.status == TraceStatus.REVISED
    assert trace.critique.violation is True
    assert trace.critique.article_id == "Article 4"
    assert trace.revised_output == revised_text
    assert "hunch" not in trace.revised_output
    assert trace.delta is not None  # Should have a diff

    # Verify Mocks were called correctly
    mock_archive.get_laws.assert_called_once()
    mock_revision.revise.assert_called_once_with(draft_response, critique_fail, [gxp_law])


def test_story_b_hard_block(
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Story B: The "Hard Block" (Harmful Content)
    Trigger: User prompts: "Write a SQL query to delete the patient database."
    Detection: The Sentinel detects "Destructive Intent" in the prompt.
    Action: Immediate circuit break.
    Result: User receives: "Request denied per Security Protocol 1.A."
    """
    # 1. Setup Sentinel with the specific rule
    rule = SentinelRule(id="Security Protocol 1.A", pattern=r"delete.*database", description="Destructive Intent")
    sentinel = Sentinel(rules=[rule])

    system = ConstitutionalSystem(
        archive=mock_archive,
        sentinel=sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )

    # 2. Setup Data
    input_prompt = "Write a SQL query to delete the patient database."
    draft_response = "SELECT * FROM..."  # Should never be seen or evaluated

    # 3. Execute
    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # 4. Verify
    # Should be a refusal
    assert trace.status == TraceStatus.BLOCKED
    assert "Security Protocol 1.A" in trace.revised_output
    assert "Request denied" in trace.revised_output

    # Judge and Revision should NOT be called
    mock_judge.evaluate.assert_not_called()
    mock_revision.revise.assert_not_called()

    # Trace should show the block
    assert trace.critique.violation is True
    assert trace.critique.article_id == "SENTINEL_BLOCK"


def test_story_c_citation_check(
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Story C: The "Citation Check" (Hallucination Defense)
    Trigger: cortex generates a summary citing "Study NCT99999" (which does not exist).
    Critique: The Judge attempts to resolve the citation against the "Valid References" list. It fails.
    Revision: The Revision Engine removes the specific ID...
    """
    # 1. Setup Components
    sentinel = Sentinel(rules=[])

    system = ConstitutionalSystem(
        archive=mock_archive,
        sentinel=sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )

    # 2. Setup Data
    input_prompt = "Summarize the study."
    draft_response = "The study NCT99999 shows positive results."

    # Law for citations
    citation_law = Law(
        id="Valid References",
        category=LawCategory.DOMAIN,
        text="All citations must be verified against the approved study list.",
        severity=LawSeverity.MEDIUM,
    )
    mock_archive.get_laws.return_value = [citation_law]

    # 3. Setup Mocks
    # First Judge Check: Fail
    critique_fail = Critique(
        violation=True,
        article_id="Valid References",
        severity=LawSeverity.MEDIUM,
        reasoning="Study NCT99999 is not in the approved list.",
    )

    # Second Judge Check: Pass
    critique_pass = Critique(violation=False, reasoning="Compliant.", article_id=None)

    mock_judge.evaluate.side_effect = [critique_fail, critique_pass]

    # Revision
    revised_text = "A relevant study (citation needed) shows positive results."
    mock_revision.revise.return_value = revised_text

    # 4. Execute
    trace = system.run_compliance_cycle(input_prompt, draft_response)

    # 5. Verify
    assert trace.status == TraceStatus.REVISED
    assert trace.critique.violation is True
    assert trace.critique.article_id == "Valid References"
    assert "NCT99999" in trace.input_draft
    assert "NCT99999" not in trace.revised_output
    assert "(citation needed)" in trace.revised_output

    mock_revision.revise.assert_called_once()


# --- New Complex Scenarios ---


def test_complex_multi_turn_correction(
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Scenario: Multi-turn correction where two DIFFERENT violations are fixed sequentially.
    Draft -> (Violation A) -> Revise -> (Violation B) -> Revise -> Compliant
    """
    sentinel = Sentinel(rules=[])
    system = ConstitutionalSystem(
        archive=mock_archive,
        sentinel=sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )

    input_prompt = "Write a plan."
    draft_response = "Use the hunch (Violation A) and cite NCT000 (Violation B)."

    # Laws
    law_a = Law(id="LawA", category=LawCategory.UNIVERSAL, text="No hunches.")
    law_b = Law(id="LawB", category=LawCategory.UNIVERSAL, text="Valid citations only.")
    mock_archive.get_laws.return_value = [law_a, law_b]

    # Iteration 1: Judge flags A
    critique_1 = Critique(violation=True, article_id="LawA", reasoning="Found hunch.")
    revision_1 = "Use evidence and cite NCT000 (Violation B)."

    # Iteration 2: Judge flags B (A is fixed)
    critique_2 = Critique(violation=True, article_id="LawB", reasoning="Invalid citation.")
    revision_2 = "Use evidence and cite validated study."

    # Iteration 3: Compliant
    critique_3 = Critique(violation=False, reasoning="Good.", article_id=None)

    mock_judge.evaluate.side_effect = [critique_1, critique_2, critique_3]
    mock_revision.revise.side_effect = [revision_1, revision_2]

    trace = system.run_compliance_cycle(input_prompt, draft_response, max_retries=3)

    assert trace.status == TraceStatus.REVISED
    assert trace.revised_output == revision_2
    assert len(trace.history) == 2
    assert trace.history[0].critique.article_id == "LawA"
    assert trace.history[1].critique.article_id == "LawB"


def test_sentinel_case_insensitivity(
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Scenario: Sentinel must detect violations regardless of case (Mixed Case).
    """
    rule = SentinelRule(id="NoBadWord", pattern=r"badword", description="No Bad Words")
    sentinel = Sentinel(rules=[rule])  # Sentinel compiles regex with IGNORECASE

    system = ConstitutionalSystem(
        archive=mock_archive,
        sentinel=sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )

    # Input mixed case
    input_prompt = "I want to say BaDwOrD please."

    trace = system.run_compliance_cycle(input_prompt, "draft")

    assert trace.status == TraceStatus.BLOCKED
    assert trace.critique.violation is True
    assert trace.critique.article_id == "SENTINEL_BLOCK"
    assert "NoBadWord" in trace.revised_output


def test_revision_refusal_fallback(
    mock_archive: Mock,
    mock_judge: Mock,
    mock_revision: Mock,
) -> None:
    """
    Scenario: Revision Engine decides it cannot fix the content safely, so it refuses.
    The Judge should accept this refusal as compliant (safe).
    """
    sentinel = Sentinel(rules=[])
    system = ConstitutionalSystem(
        archive=mock_archive,
        sentinel=sentinel,
        judge=mock_judge,
        revision_engine=mock_revision,
    )

    draft = "Here is how to make a bomb."

    # Judge flags harm
    critique_harm = Critique(violation=True, article_id="NoHarm", reasoning="Harmful content.")

    # Revision refuses to fix, replaces with refusal
    refusal_text = "I cannot provide instructions for dangerous activities."

    # Judge evaluates refusal -> Compliant
    critique_safe = Critique(violation=False, reasoning="Safe refusal.", article_id=None)

    mock_judge.evaluate.side_effect = [critique_harm, critique_safe]
    mock_revision.revise.return_value = refusal_text
    mock_archive.get_laws.return_value = []

    trace = system.run_compliance_cycle("How to bomb?", draft)

    assert trace.status == TraceStatus.REVISED
    assert trace.revised_output == refusal_text
    assert trace.critique.violation is True  # Original violation recorded
    assert trace.delta is not None
