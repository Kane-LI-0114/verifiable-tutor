"""Parse a generated review document into self-check knowledge points.

The model writes a free-form Markdown chapter. The only fixed part is that
each knowledge point starts with an H2 heading and ends with an invisible page
comment. The parser splits those sections, extracts the page, and returns a
clean Markdown document that contains no internal comments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "DocumentError",
    "ParsedDocument",
    "RevisionPoint",
    "clean_markdown",
    "normalise_heading",
    "parse_document",
]

PAGE_COMMENT = re.compile(r"\s*<!--\s*page:\s*(\d+)\s*-->\s*")
PAGE_COMMENT_ONLY = re.compile(r"<!--\s*page:\s*\d+\s*-->")
HEADING = re.compile(r"^##[ \t]+(.+?)\s*$")


class DocumentError(ValueError):
    """The generated text cannot be used as a review document."""


@dataclass(frozen=True)
class RevisionPoint:
    title: str
    body_markdown: str
    page_no: int | None


@dataclass(frozen=True)
class ParsedDocument:
    intro_markdown: str
    points: tuple[RevisionPoint, ...]
    markdown: str


def normalise_heading(title: str) -> str:
    """Fold a heading to the key used for duplicate detection."""

    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def clean_markdown(
    intro: str, points: Sequence[RevisionPoint]
) -> str:
    """Rebuild the chapter without the internal page comments."""

    parts: list[str] = []
    if intro:
        parts.append(intro)
    for point in points:
        parts.append(f"## {point.title}\n\n{point.body_markdown}".rstrip())
    return "\n\n".join(parts).strip() + "\n"


def parse_document(text: str) -> ParsedDocument:
    """Split one generated chapter on its H2 headings."""

    intro_lines: list[str] = []
    body_lines: list[str] = []
    points: list[RevisionPoint] = []
    title: str | None = None
    page_no: int | None = None
    in_fence = False
    seen: set[str] = set()

    def close() -> None:
        nonlocal title, page_no, body_lines
        if title is None:
            return
        key = normalise_heading(title)
        if key and key not in seen:
            seen.add(key)
            body = PAGE_COMMENT_ONLY.sub("", "\n".join(body_lines)).strip()
            points.append(
                RevisionPoint(
                    title=title,
                    body_markdown=body,
                    page_no=page_no,
                )
            )
        title = None
        page_no = None
        body_lines = []

    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if match is not None:
            close()
            heading = match.group(1)
            page_match = PAGE_COMMENT.search(heading)
            page_no = int(page_match.group(1)) if page_match else None
            title = PAGE_COMMENT.sub("", heading).strip()
            if not title:
                raise DocumentError("a knowledge-point heading has no title")
            continue
        if title is None:
            intro_lines.append(line)
        else:
            body_lines.append(line)

    close()
    if not points:
        raise DocumentError("the document has no knowledge points")

    intro = PAGE_COMMENT_ONLY.sub("", "\n".join(intro_lines)).strip()
    return ParsedDocument(
        intro_markdown=intro,
        points=tuple(points),
        markdown=clean_markdown(intro, points),
    )
