"""Turn-scoped source registry for numbered citation markers.

One chat turn numbers the sources it retrieves so the model can cite them as
``[ref_n]``. A course page is identified by its document and page, a web source by
its URL without the fragment, and the first retrieval of a source fixes its
marker for the rest of the turn. The registry produces the same plain dicts the
history API and the stream frame carry.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

#: Longest summary one source row carries. A page keeps its leading text.
SOURCE_SUMMARY_CHARS = 200

#: Namespace that separates a citation marker from ordinary bracketed text.
CITATION_TOKEN_PREFIX = "ref_"

SourceKind = Literal["course", "web"]


def citation_token(marker: int) -> str:
    """The model-facing citation token for one 1-based source marker."""

    return f"[{CITATION_TOKEN_PREFIX}{marker}]"


def _summarise(text: str, limit: int) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 3)].rstrip() + "..."


def _web_identity(url: str) -> tuple[tuple[str, str, str, str], str] | None:
    """Return the dedupe key and fragment-free URL, or None for an unsafe URL."""

    parts = urlsplit((url or "").strip())
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.netloc:
        return None
    host = parts.netloc.lower()
    key = (scheme, host, parts.path or "/", parts.query)
    return key, urlunsplit((scheme, host, parts.path, parts.query, ""))


@dataclass(frozen=True)
class TurnSource:
    """One source a turn retrieved, with the marker the model cites."""

    marker: int
    kind: SourceKind
    title: str
    summary: str
    doc_id: str | None = None
    page_no: int | None = None
    url: str | None = None
    chunk_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "doc_id": self.doc_id,
            "page_no": self.page_no,
            "url": self.url,
            "chunk_id": self.chunk_id,
        }


class SourceRegistry:
    """Assign stable 1-based markers to the sources one chat turn retrieves."""

    def __init__(self, *, summary_chars: int = SOURCE_SUMMARY_CHARS) -> None:
        self._summary_chars = summary_chars
        self._order: list[TurnSource] = []
        self._by_key: dict[tuple[Any, ...], TurnSource] = {}
        self._course_texts: dict[tuple[Any, ...], list[str]] = {}

    def __len__(self) -> int:
        return len(self._order)

    def add_course(
        self,
        *,
        doc_id: str,
        page_no: int,
        title: str,
        text: str,
        chunk_id: str | None = None,
    ) -> TurnSource:
        key = ("course", doc_id, page_no)
        texts = self._course_texts.setdefault(key, [])
        if text and text not in texts:
            texts.append(text)
        summary = _summarise(" ".join(texts), self._summary_chars)
        existing = self._by_key.get(key)
        if existing is not None:
            updated = replace(
                existing,
                title=title or existing.title,
                summary=summary,
                chunk_id=existing.chunk_id or chunk_id,
            )
            self._by_key[key] = updated
            self._order[existing.marker - 1] = updated
            return updated
        source = TurnSource(
            marker=len(self._order) + 1,
            kind="course",
            title=title,
            summary=summary,
            doc_id=doc_id,
            page_no=page_no,
            chunk_id=chunk_id,
        )
        self._by_key[key] = source
        self._order.append(source)
        return source

    def add_web(self, *, url: str, title: str, summary: str) -> TurnSource | None:
        identity = _web_identity(url)
        if identity is None:
            return None
        key, clean_url = identity
        web_key = ("web", *key)
        existing = self._by_key.get(web_key)
        if existing is not None:
            # A fetched page carries a fuller summary than a search snippet;
            # keep the better one without changing the marker.
            better_summary = summary if len(summary) > len(existing.summary) else existing.summary
            updated = replace(
                existing,
                title=title or existing.title,
                summary=_summarise(better_summary, self._summary_chars),
            )
            self._by_key[web_key] = updated
            self._order[existing.marker - 1] = updated
            return updated
        source = TurnSource(
            marker=len(self._order) + 1,
            kind="web",
            title=title,
            summary=_summarise(summary, self._summary_chars),
            url=clean_url,
        )
        self._by_key[web_key] = source
        self._order.append(source)
        return source

    def snapshot(self) -> list[dict[str, Any]]:
        return [source.as_dict() for source in self._order]
