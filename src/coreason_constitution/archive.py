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
from typing import List, Optional, Set

from pydantic import TypeAdapter, ValidationError

from coreason_constitution.schema import Artifact, Constitution, Law, LawCategory, Reference, SentinelRule
from coreason_constitution.utils.logger import logger


class LegislativeArchive:
    def __init__(self) -> None:
        self._laws: List[Law] = []
        self._sentinel_rules: List[SentinelRule] = []
        self._references: List[Reference] = []
        self._version: str = "0.0.0"

    def load_defaults(self) -> None:
        """
        Loads the default laws and sentinel rules packaged with the library.
        These are located in src/coreason_constitution/defaults.
        """
        defaults_path = Path(__file__).parent / "defaults"
        if defaults_path.exists():
            logger.info(f"Loading defaults from {defaults_path}")
            self.load_from_directory(defaults_path)
        else:
            logger.warning(f"Defaults directory not found at {defaults_path}")

    def load_from_directory(self, directory_path: str | Path) -> None:
        """
        Loads laws from all JSON files in the specified directory recursively.
        Files should adhere to the Constitution schema or be a list of Law objects.
        Raises ValueError if duplicate Law IDs are detected.
        """
        path = Path(directory_path)
        if not path.exists():
            logger.error(f"Directory not found: {path}")
            raise FileNotFoundError(f"Directory not found: {path}")

        loaded_laws: List[Law] = []
        loaded_ids: Set[str] = set()
        loaded_sentinel_rules: List[SentinelRule] = []
        loaded_rule_ids: Set[str] = set()
        loaded_references: List[Reference] = []
        loaded_ref_ids: Set[str] = set()

        adapter: TypeAdapter[Artifact] = TypeAdapter(Artifact)

        # Use rglob for recursive search
        for file_path in path.rglob("*.json"):
            try:
                # Read file content
                content_text = file_path.read_text(encoding="utf-8")
                content = json.loads(content_text)

                # Use Pydantic TypeAdapter to parse the content
                try:
                    parsed_obj = adapter.validate_python(content)
                except ValidationError as ve:
                    # Try to give a more helpful error if possible, or just raise
                    # This handles the case where it doesn't match any of the Union types
                    raise ValueError(f"Validation failed for {file_path}: {ve}") from ve

                new_laws: List[Law] = []
                new_rules: List[SentinelRule] = []
                new_references: List[Reference] = []

                if isinstance(parsed_obj, Constitution):
                    new_laws.extend(parsed_obj.laws)
                    new_rules.extend(parsed_obj.sentinel_rules)
                    new_references.extend(parsed_obj.references)
                    self._version = parsed_obj.version

                elif isinstance(parsed_obj, list):
                    for item in parsed_obj:
                        if isinstance(item, SentinelRule):
                            new_rules.append(item)
                        elif isinstance(item, Law):
                            new_laws.append(item)
                        elif isinstance(item, Reference):
                            new_references.append(item)

                elif isinstance(parsed_obj, SentinelRule):
                    new_rules.append(parsed_obj)

                elif isinstance(parsed_obj, Law):
                    new_laws.append(parsed_obj)

                elif isinstance(parsed_obj, Reference):
                    new_references.append(parsed_obj)

                # Check for duplicates before adding laws
                for law in new_laws:
                    if law.id in loaded_ids:
                        msg = f"Duplicate Law ID detected: {law.id} in {file_path}"
                        logger.error(msg)
                        raise ValueError(msg)
                    loaded_ids.add(law.id)
                    loaded_laws.append(law)

                # Check for duplicates before adding sentinel rules
                for rule in new_rules:
                    if rule.id in loaded_rule_ids:
                        msg = f"Duplicate Sentinel Rule ID detected: {rule.id} in {file_path}"
                        logger.error(msg)
                        raise ValueError(msg)
                    loaded_rule_ids.add(rule.id)
                    loaded_sentinel_rules.append(rule)

                # Check for duplicates before adding references
                for ref in new_references:
                    if ref.id in loaded_ref_ids:
                        msg = f"Duplicate Reference ID detected: {ref.id} in {file_path}"
                        logger.error(msg)
                        raise ValueError(msg)
                    loaded_ref_ids.add(ref.id)
                    loaded_references.append(ref)

                logger.info(f"Loaded content from {file_path}")

            except Exception as e:
                # Catch-all for JSONDecodeError or other file read issues, and re-raise as ValueError
                # to maintain the existing API contract
                logger.error(f"Failed to load {file_path}: {e}")
                raise ValueError(f"Failed to parse {file_path}: {e}") from e

        self._laws = loaded_laws
        self._sentinel_rules = loaded_sentinel_rules
        self._references = loaded_references
        logger.info(
            f"LegislativeArchive loaded {len(self._laws)} laws, "
            f"{len(self._sentinel_rules)} rules, and {len(self._references)} references."
        )

    def get_sentinel_rules(self) -> List[SentinelRule]:
        """Retrieve all loaded sentinel rules."""
        return self._sentinel_rules

    def get_references(self, context_tags: Optional[List[str]] = None) -> List[Reference]:
        """
        Retrieve references, optionally filtered by context tags.

        :param context_tags: List of strings representing the current context (e.g. ["tenant:acme"]).
                             If provided, a reference is included ONLY if:
                             1. It has NO tags (Universal application), OR
                             2. At least one of its tags exists in `context_tags`.
                             If None, all references are included.
        :return: List of filtered Reference objects.
        """
        filtered_refs = self._references

        # Filter by Context Tags
        if context_tags is not None:
            context_set = set(context_tags)
            filtered_refs = [ref for ref in filtered_refs if not ref.tags or not set(ref.tags).isdisjoint(context_set)]

        return filtered_refs

    def get_laws(
        self,
        categories: Optional[List[LawCategory]] = None,
        context_tags: Optional[List[str]] = None,
    ) -> List[Law]:
        """
        Retrieve laws, optionally filtered by category and context tags.

        :param categories: List of LawCategory to include. If None, all categories are included.
        :param context_tags: List of strings representing the current context (e.g. ["tenant:acme"]).
                             If provided, a law is included ONLY if:
                             1. It has NO tags (Universal application), OR
                             2. At least one of its tags exists in `context_tags`.
                             If None, all laws are included (subject to category filter).
        :return: List of filtered Law objects.
        """
        filtered_laws = self._laws

        # 1. Filter by Category
        if categories:
            filtered_laws = [law for law in filtered_laws if law.category in categories]

        # 2. Filter by Context Tags
        if context_tags is not None:
            # Optimize by converting to set for O(1) lookups
            context_set = set(context_tags)
            filtered_laws = [law for law in filtered_laws if not law.tags or not set(law.tags).isdisjoint(context_set)]

        return filtered_laws

    @property
    def version(self) -> str:
        return self._version
