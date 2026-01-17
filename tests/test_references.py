# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from unittest.mock import Mock

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.schema import Law, LawCategory, Reference

# --- Schema & Archive Tests ---


def test_reference_schema_validation() -> None:
    """Verify that Reference model works as expected."""
    # Valid
    ref = Reference(id="REF1", text="Source A")
    assert ref.id == "REF1"
    assert ref.tags == []
    assert ref.url is None

    # Full fields
    ref2 = Reference(id="REF2", text="Source B", tags=["t1"], url="http://example.com", metadata={"year": 2025})
    assert ref2.url == "http://example.com"
    assert ref2.metadata["year"] == 2025


def test_archive_loads_references_defaults() -> None:
    """Verify loading defaults includes references."""
    archive = LegislativeArchive()
    archive.load_defaults()

    refs = archive.get_references()
    assert len(refs) > 0
    # Check for the sample we added
    ids = {r.id for r in refs}
    assert "REF.123" in ids
    assert "REF.UNIV" in ids


def test_archive_get_references_filtering() -> None:
    """Verify context filtering for references."""
    archive = LegislativeArchive()
    # Manually inject
    refs = [
        Reference(id="U", text="Universal", tags=[]),
        Reference(id="A", text="Acme", tags=["tenant:acme"]),
        Reference(id="B", text="Beta", tags=["tenant:beta"]),
        Reference(id="S", text="Shared", tags=["tenant:acme", "tenant:beta"]),
    ]
    archive._references = refs

    # No context -> All (legacy/default behavior)
    assert len(archive.get_references(None)) == 4

    # Empty context -> Universal only
    u_refs = archive.get_references([])
    assert len(u_refs) == 1
    assert u_refs[0].id == "U"

    # Context A
    a_refs = archive.get_references(["tenant:acme"])
    ids = {r.id for r in a_refs}
    assert ids == {"U", "A", "S"}

    # Context B
    b_refs = archive.get_references(["tenant:beta"])
    ids = {r.id for r in b_refs}
    assert ids == {"U", "B", "S"}


# --- Judge Tests ---


@pytest.fixture  # type: ignore
def mock_llm() -> Mock:
    mock = Mock()
    # Setup mock to return a dummy Critique
    mock.structured_output.return_value = Mock(violation=False, article_id=None, reasoning="OK")
    return mock


def test_judge_includes_references_in_prompt(mock_llm: Mock) -> None:
    """Verify that the Judge injects references into the system prompt."""
    judge = ConstitutionalJudge(mock_llm)
    laws = [Law(id="L1", category=LawCategory.UNIVERSAL, text="Law 1")]
    refs = [
        Reference(id="R1", text="Ref Text 1", url="http://u.rl"),
        Reference(id="R2", text="Ref Text 2"),
    ]

    draft = "Some draft."
    judge.evaluate(draft, laws, references=refs)

    # Check calls
    call_args = mock_llm.structured_output.call_args
    # call_args.kwargs['messages']
    messages = call_args.kwargs["messages"]
    system_msg = messages[0]["content"]
    user_msg = messages[1]["content"]

    # Assert System Prompt mentions checking citations
    assert "VALID REFERENCES" in system_msg
    assert "--- VALID REFERENCES ---" in user_msg
    assert "ID: R1 | Text: Ref Text 1 | URL: http://u.rl" in user_msg
    assert "ID: R2 | Text: Ref Text 2" in user_msg


def test_judge_no_references_behavior(mock_llm: Mock) -> None:
    """Verify prompt when no references are provided."""
    judge = ConstitutionalJudge(mock_llm)
    laws = [Law(id="L1", category=LawCategory.UNIVERSAL, text="Law 1")]

    judge.evaluate("draft", laws, references=[])

    messages = mock_llm.structured_output.call_args.kwargs["messages"]
    user_msg = messages[1]["content"]

    assert "--- VALID REFERENCES ---" not in user_msg
