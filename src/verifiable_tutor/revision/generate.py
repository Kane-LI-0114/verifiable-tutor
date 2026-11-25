"""Generate one review chapter from a document's OCR chunks.

Long documents are split into page-ordered batches. Each batch is one model
call, and the parsed points are merged in order with duplicate headings
dropped. The page comments never reach the stored Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..prompts import load_prompt
from .document import (
    DocumentError,
    RevisionPoint,
    clean_markdown,
    normalise_heading,
    parse_document,
)

__all__ = ["GeneratedDocument", "build_document"]

PROMPT_VERSION = "revision-document/2"
PROMPT = load_prompt("revision_document")
MAX_BATCH_CHARS = 12000


@dataclass(frozen=True)
class GeneratedDocument:
    intro_markdown: str
    points: tuple[RevisionPoint, ...]
    markdown: str
    batches: int


def _batches(
    chunks: Sequence[Mapping[str, Any]], limit: int = MAX_BATCH_CHARS
):
    batch: list[Mapping[str, Any]] = []
    size = 0
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        if batch and size + len(text) > limit:
            yield batch
            batch = []
            size = 0
        batch.append(chunk)
        size += len(text)
    if batch:
        yield batch


def _chunk_text(batch: Sequence[Mapping[str, Any]]) -> str:
    return "\n\n".join(
        f"[page {chunk.get('page_no')}]\n{chunk.get('text')}" for chunk in batch
    )


def _prompt(
    title: str, filename: str, batch: Sequence[Mapping[str, Any]]
) -> str:
    pages = sorted(
        {int(chunk["page_no"]) for chunk in batch if chunk.get("page_no")}
    )
    page_range = f"{pages[0]} to {pages[-1]}" if pages else "unknown"
    return (
        PROMPT.replace("%%TITLE%%", title)
        .replace("%%FILENAME%%", filename)
        .replace("%%PAGE_RANGE%%", page_range)
        .replace("%%CHUNKS%%", _chunk_text(batch))
    )


def build_document(
    *,
    title: str,
    filename: str,
    chunks: Sequence[Mapping[str, Any]],
    adapter: Any,
    overview: str | None = None,
) -> GeneratedDocument:
    """Generate the chapter and merge the per-batch knowledge points.

    A multi-batch chapter cannot use the first batch's overview, because that
    overview describes only the first pages. The caller passes the document
    summary instead, which covers the whole document.
    """

    if not chunks:
        raise DocumentError("the document has no OCR chunks")
    intro = ""
    points: list[RevisionPoint] = []
    seen: set[str] = set()
    batches = 0
    for batch in _batches(chunks):
        batches += 1
        result = adapter.chat(
            [{"role": "user", "content": _prompt(title, filename, batch)}],
            role="chat",
        )
        parsed = parse_document(getattr(result, "text", "") or "")
        if not intro and parsed.intro_markdown:
            intro = parsed.intro_markdown
        for point in parsed.points:
            key = normalise_heading(point.title)
            if not key or key in seen:
                continue
            seen.add(key)
            points.append(point)
    if not points:
        raise DocumentError("the document produced no knowledge points")
    if batches > 1:
        intro = (overview or "").strip()
    elif not intro:
        intro = (overview or "").strip()
    return GeneratedDocument(
        intro_markdown=intro,
        points=tuple(points),
        markdown=clean_markdown(intro, points),
        batches=batches,
    )
