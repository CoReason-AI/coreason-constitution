import json
from pathlib import Path
from typing import Any, Dict

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.schema import Constitution, Law, LawCategory, LawSeverity


@pytest.fixture  # type: ignore
def law_dict() -> Dict[str, Any]:
    return {
        "id": "UNIV.1",
        "category": "Universal",
        "text": "Do not harm.",
        "severity": "High",
        "tags": ["safety"],
        "source": "Asimov",
    }


def test_law_model_validation(law_dict: Dict[str, Any]) -> None:
    law = Law(**law_dict)
    assert law.id == "UNIV.1"
    assert law.category == LawCategory.UNIVERSAL
    assert law.severity == LawSeverity.HIGH


def test_law_model_defaults() -> None:
    # Explicitly using Enums to satisfy Mypy, although Pydantic allows strings
    law = Law(
        id="GXP.1",
        category=LawCategory.DOMAIN,
        text="No hallucinations.",
        # Mypy requires optional fields if they are not explicitly Optional with default?
        # No, 'source' has default None.
    )
    assert law.severity == LawSeverity.MEDIUM
    assert law.tags == []
    assert law.source is None


def test_constitution_model() -> None:
    law = Law(id="1", category=LawCategory.UNIVERSAL, text="test")
    const = Constitution(version="1.0", laws=[law])
    assert const.version == "1.0"
    assert len(const.laws) == 1


def test_archive_load_not_found(tmp_path: Path) -> None:
    archive = LegislativeArchive()
    with pytest.raises(FileNotFoundError):
        archive.load_from_directory(tmp_path / "nonexistent")


def test_archive_load_valid_json(tmp_path: Path) -> None:
    # Create a dummy JSON file with a Constitution object
    data = {
        "version": "1.0.0",
        "laws": [{"id": "GXP.1", "category": "Domain", "text": "Do not hallucinate.", "severity": "Critical"}],
    }

    d = tmp_path / "laws"
    d.mkdir()
    p = d / "laws.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    archive = LegislativeArchive()
    archive.load_from_directory(d)

    laws = archive.get_laws()
    assert len(laws) == 1
    assert laws[0].id == "GXP.1"
    assert archive.version == "1.0.0"


def test_archive_load_list_of_laws(tmp_path: Path) -> None:
    # Create a dummy JSON file with a list of laws
    data = [{"id": "TENANT.1", "category": "Tenant", "text": "No competitor mentions.", "severity": "Low"}]

    d = tmp_path / "laws_list"
    d.mkdir()
    p = d / "laws.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    archive = LegislativeArchive()
    archive.load_from_directory(d)

    laws = archive.get_laws()
    assert len(laws) == 1
    assert laws[0].id == "TENANT.1"


def test_archive_load_single_law(tmp_path: Path) -> None:
    data = {"id": "UNIV.2", "category": "Universal", "text": "Be polite.", "severity": "Low"}
    d = tmp_path / "single"
    d.mkdir()
    p = d / "law.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    archive = LegislativeArchive()
    archive.load_from_directory(d)
    assert len(archive.get_laws()) == 1
    assert archive.get_laws()[0].id == "UNIV.2"


def test_archive_filtering(tmp_path: Path) -> None:
    laws_data = [
        {"id": "U1", "category": "Universal", "text": "U1"},
        {"id": "D1", "category": "Domain", "text": "D1"},
        {"id": "T1", "category": "Tenant", "text": "T1"},
    ]
    d = tmp_path / "mixed"
    d.mkdir()
    p = d / "mixed.json"
    p.write_text(json.dumps(laws_data), encoding="utf-8")

    archive = LegislativeArchive()
    archive.load_from_directory(d)

    universal = archive.get_laws([LawCategory.UNIVERSAL])
    assert len(universal) == 1
    assert universal[0].id == "U1"

    domain_tenant = archive.get_laws([LawCategory.DOMAIN, LawCategory.TENANT])
    assert len(domain_tenant) == 2


def test_archive_invalid_json(tmp_path: Path) -> None:
    d = tmp_path / "bad"
    d.mkdir()
    p = d / "bad.json"
    p.write_text("{broken json", encoding="utf-8")

    archive = LegislativeArchive()
    with pytest.raises(ValueError):
        archive.load_from_directory(d)
