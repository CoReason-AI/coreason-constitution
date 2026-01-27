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
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import CaptureFixture

from coreason_constitution.main import main


def test_cli_sentinel_approved(capsys: CaptureFixture[str]) -> None:
    """Test CLI in Sentinel-only mode with safe input."""
    test_args = ["main.py", "--prompt", "Hello world"]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "APPROVED"
    assert "passed Sentinel checks" in output["message"]


def test_cli_sentinel_blocked(capsys: CaptureFixture[str]) -> None:
    """Test CLI in Sentinel-only mode with unsafe input (matching default rule)."""
    # Using a known default rule pattern: "delete.*database"
    test_args = ["main.py", "--prompt", "Please delete the database now"]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "BLOCKED"
    assert "Security Protocol Violation" in output["violation"]


def test_cli_full_cycle_compliant(capsys: CaptureFixture[str]) -> None:
    """Test CLI in full cycle mode with compliant draft."""
    test_args = ["main.py", "--prompt", "Hello", "--draft", "This is a safe response."]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    # Check for ConstitutionalTrace fields
    assert "input_draft" in output
    assert "critique" in output
    assert output["critique"]["violation"] is False
    assert output["revised_output"] == "This is a safe response."


def test_cli_full_cycle_violation_correction(capsys: CaptureFixture[str]) -> None:
    """Test CLI in full cycle mode with violation (Story A logic)."""
    # Story A: "hunch" triggers GxP violation
    test_args = ["main.py", "--prompt", "What dosage?", "--draft", "I have a hunch we should double it."]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["critique"]["violation"] is True
    assert output["critique"]["article_id"] == "GCP.4"
    assert "hunch" not in output["revised_output"]
    assert "evidence" in output["revised_output"]


