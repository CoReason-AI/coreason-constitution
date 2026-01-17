# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from coreason_constitution.utils.diff import compute_unified_diff


def test_compute_unified_diff_identity() -> None:
    text = "Hello world"
    diff = compute_unified_diff(text, text)
    assert diff is None


def test_compute_unified_diff_change() -> None:
    original = "Hello world\nThis is a test."
    revised = "Hello universe\nThis is a test."

    diff = compute_unified_diff(original, revised)
    assert diff is not None
    assert "--- original" in diff
    assert "+++ revised" in diff
    assert "-Hello world" in diff
    assert "+Hello universe" in diff
    assert " This is a test." in diff


def test_compute_unified_diff_empty() -> None:
    original = ""
    revised = "New content"
    diff = compute_unified_diff(original, revised)
    assert diff is not None
    assert "+New content" in diff


def test_compute_unified_diff_multiline() -> None:
    original = "Line 1\nLine 2\nLine 3"
    revised = "Line 1\nLine 2 Modified\nLine 3"
    diff = compute_unified_diff(original, revised)
    assert diff is not None
    assert "-Line 2" in diff
    assert "+Line 2 Modified" in diff


def test_compute_unified_diff_whitespace() -> None:
    original = "A B"
    revised = "A  B"
    diff = compute_unified_diff(original, revised)
    assert diff is not None
    assert "-A B" in diff
    assert "+A  B" in diff


def test_compute_unified_diff_unicode() -> None:
    original = "Hello 🌍"
    revised = "Hello 🪐"
    diff = compute_unified_diff(original, revised)
    assert diff is not None
    assert "-Hello 🌍" in diff
    assert "+Hello 🪐" in diff
