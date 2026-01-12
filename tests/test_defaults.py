from unittest.mock import MagicMock, patch

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.schema import LawCategory, LawSeverity


def test_load_defaults() -> None:
    """
    Verify that the LegislativeArchive can load the default laws and sentinel rules
    packaged with the library.
    """
    archive = LegislativeArchive()
    archive.load_defaults()

    # 1. Verify Laws
    laws = archive.get_laws()
    assert len(laws) >= 2, "Should load at least 2 default laws (GCP.4 and REF.1)"

    # Check for GCP.4 (Evidence-Based Claims)
    gxp_law = next((law for law in laws if law.id == "GCP.4"), None)
    assert gxp_law is not None
    assert gxp_law.category == LawCategory.DOMAIN
    assert gxp_law.severity == LawSeverity.HIGH
    assert "speculation" in gxp_law.text
    assert "GxP" in gxp_law.tags

    # Check for REF.1 (Citation Check)
    ref_law = next((law for law in laws if law.id == "REF.1"), None)
    assert ref_law is not None
    assert ref_law.category == LawCategory.DOMAIN
    assert "citations" in ref_law.text

    # 2. Verify Sentinel Rules
    rules = archive.get_sentinel_rules()
    assert len(rules) >= 1, "Should load at least 1 default sentinel rule (SEC.1)"

    # Check for SEC.1 (Destructive Intent)
    sec_rule = next((r for r in rules if r.id == "SEC.1"), None)
    assert sec_rule is not None
    assert "delete" in sec_rule.pattern
    assert "Destructive Intent" in sec_rule.description


def test_load_defaults_missing_dir() -> None:
    """
    Verify that load_defaults handles missing directory gracefully.
    """
    archive = LegislativeArchive()
    with patch("pathlib.Path.exists", return_value=False):
        archive.load_defaults()
    # Should log warning but not raise error


def test_duplicate_sentinel_rule_error() -> None:
    """
    Verify that loading a sentinel rule with a duplicate ID raises a ValueError.
    """
    archive = LegislativeArchive()

    # Define duplicate content
    content1 = '[{"id": "RULE1", "pattern": "abc", "description": "desc1"}]'
    content2 = '[{"id": "RULE1", "pattern": "def", "description": "desc2"}]'

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file1 = MagicMock()
        file1.read_text.return_value = content1

        file2 = MagicMock()
        file2.read_text.return_value = content2

        mock_rglob.return_value = [file1, file2]
        mock_exists.return_value = True  # Pretend the directory exists

        with pytest.raises(ValueError, match="Duplicate Sentinel Rule ID detected"):
            archive.load_from_directory("dummy_path")


def test_load_single_rule_object() -> None:
    """
    Verify loading a single SentinelRule object from a JSON file (as a dict).
    """
    archive = LegislativeArchive()
    content = '{"id": "SINGLE_RULE", "pattern": "xyz", "description": "Single Rule"}'

    with patch("pathlib.Path.rglob") as mock_rglob, patch("pathlib.Path.exists") as mock_exists:
        file_mock = MagicMock()
        file_mock.read_text.return_value = content
        mock_rglob.return_value = [file_mock]
        mock_exists.return_value = True

        archive.load_from_directory("dummy_path")

        rules = archive.get_sentinel_rules()
        assert len(rules) == 1
        assert rules[0].id == "SINGLE_RULE"
