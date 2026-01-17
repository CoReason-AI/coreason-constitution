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


def test_load_references_list() -> None:
    """
    Test loading a JSON file that is a list of References.
    This hits lines 100-101 in archive.py.
    """
    archive = LegislativeArchive()
    content = """
    [
      {
        "id": "REF.A",
        "text": "Ref A"
      },
      {
        "id": "REF.B",
        "text": "Ref B"
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__.return_value = "refs.json"  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        refs = archive.get_references()
        assert len(refs) == 2
        assert {r.id for r in refs} == {"REF.A", "REF.B"}


def test_load_single_reference() -> None:
    """
    Test loading a JSON file that is a SINGLE Reference object.
    This hits the `elif isinstance(parsed_obj, Reference):` block.
    """
    archive = LegislativeArchive()
    content = """
    {
      "id": "REF.SINGLE",
      "text": "Single Ref"
    }
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__.return_value = "single_ref.json"  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy")

        refs = archive.get_references()
        assert len(refs) == 1
        assert refs[0].id == "REF.SINGLE"


def test_duplicate_references_error() -> None:
    """
    Test that duplicate Reference IDs raise ValueError.
    This hits lines 124-126 in archive.py.
    """
    archive = LegislativeArchive()
    content = """
    [
      {
        "id": "REF.DUP",
        "text": "Ref 1"
      },
      {
        "id": "REF.DUP",
        "text": "Ref 2"
      }
    ]
    """

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        file_mock.__str__.return_value = "dup_refs.json"  # type: ignore

        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        with pytest.raises(ValueError, match="Duplicate Reference ID detected"):
            archive.load_from_directory("dummy")
