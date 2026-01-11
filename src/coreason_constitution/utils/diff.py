import difflib
from typing import Optional


def compute_unified_diff(
    original: str, revised: str, fromfile: str = "original", tofile: str = "revised"
) -> Optional[str]:
    """
    Computes a standard unified diff between two strings.

    :param original: The original text.
    :param revised: The modified text.
    :param fromfile: Label for the original source.
    :param tofile: Label for the revised source.
    :return: A string containing the unified diff, or None if there are no differences.
    """
    original_lines = original.splitlines(keepends=True)
    revised_lines = revised.splitlines(keepends=True)

    diff = list(difflib.unified_diff(original_lines, revised_lines, fromfile=fromfile, tofile=tofile, lineterm=""))

    if not diff:
        return None

    return "".join(diff)
