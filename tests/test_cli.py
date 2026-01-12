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
