import json
from pathlib import Path
from typing import List, Optional, Set

from coreason_constitution.schema import Constitution, Law, LawCategory
from coreason_constitution.utils.logger import logger


class LegislativeArchive:
    def __init__(self) -> None:
        self._laws: List[Law] = []
        self._version: str = "0.0.0"

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

        # Use rglob for recursive search
        for file_path in path.rglob("*.json"):
            try:
                content = json.loads(file_path.read_text(encoding="utf-8"))
                new_laws: List[Law] = []

                # Handle if the file is a full Constitution object
                if isinstance(content, dict) and "laws" in content and "version" in content:
                    const = Constitution(**content)
                    new_laws.extend(const.laws)
                    # Simple version handling: take the last one or keep default if multiple
                    self._version = const.version

                # Handle if the file is just a list of laws
                elif isinstance(content, list):
                    for item in content:
                        new_laws.append(Law(**item))

                # Handle single law object
                elif isinstance(content, dict):
                    new_laws.append(Law(**content))

                # Check for duplicates before adding
                for law in new_laws:
                    if law.id in loaded_ids:
                        msg = f"Duplicate Law ID detected: {law.id} in {file_path}"
                        logger.error(msg)
                        raise ValueError(msg)
                    loaded_ids.add(law.id)
                    loaded_laws.append(law)

                logger.info(f"Loaded laws from {file_path}")

            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                raise ValueError(f"Failed to parse {file_path}: {e}") from e

        self._laws = loaded_laws
        logger.info(f"LegislativeArchive loaded {len(self._laws)} laws total.")

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
