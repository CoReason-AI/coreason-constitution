import json
import sys
from pathlib import Path
from typing import Generator, List
from unittest.mock import patch

import pytest
from pytest import CaptureFixture

from coreason_constitution.main import main
from coreason_constitution.utils.logger import logger


@pytest.fixture  # type: ignore
def capture_logs() -> Generator[List[str], None, None]:
    """Fixture to capture loguru logs into a list."""
    logs: List[str] = []
    sink_id = logger.add(lambda msg: logs.append(msg), format="{message}")
    yield logs
    logger.remove(sink_id)


def test_cli_mutually_exclusive_args(capsys: CaptureFixture[str]) -> None:
    """
    Edge Case: User provides both --prompt and --prompt-file.
    Expectation: CLI should exit with status code 2 (argparse error).
    """
    test_args = ["main.py", "--prompt", "text", "--prompt-file", "file.txt"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2


def test_cli_permission_error(capsys: CaptureFixture[str], tmp_path: Path) -> None:
    """
    Edge Case: User provides a file that exists but is not readable.
    Expectation: CLI should log error and exit with status code 1.
    """
    # Create a file and remove read permissions
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("content", encoding="utf-8")

    # Attempt to remove permissions
    import os

    try:
        os.chmod(secret_file, 0o000)
    except Exception:
        pytest.skip("Cannot change file permissions in this environment")

    test_args = ["main.py", "--prompt-file", str(secret_file)]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1

    # Restore permissions
    os.chmod(secret_file, 0o666)


def test_cli_output_purity_with_logs(capsys: CaptureFixture[str], capture_logs: List[str]) -> None:
    """
    Complex Scenario: Ensure stdout remains pure JSON even when logs are emitted.
    We trigger a Sentinel warning which logs to stderr/logs.
    """
    # "delete database" triggers Sentinel SEC.1 which logs a warning.
    test_args = ["main.py", "--prompt", "delete database"]

    with patch.object(sys, "argv", test_args):
        main()

    captured = capsys.readouterr()

    # 1. Verify stdout is parseable JSON
    try:
        output = json.loads(captured.out)
    except json.JSONDecodeError:
        pytest.fail(f"stdout is not valid JSON. Content: {captured.out}")

    assert output["status"] == "BLOCKED"

    # 2. Verify logs were emitted
    # We check our custom sink because capsys might miss loguru's direct stderr writes depending on config
    log_content = "".join(capture_logs)
    assert "Sentinel Red Line crossed" in log_content


def test_cli_corrupted_defaults(capsys: CaptureFixture[str], capture_logs: List[str]) -> None:
    """
    Edge Case: The defaults directory contains corrupted data (e.g. bad schema).
    Expectation: System initialization fails, CLI logs error and exits 1.
    """
    test_args = ["main.py", "--prompt", "Hello"]

    with patch.object(sys, "argv", test_args):
        # We mock LegislativeArchive.load_defaults to raise ValueError
        with patch("coreason_constitution.main.LegislativeArchive") as MockArchive:
            instance = MockArchive.return_value
            instance.load_defaults.side_effect = ValueError("Corrupted JSON in defaults")

            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1

    # Verify log message
    log_content = "".join(capture_logs)
    assert "Failed to initialize system" in log_content


def test_cli_no_args(capsys: CaptureFixture[str]) -> None:
    """
    Edge Case: User runs CLI with no arguments.
    Expectation: argparse shows usage and exits with code 2.
    """
    test_args = ["main.py"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2
