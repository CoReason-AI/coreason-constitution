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


class TestDynamicContextIntegration:
    """
    Integration tests to verify that the CLI and Simulation correctly handle
    dynamic law loading via context tags.
    """

    def test_cli_context_story_a_enabled(self, capsys: CaptureFixture[str]) -> None:
        """
        Story A (GxP Compliance):
        Input contains "hunch".
        Context: "GxP" (Should load GCP.4).
        Expectation: VIOLATION -> REVISED.
        """
        # GCP.4 is tagged with ["GxP", "Clinical"].
        test_args = [
            "main.py",
            "--prompt",
            "What dosage?",
            "--draft",
            f"I have a {TRIGGER_HUNCH} we should double it.",
            "--context",
            "GxP",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "REVISED"
        assert output["critique"]["violation"] is True
        assert output["critique"]["article_id"] == LAW_ID_GCP4
        assert "evidence" in output["revised_output"]

    def test_cli_context_story_a_disabled(self, capsys: CaptureFixture[str]) -> None:
        """
        Story A (GxP Compliance):
        Input contains "hunch".
        Context: "Finance" (Should NOT load GCP.4).
        Expectation: APPROVED (No violation because law is not active).
        """
        # Passing an unrelated context tag means GCP.4 (tagged GxP) is filtered out.
        test_args = [
            "main.py",
            "--prompt",
            "What dosage?",
            "--draft",
            f"I have a {TRIGGER_HUNCH} we should double it.",
            "--context",
            "Finance",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "APPROVED"
        assert output["critique"]["violation"] is False
        # The output should remain unchanged (the bad draft is accepted because no law prevents it)
        assert TRIGGER_HUNCH in output["revised_output"]

    def test_cli_context_story_c_enabled(self, capsys: CaptureFixture[str]) -> None:
        """
        Story C (Citation Check):
        Input contains "NCT99999".
        Context: "Citation" (Should load REF.1).
        Expectation: VIOLATION -> REVISED.
        """
        # REF.1 is tagged with ["Citation", "Fact-Check"].
        test_args = [
            "main.py",
            "--prompt",
            "Summarize study.",
            "--draft",
            f"The study {TRIGGER_NCT} shows results.",
            "--context",
            "Citation",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "REVISED"
        assert output["critique"]["violation"] is True
        assert output["critique"]["article_id"] == LAW_ID_REF1
        assert "(citation needed)" in output["revised_output"]

    def test_cli_context_story_c_disabled(self, capsys: CaptureFixture[str]) -> None:
        """
        Story C (Citation Check):
        Input contains "NCT99999".
        Context: None (No tags passed, but implicit empty context behavior).
        Wait, if we pass NO context, get_laws(None) returns ALL laws.
        So REF.1 (tagged) IS included by default?
        Let's check `archive.py`:
            if context_tags is not None: ...
        Yes, default includes everything.

        So to DISABLE it, we must pass a context that DOES NOT match REF.1 tags.
        Context: "GxP" (Matches GCP.4 but NOT REF.1).
        Expectation: APPROVED.
        """
        test_args = [
            "main.py",
            "--prompt",
            "Summarize study.",
            "--draft",
            f"The study {TRIGGER_NCT} shows results.",
            "--context",
            "GxP",  # Matches GCP.4, but NOT REF.1
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "APPROVED"
        assert output["critique"]["violation"] is False

    def test_cli_max_retries(self, capsys: CaptureFixture[str]) -> None:
        """
        Test that max-retries argument is accepted.
        We can't easily force a retry loop failure with standard simulation unless we mock RevisionEngine failure.
        But we can at least check it doesn't crash and passes the arg.
        We'll use patch on ConstitutionalSystem to verify the arg is passed.
        """
        test_args = [
            "main.py",
            "--prompt",
            "Hi",
            "--draft",
            "Hi",
            "--max-retries",
            "5",
        ]
        with patch.object(sys, "argv", test_args):
            with patch("coreason_constitution.main.ConstitutionalSystem") as MockSystem:
                # We need to mock the components initialization too since main() does it before system init
                # But main() instantiates real classes. We can rely on that.
                # We just want to check run_compliance_cycle call args.
                mock_instance = MockSystem.return_value
                # Mock return trace
                from coreason_constitution.schema import ConstitutionalTrace, Critique, TraceStatus

                mock_instance.run_compliance_cycle.return_value = ConstitutionalTrace(
                    status=TraceStatus.APPROVED,
                    input_draft="Hi",
                    critique=Critique(violation=False, reasoning="OK"),
                    revised_output="Hi",
                )

                main()

                # Check call args
                args, kwargs = mock_instance.run_compliance_cycle.call_args
                assert kwargs["max_retries"] == 5
