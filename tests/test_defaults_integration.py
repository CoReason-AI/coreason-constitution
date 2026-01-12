from typing import List, Set

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.schema import Law


@pytest.fixture  # type: ignore
def real_archive() -> LegislativeArchive:
    """
    Fixture that loads the ACTUAL default laws from the filesystem.
    This ensures we are testing the real configuration, not mocks.
    """
    archive = LegislativeArchive()
    archive.load_defaults()
    return archive


def get_law_ids(laws: List[Law]) -> Set[str]:
    return {law.id for law in laws}


def test_defaults_filtering_no_context(real_archive: LegislativeArchive) -> None:
    """
    Complex Scenario: User provides NO context tags (empty list).
    Expectation: Only 'Universal' laws (no tags) should be returned.
    Specifically: UNI.1
    """
    laws = real_archive.get_laws(context_tags=[])
    ids = get_law_ids(laws)

    assert "UNI.1" in ids, "Universal law UNI.1 must be present when no context is provided"
    assert "TEN.1" not in ids, "Tenant law TEN.1 (tagged) must NOT be present without context"
    assert "GCP.4" not in ids, "Domain law GCP.4 (tagged) must NOT be present without context"
    assert "REF.1" not in ids, "Domain law REF.1 (tagged) must NOT be present without context"


def test_defaults_filtering_tenant_context(real_archive: LegislativeArchive) -> None:
    """
    Complex Scenario: User acts as 'tenant:acme'.
    Expectation: Universal laws + Tenant specific laws.
    """
    laws = real_archive.get_laws(context_tags=["tenant:acme"])
    ids = get_law_ids(laws)

    assert "UNI.1" in ids, "Universal law must be present"
    assert "TEN.1" in ids, "Tenant law for 'tenant:acme' must be present"
    assert "GCP.4" not in ids, "Unrelated Domain law should not be present"


def test_defaults_filtering_domain_context(real_archive: LegislativeArchive) -> None:
    """
    Complex Scenario: User is in a 'GxP' application context.
    Expectation: Universal laws + GxP laws.
    """
    laws = real_archive.get_laws(context_tags=["GxP"])
    ids = get_law_ids(laws)

    assert "UNI.1" in ids, "Universal law must be present"
    assert "GCP.4" in ids, "GxP law must be present"
    assert "TEN.1" not in ids, "Unrelated Tenant law should not be present"


def test_defaults_filtering_mixed_context(real_archive: LegislativeArchive) -> None:
    """
    Complex Scenario: User is 'tenant:acme' working in 'GxP' app.
    Expectation: Union of Universal, Tenant, and GxP laws.
    """
    laws = real_archive.get_laws(context_tags=["tenant:acme", "GxP"])
    ids = get_law_ids(laws)

    assert "UNI.1" in ids
    assert "TEN.1" in ids
    assert "GCP.4" in ids

    # REF.1 has tags ["Citation", "Fact-Check"], so it should NOT be here unless we add those tags
    assert "REF.1" not in ids


def test_defaults_filtering_partial_overlap(real_archive: LegislativeArchive) -> None:
    """
    Edge Case: Context matches one tag of a multi-tag law.
    GCP.4 has tags ["GxP", "Clinical"].
    Providing ["Clinical"] should be enough to include it.
    """
    laws = real_archive.get_laws(context_tags=["Clinical"])
    ids = get_law_ids(laws)

    assert "GCP.4" in ids


def test_defaults_filtering_unknown_tag(real_archive: LegislativeArchive) -> None:
    """
    Edge Case: Context contains unknown tags.
    Should return ONLY Universal laws.
    """
    laws = real_archive.get_laws(context_tags=["unknown:tag", "random:nonsense"])
    ids = get_law_ids(laws)

    assert "UNI.1" in ids
    assert len(ids) == 1, "Only universal law should be returned for unknown context"
