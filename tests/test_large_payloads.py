# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import time
from unittest.mock import Mock, create_autospec

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import SentinelRule
from coreason_constitution.sentinel import Sentinel
from coreason_constitution.simulation import SimulatedLLMClient


@pytest.fixture
def sentinel_with_rule() -> Sentinel:
    rule = SentinelRule(id="SEC.TEST", pattern=r"delete.*database", description="Destructive Intent")
    return Sentinel(rules=[rule])


def test_sentinel_large_payload_performance(sentinel_with_rule: Sentinel) -> None:
    """
    Test Sentinel performance with a large payload (500KB+).
    Ensures that regex matching on large strings doesn't hang or crash.
    """
    # Create a large payload (approx 500KB)
    # Case 1: Safe content (repeating string that doesn't match)
    large_safe_content = "This is a safe sentence repeated. " * 20000

    start_time = time.time()
    sentinel_with_rule.check(large_safe_content)
    duration = time.time() - start_time

    # It should be very fast (< 1s)
    assert duration < 1.0, f"Sentinel took too long on safe large payload: {duration:.4f}s"

    # Case 2: Malicious content at the very end
    large_malicious_content = large_safe_content + "delete the production database now"

    with pytest.raises(Exception) as exc:
        sentinel_with_rule.check(large_malicious_content)

    # Sentinel raises SecurityException with the rule ID, but not necessarily the description
    # Message format: "Security Protocol Violation: {rule.id}. Request denied."
    assert "SEC.TEST" in str(exc.value)


def test_system_large_draft_handling() -> None:
    """
    Test that the ConstitutionalSystem can handle a very large draft response
    without crashing or memory errors (simulated).
    """
    # Setup mocks
    mock_archive = create_autospec(LegislativeArchive, instance=True)
    # Judge requires at least one law to proceed
    dummy_law = Mock()
    dummy_law.id = "GCP.4"
    dummy_law.text = "Evidence based claims"
    dummy_law.category.value = "Domain"
    mock_archive.get_laws.return_value = [dummy_law]

    mock_sentinel = create_autospec(Sentinel, instance=True)
    mock_sentinel.check.return_value = None

    # We use a real Judge/Revision with SimulatedLLMClient to verify data passing
    llm_client = SimulatedLLMClient()
    judge = ConstitutionalJudge(llm_client)
    revision = RevisionEngine(llm_client)

    system = ConstitutionalSystem(archive=mock_archive, sentinel=mock_sentinel, judge=judge, revision_engine=revision)

    # 1MB Draft
    large_draft = "Just a hunch... " * 50000
    input_prompt = "What do you think?"

    # The SimulatedLLMClient detects "hunch" and triggers a violation.
    # We want to ensure the system processes this large string through the loop.

    trace = system.run_compliance_cycle(input_prompt, large_draft)

    assert trace.critique.violation is True
    assert trace.critique.article_id == "GCP.4"
    # Verify the revised output is short (the canned response)
    assert "dosage change is not supported" in trace.revised_output
    # Verify input draft is preserved
    assert len(trace.input_draft) == len(large_draft)


def test_sentinel_regex_backtracking_edge_case() -> None:
    """
    Test a potential ReDoS scenario: 'delete' followed by many characters
    but no 'database', where the regex is 'delete.*database'.
    """
    rule = SentinelRule(id="SEC.REDOS", pattern=r"delete.*database", description="ReDoS Check")
    sentinel = Sentinel(rules=[rule])

    # 'delete' + 100k non-newline chars.
    # Since '.' matches everything (except newline usually), it greedily consumes.
    # It fails to find 'database' and backtracks.
    # For `.*`, typically it's linear scan, but let's verify.
    payload = "delete " + ("a" * 100000)

    start_time = time.time()
    sentinel.check(payload)
    duration = time.time() - start_time

    assert duration < 0.5, f"Regex took too long, possible ReDoS: {duration:.4f}s"
