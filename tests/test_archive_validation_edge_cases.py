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
from coreason_constitution.schema import LawCategory


def test_poison_pill_list() -> None:
    """
    Test that a list containing mostly valid Laws but one invalid object
    causes the entire file load to fail (fail-safe).
    """
    archive = LegislativeArchive()
    # List has one valid Law and one object missing 'category'
    content = """
    [
      {
        "id": "VALID.1",
        "category": "Universal",
        "text": "Valid law",
        "severity": "Low"
      },
      {
        "id": "INVALID.1",
        "text": "Missing category",
        "severity": "Low"
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__ = MagicMock(return_value="poison_pill.json")  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        # Should fail validation for the list
        with pytest.raises(ValueError, match="Validation failed"):
            archive.load_from_directory("dummy")


def test_unexpected_root_types() -> None:
    """
    Verify behavior when the JSON root is a valid JSON type (e.g., list[int])
    but does not match the Artifact union (List[Law|Rule], Constitution, etc.).
    """
    archive = LegislativeArchive()
    # A list of integers is valid JSON but not a valid Artifact
    content = "[1, 2, 3, 4, 5]"

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__ = MagicMock(return_value="integers.json")  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        with pytest.raises(ValueError, match="Validation failed"):
            archive.load_from_directory("dummy")


def test_extra_fields_ignored() -> None:
    """
    Verify that objects with extra fields (forward compatibility) are loaded correctly
    without error, matching Pydantic's default 'ignore' behavior.
    """
    archive = LegislativeArchive()
    # Law object with an extra "metadata" field
    content = """
    [
      {
        "id": "EXTRA.1",
        "category": "Universal",
        "text": "Has extra fields",
        "severity": "Medium",
        "metadata": {
            "deprecated": false,
            "author": "Gowtham"
        }
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__ = MagicMock(return_value="extra_fields.json")  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        laws = archive.get_laws()
        assert len(laws) == 1
        law = laws[0]
        assert law.id == "EXTRA.1"
        assert law.text == "Has extra fields"
        # Verify the model didn't crash and loaded the known fields correctly.
        # Since extra='ignore' is default, 'metadata' is not on the model instance.
        assert not hasattr(law, "metadata")


def test_ambiguous_fields_resolution() -> None:
    """
    Verify resolution behavior when an object contains fields from both Law and SentinelRule.
    Since Law is checked before SentinelRule in the Union (or via structural matching),
    we want to see which one wins.

    Law requires: id, category, text
    SentinelRule requires: id, pattern, description
    """
    archive = LegislativeArchive()
    # This object has ALL fields for both.
    content = """
    [
      {
        "id": "HYBRID.1",
        "category": "Universal",
        "text": "I am a law",
        "severity": "Low",
        "pattern": "regex_pattern",
        "description": "I am a rule"
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__ = MagicMock(return_value="hybrid.json")  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        laws = archive.get_laws()
        rules = archive.get_sentinel_rules()

        # Since Pydantic tries Union members left-to-right (if not discriminated).
        # We need to know the order in schema.LawOrRule.
        # If schema.py defines `LawOrRule = Union[Law, SentinelRule]`, Law is first.
        # Since this object satisfies Law, it should match Law.
        # The extra fields (pattern, description) should be ignored.

        # Check results
        # If it matched Law:
        if len(laws) == 1:
            assert laws[0].id == "HYBRID.1"
            assert laws[0].category == LawCategory.UNIVERSAL
            # Ensure it didn't ALSO match Rule (should be impossible in a list of Union unless duplicated)
            assert len(rules) == 0
        else:
            # If it matched Rule:
            assert len(rules) == 1
            assert rules[0].id == "HYBRID.1"
            assert len(laws) == 0