def test_cli_file_inputs(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    """Test CLI using file inputs for prompt and draft."""
    prompt_file = tmp_path / "prompt.txt"
    draft_file = tmp_path / "draft.txt"

    prompt_file.write_text("What dosage?", encoding="utf-8")
    draft_file.write_text("I have a hunch.", encoding="utf-8")

    test_args = ["main.py", "--prompt-file", str(prompt_file), "--draft-file", str(draft_file)]

    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["critique"]["violation"] is True
    assert output["input_draft"] == "I have a hunch."


def test_cli_missing_file(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    """Test CLI behavior when input file does not exist."""
    missing_file = tmp_path / "nonexistent.txt"
    test_args = ["main.py", "--prompt-file", str(missing_file)]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_cli_invalid_user_context(capsys: CaptureFixture[str]) -> None:
    """Test CLI behavior when UserContext creation fails (e.g. invalid email)."""
    test_args = [
        "main.py",
        "--prompt",
        "Hello",
        "--user-id",
        "u123",
        "--user-email",
        "not-an-email",  # Should trigger Pydantic validation error
    ]
    with patch.object(sys, "argv", test_args):
        # We expect SystemExit(1) due to the try-except block in main.py
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_cli_sentinel_blocked_full_cycle(capsys: CaptureFixture[str]) -> None:
    """Test CLI full cycle but blocked by Sentinel (never reaches draft check)."""
    test_args = ["main.py", "--prompt", "delete database", "--draft", "Irrelevant"]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    # Trace should show sentinel block
    assert output["critique"]["article_id"] == "SENTINEL_BLOCK"
    assert output["revised_output"] != "Irrelevant"


# --- Coverage Tests ---


def test_cli_init_exception(capsys: CaptureFixture[str]) -> None:
    """Test CLI behavior when system initialization fails."""
    test_args = ["main.py", "--prompt", "Hello"]
    with patch.object(sys, "argv", test_args):
        with patch("coreason_constitution.main.LegislativeArchive") as MockArchive:
            MockArchive.side_effect = Exception("Init Error")
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1


def test_cli_compliance_cycle_exception(capsys: CaptureFixture[str]) -> None:
    """Test CLI behavior when run_compliance_cycle fails generically."""
    test_args = ["main.py", "--prompt", "Hello", "--draft", "Draft"]
    with patch.object(sys, "argv", test_args):
        with patch("coreason_constitution.main.ConstitutionalSystem") as MockSystem:
            instance = MockSystem.return_value
            instance.run_compliance_cycle.side_effect = Exception("Cycle Error")

            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1


def test_cli_sentinel_generic_exception(capsys: CaptureFixture[str]) -> None:
    """Test CLI behavior when Sentinel checks fail generically (not SecurityException)."""
    test_args = ["main.py", "--prompt", "Hello"]
    with patch.object(sys, "argv", test_args):
        with patch("coreason_constitution.main.Sentinel") as MockSentinel:
            instance = MockSentinel.return_value
            instance.check.side_effect = Exception("Sentinel Error")

            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1


# --- Edge Case & Complex Tests ---


def test_cli_explicit_empty_draft(capsys: CaptureFixture[str]) -> None:
    """
    Test that providing an empty draft explicitly (--draft "") triggers an error
    because ConstitutionalTrace requires non-empty strings.
    """
    test_args = ["main.py", "--prompt", "Hello", "--draft", "   "]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1

    # Loguru logs to stderr usually, but capsys captures it if configured?
    # We won't assert the log message strictly if capture is tricky, but we assert exit code.


def test_cli_large_input(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    """
    Test CLI robustness with large input files (~50KB).
    """
    large_text = "Safe content. " * 5000  # ~70KB
    prompt_file = tmp_path / "large_prompt.txt"
    prompt_file.write_text(large_text, encoding="utf-8")

    test_args = ["main.py", "--prompt-file", str(prompt_file)]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "APPROVED"


def test_cli_unicode_input(capsys: CaptureFixture[str]) -> None:
    """
    Test CLI with Unicode characters (Emoji, non-Latin scripts) to ensure JSON encoding works.
    """
    prompt = "Hello 👋, ni hao 你好"
    draft = "Review this: 📝"

    test_args = ["main.py", "--prompt", prompt, "--draft", draft]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["input_draft"] == draft
    # Ensure unicode is preserved or correctly escaped in JSON
    # Python json.dumps escapes non-ascii by default unless ensure_ascii=False,
    # but Pydantic model_dump_json typically outputs unicode.
    # We just check content match.
    assert "📝" in output["input_draft"]


def test_cli_complex_triggers(capsys: CaptureFixture[str]) -> None:
    """
    Test input containing multiple triggers (Story A and Story C).
    SimulatedLLMClient likely picks one.
    """
    # "hunch" -> Story A (Correction)
    # "NCT99999" -> Story C (Citation)
    prompt = "Multiple triggers test."
    draft = "I have a hunch we should use study NCT99999."

    test_args = ["main.py", "--prompt", prompt, "--draft", draft]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["critique"]["violation"] is True
    # We verify WHICH violation was caught.
    # Based on SimulatedLLMClient implementation, "hunch" is checked first.
    if "hunch" in output["critique"]["reasoning"]:
        assert output["critique"]["article_id"] == "GCP.4"
    else:
        assert output["critique"]["article_id"] == "REF.1"


def test_cli_with_user_context(capsys: CaptureFixture[str]) -> None:
    """Test CLI with user identity arguments."""
    test_args = [
        "main.py",
        "--prompt",
        "Hello",
        "--draft",
        "Draft",
        "--user-id",
        "u123",
        "--user-email",
        "u123@example.com",
        "--user-roles",
        "admin",
        "staff",
    ]
    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "APPROVED"


def test_cli_missing_email_for_user_context(capsys: CaptureFixture[str]) -> None:
    """Test CLI fails when user-id is provided without user-email."""
    test_args = ["main.py", "--prompt", "Hello", "--user-id", "u123"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1
