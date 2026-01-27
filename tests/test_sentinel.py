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
from pathlib import Path

import pytest
from loguru import logger

from coreason_identity.models import UserContext

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


class TestSentinelComplexScenarios:
    def test_large_payload(self) -> None:
        """Test Sentinel behavior with a large payload (1MB)."""
        rules = [SentinelRule(id="SR.1", pattern=r"malicious", description="Bad stuff")]
        sentinel = Sentinel(rules)

        # 1MB string
        large_safe = "safe " * 200000
        sentinel.check(large_safe)  # Should not raise or hang

        # 1MB string with violation at end
        large_unsafe = large_safe + "malicious"
        with pytest.raises(SecurityException, match="SR.1"):
            sentinel.check(large_unsafe)

    def test_multiline_anchor_behavior(self) -> None:
        """Test that ^ matches start of line in multiline input (due to re.MULTILINE)."""
        rules = [SentinelRule(id="SR.ML", pattern=r"^forbidden", description="Must not start line")]
        sentinel = Sentinel(rules)

        # Should match on second line
        content = "Line 1 is okay\nforbidden on line 2"
        with pytest.raises(SecurityException, match="SR.ML"):
            sentinel.check(content)

    def test_rule_priority(self) -> None:
        """Test that the first matching rule in the list is the one reported."""
        rules = [
            SentinelRule(id="SR.FIRST", pattern=r"bad", description="First rule"),
            SentinelRule(id="SR.SECOND", pattern=r"bad", description="Second rule"),
        ]
        sentinel = Sentinel(rules)

        with pytest.raises(SecurityException, match="SR.FIRST"):
            sentinel.check("This is bad")

    def test_unicode_handling(self) -> None:
        """Test handling of unicode characters and homoglyphs."""
        rules = [SentinelRule(id="SR.UNI", pattern=r"bad", description="Standard ASCII match")]
        sentinel = Sentinel(rules)

        # Standard ASCII
        with pytest.raises(SecurityException, match="SR.UNI"):
            sentinel.check("This is bad")

        # Homoglyph (Cyrillic 'a') - Should NOT match standard ASCII regex
        # Cyrillic 'a' is U+0430
        cyrillic_bad = "b\u0430d"
        sentinel.check(cyrillic_bad)  # Should pass

        # Regex targeting unicode property or specific char
        # Note: Python's re module has limited Unicode support compared to `regex` module,
        # but supports basic matching.
        rules_uni = [SentinelRule(id="SR.CYR", pattern=r"b\u0430d", description="Cyrillic match")]
        sentinel_uni = Sentinel(rules_uni)
        with pytest.raises(SecurityException, match="SR.CYR"):
            sentinel_uni.check(cyrillic_bad)


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


class TestSentinelExemptions:
    def test_exemption_bypass(self) -> None:
        """Test that a user with an exempt group can bypass a specific rule."""
        rules = [
            SentinelRule(
                id="SR.ADMIN_ONLY",
                pattern="sudo",
                description="Admin command",
                exempt_groups=["admins"],
            )
        ]
        sentinel = Sentinel(rules)
        user_context = UserContext(user_id="u123", email="u123@example.com", groups=["admins", "staff"])

        # Capture logs
        logs = []
        handler_id = logger.add(lambda msg: logs.append(msg.record["message"]))

        try:
            # Should NOT raise exception
            sentinel.check("sudo reboot", user_context)
        finally:
            logger.remove(handler_id)

        # Should log the bypass
        log_text = "\n".join(logs)
        assert "Sentinel match bypassed" in log_text
        assert "u123" in log_text
        assert "SR.ADMIN_ONLY" in log_text

    def test_no_exemption_violation(self) -> None:
        """Test that a user WITHOUT the exempt group is still blocked."""
        rules = [
            SentinelRule(
                id="SR.ADMIN_ONLY",
                pattern="sudo",
                description="Admin command",
                exempt_groups=["admins"],
            )
        ]
        sentinel = Sentinel(rules)
        user_context = UserContext(user_id="u456", email="u456@example.com", groups=["staff", "interns"])

        # Should raise exception
        with pytest.raises(SecurityException, match="SR.ADMIN_ONLY"):
            sentinel.check("sudo reboot", user_context)

    def test_none_user_context(self) -> None:
        """Test that no user context means no exemptions."""
        rules = [
            SentinelRule(
                id="SR.ADMIN_ONLY",
                pattern="sudo",
                description="Admin command",
                exempt_groups=["admins"],
            )
        ]
        sentinel = Sentinel(rules)

        with pytest.raises(SecurityException, match="SR.ADMIN_ONLY"):
            sentinel.check("sudo reboot", None)

    def test_mixed_rules_exemption(self) -> None:
        """Test that exemption only applies to the specific rule, not others."""
        rules = [
            SentinelRule(
                id="SR.ADMIN",
                pattern="sudo",
                description="Admin only",
                exempt_groups=["admins"],
            ),
            SentinelRule(
                id="SR.BAD",
                pattern="bad",
                description="Nobody allowed",
                exempt_groups=[],
            ),
        ]
        sentinel = Sentinel(rules)
        user_context = UserContext(user_id="u123", email="u123@example.com", groups=["admins"])

        # Exempt from SR.ADMIN
        sentinel.check("sudo make me a sandwich", user_context)

        # NOT exempt from SR.BAD
        with pytest.raises(SecurityException, match="SR.BAD"):
            sentinel.check("this is bad", user_context)
