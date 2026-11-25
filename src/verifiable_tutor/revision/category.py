"""Document category from a file name.

The corpus has no folder rows in a local import, so the file name is the only
stable signal. Precedence matters: "Assignment" wins over a word such as
"lecture" appearing in the same name.
"""

from __future__ import annotations

__all__ = ["document_category"]


def document_category(name: str) -> str:
    """Return assignment, lecture, tutorial, or other for one file name."""

    lowered = (name or "").lower()
    if "assign" in lowered:
        return "assignment"
    if "lecture" in lowered:
        return "lecture"
    if "tutorial" in lowered or "toturial" in lowered:
        return "tutorial"
    return "other"
