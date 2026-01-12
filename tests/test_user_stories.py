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
    assert trace.critique.violation is True
    assert trace.critique.article_id == "Valid References"
    assert "NCT99999" in trace.input_draft
    assert "NCT99999" not in trace.revised_output
    assert "(citation needed)" in trace.revised_output

    mock_revision.revise.assert_called_once()
