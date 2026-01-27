# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import re
from typing import List, Optional

from coreason_identity.models import UserContext

from coreason_constitution.exceptions import SecurityException
from coreason_constitution.schema import SentinelRule
from coreason_constitution.utils.logger import logger


class Sentinel:
    """
    A lightweight, low-latency classifier for 'Red Line' events.
    It scans the Input Prompt for immediate threats (Jailbreaks, PII injection, prohibited topics)
    using Regex/Keyword matching.
    """

    def __init__(self, rules: List[SentinelRule]) -> None:
        """
        Initialize the Sentinel with a list of rules.

        :param rules: List of SentinelRule objects to enforce.
        """
        self.rules = rules
        self._compiled_patterns = []

        # Pre-compile regex patterns for performance
        for rule in rules:
            try:
                # Compile regex with Ignore Case and Multiline flags
                # re.IGNORECASE: Matches 'drop' and 'DROP'
                # re.MULTILINE: '^' matches start of line, '$' matches end of line
                pattern = re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)
                self._compiled_patterns.append((rule, pattern))
            except re.error as e:
                logger.error(f"Invalid regex pattern for rule {rule.id}: {rule.pattern} - {e}")
                # We log but continue, effectively disabling this broken rule
                # Alternatively, we could raise an exception to fail early on configuration error.
                # Given 'fail-closed' philosophy, maybe we should raise?
                # But here we are just initializing. If a rule is bad, we probably want to fix it.
                # Let's log error.

    def check(self, content: str, user_context: Optional[UserContext] = None) -> None:
        """
        Scans the content against all configured Red Line rules.
        Raises SecurityException if a match is found.

        :param content: The text content to scan (usually the user input prompt).
        :param user_context: Context of the user making the request.
        :raises SecurityException: If any rule is violated.
        """
        if not content:
            return

        for rule, pattern in self._compiled_patterns:
            if pattern.search(content):
                # Check for exemptions
                if user_context and any(group in rule.exempt_groups for group in user_context.groups):
                    logger.warning(
                        f"Sentinel match bypassed for privileged user {user_context.user_id} on rule {rule.id}"
                    )
                    continue

                logger.warning(f"Sentinel Red Line crossed: {rule.id} - {rule.description}")
                raise SecurityException(f"Security Protocol Violation: {rule.id}. Request denied.")
