# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from typing import List

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.schema import Law, LawCategory


@pytest.fixture  # type: ignore
def sample_laws() -> List[Law]:
    return [
        Law(
            id="U1",
            category=LawCategory.UNIVERSAL,
            text="Do no harm.",
            tags=[],  # No tags => Universal
        ),
        Law(
            id="T1",
            category=LawCategory.TENANT,
            text="No mention of Competitor X.",
            tags=["tenant:acme"],
        ),
        Law(
            id="T2",
            category=LawCategory.TENANT,
            text="No mention of Competitor Y.",
            tags=["tenant:beta"],
        ),
        Law(
            id="D1",
            category=LawCategory.DOMAIN,
            text="GxP Compliance.",
            tags=["app:bio"],
        ),
        Law(
            id="DT1",
            category=LawCategory.DOMAIN,
            text="Special Bio Rule for Acme.",
            tags=["app:bio", "tenant:acme"],
        ),
        Law(
            id="SHARED",
            category=LawCategory.TENANT,
            text="Shared Rule for Acme and Beta.",
            tags=["tenant:acme", "tenant:beta"],
        ),
        Law(
            id="CASE",
            category=LawCategory.TENANT,
            text="Case sensitive check.",
            tags=["Tag:Case"],
        ),
        Law(
            id="EMPTY",
            category=LawCategory.TENANT,
            text="Empty string tag.",
            tags=[""],
        ),
    ]


@pytest.fixture  # type: ignore
def archive_with_laws(sample_laws: List[Law]) -> LegislativeArchive:
    archive = LegislativeArchive()
    # Manually inject laws to avoid filesystem dependency for this unit test
    archive._laws = sample_laws
    return archive


def test_get_laws_no_filters(archive_with_laws: LegislativeArchive) -> None:
    """If no filters provided, return all laws."""
    laws = archive_with_laws.get_laws()
    assert len(laws) == 8


def test_get_laws_category_filter(archive_with_laws: LegislativeArchive) -> None:
    """Filter only by category."""
    laws = archive_with_laws.get_laws(categories=[LawCategory.TENANT])
    ids = {law.id for law in laws}
    assert ids == {"T1", "T2", "SHARED", "CASE", "EMPTY"}


def test_get_laws_context_filter_none(archive_with_laws: LegislativeArchive) -> None:
    """
    Explicitly passing None for context_tags should behave like no filter
    (i.e., legacy behavior: return everything).
    """
    laws = archive_with_laws.get_laws(context_tags=None)
    assert len(laws) == 8


def test_get_laws_context_filter_empty_list(archive_with_laws: LegislativeArchive) -> None:
    """
    Passing empty list [] as context_tags means 'no active context'.
    Should return ONLY laws with NO tags (Universal ones).
    """
    laws = archive_with_laws.get_laws(context_tags=[])
    # Should get U1 (tags=[])
    # All others have tags, so they should be excluded.
    assert len(laws) == 1
    assert laws[0].id == "U1"


def test_get_laws_context_tenant_acme(archive_with_laws: LegislativeArchive) -> None:
    """Context: tenant:acme"""
    laws = archive_with_laws.get_laws(context_tags=["tenant:acme"])
    ids = {law.id for law in laws}
    # Expect:
    # U1 (No tags -> include)
    # T1 (Matches tenant:acme)
    # T2 (tenant:beta -> exclude)
    # D1 (app:bio -> exclude)
    # DT1 (Matches tenant:acme)
    # SHARED (Matches tenant:acme)
    assert ids == {"U1", "T1", "DT1", "SHARED"}


def test_get_laws_context_tenant_beta(archive_with_laws: LegislativeArchive) -> None:
    """Context: tenant:beta"""
    laws = archive_with_laws.get_laws(context_tags=["tenant:beta"])
    ids = {law.id for law in laws}
    # Expect: U1, T2, SHARED
    assert ids == {"U1", "T2", "SHARED"}


