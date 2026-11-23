"""Page-level retrieval metrics.

The retrieval unit is a chunk, but the citation and preview unit is a page.
Every metric therefore expands the ranked chunks into a ranked page list first:
pages are deduplicated and keep the rank of their first occurrence. A chunk
that covers several pages contributes all of its pages in ascending order.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

PageKey = tuple[str, int]


def page_sequence(
    chunks: Sequence[Mapping], page_map: Mapping[str, Sequence[PageKey]]
) -> list[PageKey]:
    """Expand ranked chunks into ranked pages, keeping first occurrences."""

    seen: set[PageKey] = set()
    pages: list[PageKey] = []
    for chunk in chunks:
        for page in page_map.get(str(chunk.get("chunk_id")), ()):
            key = (str(page[0]), int(page[1]))
            if key not in seen:
                seen.add(key)
                pages.append(key)
    return pages


def page_hit_at_k(
    chunks: Sequence[Mapping],
    page_map: Mapping[str, Sequence[PageKey]],
    gold_pages: Iterable[PageKey],
    k: int,
) -> bool:
    gold = {(str(doc), int(page)) for doc, page in gold_pages}
    return any(page in gold for page in page_sequence(chunks, page_map)[:k])


def ndcg_at_k(
    chunks: Sequence[Mapping],
    page_map: Mapping[str, Sequence[PageKey]],
    gold_pages: Iterable[PageKey],
    k: int,
) -> float:
    gold = {(str(doc), int(page)) for doc, page in gold_pages}
    if not gold or k <= 0:
        return 0.0
    pages = page_sequence(chunks, page_map)[:k]
    dcg = sum(
        1.0 / math.log2(position + 1)
        for position, page in enumerate(pages, start=1)
        if page in gold
    )
    ideal_hits = min(len(gold), k)
    idcg = sum(1.0 / math.log2(position + 1) for position in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def mrr(
    chunks: Sequence[Mapping],
    page_map: Mapping[str, Sequence[PageKey]],
    gold_pages: Iterable[PageKey],
) -> float:
    gold = {(str(doc), int(page)) for doc, page in gold_pages}
    for position, page in enumerate(page_sequence(chunks, page_map), start=1):
        if page in gold:
            return 1.0 / position
    return 0.0


def context_tokens_at_k(
    chunks: Sequence[Mapping],
    page_map: Mapping[str, Sequence[PageKey]],
    k: int,
) -> int:
    """Tokens consumed by the shortest chunk prefix that yields k pages."""

    seen: set[PageKey] = set()
    tokens = 0
    for chunk in chunks:
        tokens += int(chunk.get("token_estimate") or 0)
        for page in page_map.get(str(chunk.get("chunk_id")), ()):
            seen.add((str(page[0]), int(page[1])))
        if len(seen) >= k:
            return tokens
    return tokens


def evaluate_rankings(
    chunks: Sequence[Mapping],
    page_map: Mapping[str, Sequence[PageKey]],
    gold_pages: Iterable[PageKey],
    *,
    ks: Sequence[int] = (3, 5, 10),
) -> dict[str, float | bool | int]:
    gold = {(str(doc), int(page)) for doc, page in gold_pages}
    result: dict[str, float | bool | int] = {
        "mrr": mrr(chunks, page_map, gold),
    }
    for k in ks:
        result[f"hit@{k}"] = page_hit_at_k(chunks, page_map, gold, k)
        result[f"ndcg@{k}"] = ndcg_at_k(chunks, page_map, gold, k)
        result[f"context_tokens@{k}"] = context_tokens_at_k(chunks, page_map, k)
    return result
