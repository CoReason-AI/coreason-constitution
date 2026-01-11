import json
from pathlib import Path

import pytest
from loguru import logger

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.schema import SentinelRule
from coreason_constitution.sentinel import Sentinel


class TestSentinel:
    def test_sentinel_match_violation(self) -> None:
        """Test that Sentinel correctly identifies and raises exception for matching patterns."""
        rules = [
            SentinelRule(id="SR.1", pattern=r"drop table", description="SQL Injection"),
            SentinelRule(id="SR.2", pattern=r"password", description="PII/Credentials"),
        ]
        sentinel = Sentinel(rules)

        # Direct match
        with pytest.raises(SecurityException, match="Security Protocol Violation: SR.1"):
            sentinel.check("Please write a query to drop table users;")

        # Case insensitive match
        with pytest.raises(SecurityException, match="Security Protocol Violation: SR.1"):
            sentinel.check("DROP TABLE users;")

        # Another rule match
        with pytest.raises(SecurityException, match="Security Protocol Violation: SR.2"):
            sentinel.check("My password is 12345")

    def test_sentinel_no_violation(self) -> None:
        """Test that Sentinel allows safe content."""
        rules = [
            SentinelRule(id="SR.1", pattern=r"drop table", description="SQL Injection"),
        ]
        sentinel = Sentinel(rules)

        # Safe content
        try:
            sentinel.check("Select * from users")
        except SecurityException:
            pytest.fail("Sentinel raised SecurityException for safe content")

    def test_sentinel_empty_content(self) -> None:
        """Test that empty content is allowed (or at least doesn't crash)."""
        rules = [
            SentinelRule(id="SR.1", pattern=r".+", description="Match anything"),
        ]
        sentinel = Sentinel(rules)
        sentinel.check("")  # Should not raise

    def test_sentinel_invalid_regex(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test robust handling of invalid regex in rules."""
        rules = [
            SentinelRule(id="SR.BAD", pattern=r"[", description="Broken regex"),
            SentinelRule(id="SR.GOOD", pattern=r"bad", description="Valid regex"),
        ]

        # Use loguru capture to check for the error
        logs = []
        handler_id = logger.add(lambda msg: logs.append(msg.record["message"]))

        try:
            # Should log error but not crash constructor
            sentinel = Sentinel(rules)
        finally:
            logger.remove(handler_id)

        assert any("Invalid regex pattern" in msg for msg in logs)

        # Good rule should still work
        with pytest.raises(SecurityException, match="SR.GOOD"):
            sentinel.check("This is bad content")


class TestSentinelIntegration:
    def test_archive_loads_sentinel_rules(self, tmp_path: Path) -> None:
        """Test that LegislativeArchive correctly loads SentinelRules from JSON."""

        # Create a sample constitution file
        const_data = {
            "version": "1.0.0",
            "laws": [{"id": "GCP.1", "category": "Domain", "text": "Do no harm", "severity": "High"}],
            "sentinel_rules": [{"id": "RED.1", "pattern": "kill all humans", "description": "Existential threat"}],
        }

        file_path = tmp_path / "const.json"
        file_path.write_text(json.dumps(const_data), encoding="utf-8")

        archive = LegislativeArchive()
        archive.load_from_directory(tmp_path)

        # Check laws loaded
        assert len(archive.get_laws()) == 1

        # Check sentinel rules loaded
        rules = archive.get_sentinel_rules()
        assert len(rules) == 1
        assert rules[0].id == "RED.1"
        assert rules[0].pattern == "kill all humans"

        # Verify Sentinel uses these rules
        sentinel = Sentinel(rules)
        with pytest.raises(SecurityException, match="RED.1"):
            sentinel.check("I want to kill all humans")

    def test_archive_duplicate_rule_ids(self, tmp_path: Path) -> None:
        """Test detection of duplicate Sentinel Rule IDs."""
        const_data_1 = {"version": "1.0.0", "sentinel_rules": [{"id": "RED.1", "pattern": "a", "description": "a"}]}
        const_data_2 = {"version": "1.0.0", "sentinel_rules": [{"id": "RED.1", "pattern": "b", "description": "b"}]}

        (tmp_path / "c1.json").write_text(json.dumps(const_data_1), encoding="utf-8")
        (tmp_path / "c2.json").write_text(json.dumps(const_data_2), encoding="utf-8")

        archive = LegislativeArchive()
        with pytest.raises(ValueError, match="Duplicate Sentinel Rule ID detected: RED.1"):
            archive.load_from_directory(tmp_path)
