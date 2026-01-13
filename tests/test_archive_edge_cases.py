# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from unittest.mock import MagicMock, patch

import pytest

from coreason_constitution.archive import LegislativeArchive


def test_malformed_json_file() -> None:
    """Test that a file with invalid JSON syntax raises ValueError."""
    archive = LegislativeArchive()
    content = "{ invalid json"

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        # Ensure we can stringify the path for error message formatting
        file_mock.__str__ = MagicMock(return_value="bad_file.json")  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        with pytest.raises(ValueError, match="Failed to parse"):
            archive.load_from_directory("dummy")


def test_schema_violation_missing_field() -> None:
    """Test that a Law object missing a required field (category) raises ValueError."""
    archive = LegislativeArchive()
    # Missing 'category'
    content = '[{"id": "BAD.1", "text": "Missing category", "severity": "Low"}]'

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__ = MagicMock(return_value="bad_schema.json")  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        # The archive catches Pydantic validation errors and re-raises as ValueError
        with pytest.raises(ValueError, match="Failed to parse"):
            archive.load_from_directory("dummy")


def test_ambiguous_item_resolution() -> None:
    """
    Test an item that has both Law fields and SentinelRule fields.
    Current heuristic: if 'pattern' exists, it's a SentinelRule.
    """
    archive = LegislativeArchive()
    # Has 'pattern' (Rule) AND 'category' (Law)
    content = """
    [
      {
        "id": "AMBIG.1",
        "pattern": "some regex",
        "category": "Universal",
        "text": "some text",
        "description": "A rule description"
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        # Should be loaded as a SentinelRule, NOT a Law
        rules = archive.get_sentinel_rules()
        laws = archive.get_laws()

        assert len(rules) == 1
        assert len(laws) == 0
        assert rules[0].id == "AMBIG.1"
        assert rules[0].pattern == "some regex"


def test_mixed_content_list() -> None:
    """Test a JSON list containing both Laws and SentinelRules."""
    archive = LegislativeArchive()
    content = """
    [
      {
        "id": "LAW.1",
        "category": "Universal",
        "text": "Be good."
      },
      {
        "id": "RULE.1",
        "pattern": "bad_pattern",
        "description": "Don't do this."
      },
      {
        "id": "LAW.2",
        "category": "Domain",
        "text": "Be accurate."
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        laws = archive.get_laws()
        rules = archive.get_sentinel_rules()

        assert len(laws) == 2
        assert len(rules) == 1

        # Verify IDs to ensure correct parsing
        law_ids = {law.id for law in laws}
        assert "LAW.1" in law_ids
        assert "LAW.2" in law_ids
        assert rules[0].id == "RULE.1"


def test_empty_json_list() -> None:
    """Test that an empty JSON list loads nothing but does not error."""
    archive = LegislativeArchive()
    content = "[]"

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        assert len(archive.get_laws()) == 0
        assert len(archive.get_sentinel_rules()) == 0
