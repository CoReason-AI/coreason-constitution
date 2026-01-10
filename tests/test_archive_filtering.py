from typing import List

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.schema import Law, LawCategory


@pytest.fixture  # type: ignore[misc]
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
    ]


@pytest.fixture  # type: ignore[misc]
def archive_with_laws(sample_laws: List[Law]) -> LegislativeArchive:
    archive = LegislativeArchive()
    # Manually inject laws to avoid filesystem dependency for this unit test
    archive._laws = sample_laws
    return archive


def test_get_laws_no_filters(archive_with_laws: LegislativeArchive) -> None:
    """If no filters provided, return all laws."""
    laws = archive_with_laws.get_laws()
    assert len(laws) == 5
    ids = {law.id for law in laws}
    assert ids == {"U1", "T1", "T2", "D1", "DT1"}


def test_get_laws_category_filter(archive_with_laws: LegislativeArchive) -> None:
    """Filter only by category."""
    laws = archive_with_laws.get_laws(categories=[LawCategory.TENANT])
    assert len(laws) == 2
    ids = {law.id for law in laws}
    assert ids == {"T1", "T2"}


def test_get_laws_context_filter_none(archive_with_laws: LegislativeArchive) -> None:
    """
    Explicitly passing None for context_tags should behave like no filter
    (i.e., legacy behavior: return everything).
    """
    laws = archive_with_laws.get_laws(context_tags=None)
    assert len(laws) == 5


def test_get_laws_context_filter_empty_list(archive_with_laws: LegislativeArchive) -> None:
    """
    Passing empty list [] as context_tags means 'no active context'.
    Should return ONLY laws with NO tags (Universal ones).
    """
    laws = archive_with_laws.get_laws(context_tags=[])
    # Should get U1 (tags=[])
    # T1, T2, D1, DT1 all have tags, so they should be excluded.
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
    assert ids == {"U1", "T1", "DT1"}


def test_get_laws_context_tenant_beta(archive_with_laws: LegislativeArchive) -> None:
    """Context: tenant:beta"""
    laws = archive_with_laws.get_laws(context_tags=["tenant:beta"])
    ids = {law.id for law in laws}
    # Expect: U1, T2
    assert ids == {"U1", "T2"}


def test_get_laws_context_app_bio(archive_with_laws: LegislativeArchive) -> None:
    """Context: app:bio"""
    laws = archive_with_laws.get_laws(context_tags=["app:bio"])
    ids = {law.id for law in laws}
    # Expect:
    # U1
    # D1 (Matches app:bio)
    # DT1 (Matches app:bio)
    # T1, T2 exclude
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
    assert ids == {"U1", "T1", "D1", "DT1"}


def test_get_laws_combined_category_and_context(archive_with_laws: LegislativeArchive) -> None:
    """Filter by Category=TENANT AND Context=tenant:acme"""
    laws = archive_with_laws.get_laws(categories=[LawCategory.TENANT], context_tags=["tenant:acme"])
    ids = {law.id for law in laws}
    # U1 is Universal, so excluded by category filter (even though it matches context logic).
    # T1 is Tenant + matches context -> Include.
    # T2 is Tenant + mismatch context -> Exclude.
    # D1 is Domain -> Exclude by category.
    # DT1 is Domain -> Exclude by category.
    assert ids == {"T1"}
