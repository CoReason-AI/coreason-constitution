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
from typing import Any, Dict

import pytest

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.schema import Constitution, Law, LawCategory, LawSeverity


@pytest.fixture
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
    # Explicitly using Enums to satisfy Mypy
    law = Law(
        id="GXP.1",
        category=LawCategory.DOMAIN,
        text="No hallucinations.",
    )
    assert law.severity == LawSeverity.MEDIUM
    assert law.tags == []
    assert law.source is None


def test_law_empty_strings() -> None:
    # Test min_length constraint
    with pytest.raises(ValueError):
        Law(id="", category=LawCategory.UNIVERSAL, text="Valid text")

    with pytest.raises(ValueError):
        Law(id="VALID", category=LawCategory.UNIVERSAL, text="")


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


def test_archive_load_duplicate_ids(tmp_path: Path) -> None:
    # Create two files with same Law ID
    law1 = {
        "id": "DUP.1",
        "category": "Universal",
        "text": "First definition",
    }
    law2 = {
        "id": "DUP.1",
        "category": "Universal",
        "text": "Second definition",
    }

    d = tmp_path / "dups"
    d.mkdir()
    (d / "1.json").write_text(json.dumps(law1), encoding="utf-8")
    (d / "2.json").write_text(json.dumps(law2), encoding="utf-8")

    archive = LegislativeArchive()
    with pytest.raises(ValueError, match="Duplicate Law ID detected"):
        archive.load_from_directory(d)


def test_archive_recursive_loading(tmp_path: Path) -> None:
    d = tmp_path / "recursive"
    d.mkdir()
    sub = d / "subdir"
    sub.mkdir()

    (d / "root.json").write_text(
        json.dumps({"id": "ROOT.1", "category": "Universal", "text": "Root"}), encoding="utf-8"
    )

    (sub / "nested.json").write_text(
        json.dumps({"id": "NESTED.1", "category": "Universal", "text": "Nested"}), encoding="utf-8"
    )

    archive = LegislativeArchive()
    archive.load_from_directory(d)

    laws = archive.get_laws()
    ids = {law.id for law in laws}
    assert "ROOT.1" in ids
    assert "NESTED.1" in ids
    assert len(laws) == 2


def test_archive_unicode_support(tmp_path: Path) -> None:
    d = tmp_path / "unicode"
    d.mkdir()
    # Japanese text
    text = "こんにちは"
    (d / "jp.json").write_text(json.dumps({"id": "JP.1", "category": "Universal", "text": text}), encoding="utf-8")

    archive = LegislativeArchive()
    archive.load_from_directory(d)
    assert archive.get_laws()[0].text == text


def test_archive_mixed_content_types(tmp_path: Path) -> None:
    d = tmp_path / "mixed_types"
    d.mkdir()

    # 1. Full Constitution
    (d / "const.json").write_text(
        json.dumps({"version": "1.0", "laws": [{"id": "C.1", "category": "Universal", "text": "Const Law"}]}),
        encoding="utf-8",
    )

    # 2. List of Laws
    (d / "list.json").write_text(
        json.dumps([{"id": "L.1", "category": "Universal", "text": "List Law"}]), encoding="utf-8"
    )

    # 3. Single Law
    (d / "single.json").write_text(
        json.dumps({"id": "S.1", "category": "Universal", "text": "Single Law"}), encoding="utf-8"
    )

    archive = LegislativeArchive()
    archive.load_from_directory(d)

    assert len(archive.get_laws()) == 3
    ids = {law.id for law in archive.get_laws()}
    assert ids == {"C.1", "L.1", "S.1"}


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
