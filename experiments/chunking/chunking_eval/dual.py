"""Page-level fusion for two chunk granularities.

The lexical arm reads page-level chunks and the dense arm reads smaller
subchunks. Their chunk identifiers are not comparable, so both rankings are
converted to pages first, deduplicated, and fused with reciprocal rank fusion
at the page level.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

Page = tuple[str, int]


def page_ranking_from_chunks(chunks: Sequence[Mapping]) -> list[Page]:
    """Convert ranked chunks into a deduplicated page ranking."""

    seen: set[Page] = set()
    pages: list[Page] = []
    for chunk in chunks:
        doc_id = str(chunk.get("doc_id") or "")
        page_nos = chunk.get("page_nos") or [chunk.get("page_no")]
        for page_no in page_nos:
            if page_no is None:
                continue
            page = (doc_id, int(page_no))
            if page not in seen:
                seen.add(page)
                pages.append(page)
    return pages


def fuse_page_rankings(
    lexical_pages: Sequence[Page],
    dense_pages: Sequence[Page],
    *,
    k: int = 60,
    weights: tuple[float, float] = (1.0, 1.0),
) -> list[Page]:
    """Reciprocal rank fusion over two page rankings."""

    lexical_weight, dense_weight = weights
    scores: dict[Page, float] = {}
    for pages, weight in ((lexical_pages, lexical_weight), (dense_pages, dense_weight)):
        seen: set[Page] = set()
        for position, page in enumerate(pages, start=1):
            if page in seen:
                continue
            seen.add(page)
            scores[page] = scores.get(page, 0.0) + weight / (k + position)
    return sorted(scores, key=lambda page: (-scores[page], page[0], page[1]))


def page_chunks(
    pages: Sequence[Page], page_tokens: Mapping[Page, int]
) -> tuple[list[dict], dict[str, list[Page]]]:
    """Build one virtual chunk per selected page for the metric functions."""

    chunks: list[dict] = []
    page_map: dict[str, list[Page]] = {}
    for page in pages:
        chunk_id = f"page:{page[0]}:{page[1]}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "doc_id": page[0],
                "page_no": page[1],
                "page_nos": [page[1]],
                "token_estimate": int(page_tokens.get(page, 0)),
            }
        )
        page_map[chunk_id] = [page]
    return chunks, page_map