def test_get_laws_context_app_bio(archive_with_laws: LegislativeArchive) -> None:
    """Context: app:bio"""
    laws = archive_with_laws.get_laws(context_tags=["app:bio"])
    ids = {law.id for law in laws}
    # Expect:
    # U1
    # D1 (Matches app:bio)
    # DT1 (Matches app:bio)
    assert ids == {"U1", "D1", "DT1"}


def test_get_laws_context_complex_intersection(archive_with_laws: LegislativeArchive) -> None:
    """Context: tenant:acme AND app:bio"""
    laws = archive_with_laws.get_laws(context_tags=["tenant:acme", "app:bio"])
    ids = {law.id for law in laws}
    # Expect:
    # U1 (Universal)
    # T1 (Matches tenant:acme)
    # T2 (Exclude)
    # D1 (Matches app:bio)
    # DT1 (Matches tenant:acme AND app:bio)
    # SHARED (Matches tenant:acme)
    assert ids == {"U1", "T1", "D1", "DT1", "SHARED"}


def test_get_laws_combined_category_and_context(archive_with_laws: LegislativeArchive) -> None:
    """Filter by Category=TENANT AND Context=tenant:acme"""
    laws = archive_with_laws.get_laws(categories=[LawCategory.TENANT], context_tags=["tenant:acme"])
    ids = {law.id for law in laws}
    # U1 (Univ) -> Exclude by Cat
    # T1 (Tenant, acme) -> Include
    # DT1 (Domain, acme) -> Exclude by Cat
    # SHARED (Tenant, acme) -> Include
    assert ids == {"T1", "SHARED"}


# --- New Edge Cases ---


def test_get_laws_duplicates_in_context(archive_with_laws: LegislativeArchive) -> None:
    """Duplicate tags in context should not affect result."""
    laws = archive_with_laws.get_laws(context_tags=["tenant:acme", "tenant:acme"])
    ids = {law.id for law in laws}
    assert ids == {"U1", "T1", "DT1", "SHARED"}


def test_get_laws_case_sensitivity(archive_with_laws: LegislativeArchive) -> None:
    """Tags should be treated case-sensitively by default."""
    # Law 'CASE' has tag 'Tag:Case'

    # 1. Exact match
    laws_exact = archive_with_laws.get_laws(context_tags=["Tag:Case"])
    assert "CASE" in {law.id for law in laws_exact}

    # 2. Case mismatch
    laws_mismatch = archive_with_laws.get_laws(context_tags=["tag:case"])
    ids_mismatch = {law.id for law in laws_mismatch}
    assert "CASE" not in ids_mismatch
    assert "U1" in ids_mismatch  # U1 is universal


def test_get_laws_empty_string_tag(archive_with_laws: LegislativeArchive) -> None:
    """Handle empty string as a valid tag if present."""
    # Law 'EMPTY' has tag [""]

    # 1. Match empty string
    laws = archive_with_laws.get_laws(context_tags=[""])
    ids = {law.id for law in laws}
    assert "EMPTY" in ids
    assert "U1" in ids

    # 2. No match
    laws_nm = archive_with_laws.get_laws(context_tags=["something"])
    ids_nm = {law.id for law in laws_nm}
    assert "EMPTY" not in ids_nm


def test_get_laws_large_number_of_tags(archive_with_laws: LegislativeArchive) -> None:
    """Simulate a law with many tags and a context with many tags."""
    # Create a law with 1000 tags
    many_tags = [f"tag:{i}" for i in range(1000)]
    complex_law = Law(id="COMPLEX", category=LawCategory.DOMAIN, text="Complex law", tags=many_tags)

    # Inject it
    archive_with_laws._laws.append(complex_law)

    # Context matching the last tag
    laws = archive_with_laws.get_laws(context_tags=["tag:999"])
    assert "COMPLEX" in {law.id for law in laws}

    # Context matching none
    laws_none = archive_with_laws.get_laws(context_tags=["tag:1001"])
    assert "COMPLEX" not in {law.id for law in laws_none}
