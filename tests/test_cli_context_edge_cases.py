# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import json
import sys
from unittest.mock import patch

from pytest import CaptureFixture

from coreason_constitution.main import main
from coreason_constitution.simulation import LAW_ID_GCP4, LAW_ID_REF1, TRIGGER_HUNCH, TRIGGER_NCT


class TestCLIContextEdgeCases:
    """
    Edge cases and complex scenarios for CLI context handling.
    """

    def test_cli_context_empty_flag(self, capsys: CaptureFixture[str]) -> None:
        """
        Edge Case: User passes `--context` but NO values.
        Result: args.context is [].
        Logic: get_laws([]) returns ONLY Universal laws (no tags).
        Expectation: Domain laws (GxP, Citation) are filtered out.
        So "hunch" (GxP) should be APPROVED (ignored).
        """
        test_args = [
            "main.py",
            "--prompt",
            "What dosage?",
            "--draft",
            f"I have a {TRIGGER_HUNCH} we should double it.",
            "--context",  # Flag present, no values
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Should be approved because GxP law is NOT universal, so it's filtered out.
        assert output["status"] == "APPROVED"
        assert output["critique"]["violation"] is False
        assert TRIGGER_HUNCH in output["revised_output"]

    def test_cli_context_duplicate_tags(self, capsys: CaptureFixture[str]) -> None:
        """
        Edge Case: User passes duplicate tags `--context GxP GxP`.
        Expectation: Handled gracefully, GxP law enabled.
        """
        test_args = [
            "main.py",
            "--prompt",
            "Dosage?",
            "--draft",
            f"Just a {TRIGGER_HUNCH}.",
            "--context",
            "GxP",
            "GxP",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # GxP enabled -> Violation -> Revised
        assert output["status"] == "REVISED"
        assert output["critique"]["article_id"] == LAW_ID_GCP4

    def test_cli_max_retries_zero(self, capsys: CaptureFixture[str]) -> None:
        """
        Edge Case: `--max-retries 0`.
        Expectation: If violation found, system cannot revise (attempts < 0 is false).
        Result: BLOCKED (with original violation).
        """
        test_args = [
            "main.py",
            "--prompt",
            "Dosage?",
            "--draft",
            f"Just a {TRIGGER_HUNCH}.",
            "--context",
            "GxP",
            "--max-retries",
            "0",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Status should be BLOCKED because we failed to produce a compliant revision (we didn't try)
        # Wait, core.py logic:
        # if not initial_critique.violation: return APPROVED
        # while attempts < max_retries: ...
        # If max_retries=0, loop doesn't run.
        # Fallthrough to "Revision loop failed".
        # Returns BLOCKED with "Safety Protocol Exception".

        assert output["status"] == "BLOCKED"
        assert output["critique"]["violation"] is True
        assert "Unable to generate compliant response" in output["revised_output"]

    def test_cli_complex_mixed_contexts(self, capsys: CaptureFixture[str]) -> None:
        """
        Complex Scenario: Mixed context tags enabling multiple distinct laws.
        Context: "GxP" (for hunch) AND "Citation" (for NCT).
        Input contains BOTH triggers.
        Expectation: The system catches one of them (likely the first one checked by Simulator).
        Currently Simulator checks Hunch first.
        """
        draft = f"I have a {TRIGGER_HUNCH} about {TRIGGER_NCT}."
        test_args = [
            "main.py",
            "--prompt",
            "Analysis?",
            "--draft",
            draft,
            "--context",
            "GxP",
            "Citation",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "REVISED"
        assert output["critique"]["violation"] is True
        # Since Hunch is checked first in Simulator, it should be GCP.4
        assert output["critique"]["article_id"] == LAW_ID_GCP4

    def test_cli_complex_mixed_context_partial_match(self, capsys: CaptureFixture[str]) -> None:
        """
        Complex Scenario: Input has Hunch and NCT.
        Context: ONLY "Citation".
        Expectation: Hunch (GxP) is IGNORED (law not loaded). NCT (Citation) is CAUGHT.
        """
        draft = f"I have a {TRIGGER_HUNCH} about {TRIGGER_NCT}."
        test_args = [
            "main.py",
            "--prompt",
            "Analysis?",
            "--draft",
            draft,
            "--context",
            "Citation",  # ONLY Citation
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "REVISED"
        assert output["critique"]["violation"] is True

        # Hunch is present but GxP law is NOT loaded.
        # NCT is present and Citation law IS loaded.
        # Simulator checks Hunch first.
        # Simulator logic:
        #   if TRIGGER_HUNCH ... if LAW_ID_GCP4 in prompt ... return Violation
        # Since GxP law is missing, GCP.4 ID is missing from prompt. So Simulator skips Hunch.
        # Then checks NCT...

        assert output["critique"]["article_id"] == LAW_ID_REF1
        assert "citation needed" in output["revised_output"]
        # The 'hunch' should likely remain in the output since it wasn't fixed?
        # Or does the Revisor fix it?
        # The Simulated Revisor for NCT replaces "The summary cites..." -> "The summary cites...".
        # It doesn't touch the "hunch" part if it's not triggered.
        # However, the draft string in this test is "I have a hunch about NCT...".
        # The Simulated Revisor for NCT returns fixed string "The summary cites...".
        # It replaces the WHOLE string with the canned response.
        # So 'hunch' will disappear as a side effect of the canned response.
        # That's fine for simulation.
        pass
