"""Reciprocal rank fusion over two or more ranked chunk lists.

Each arm contributes ``weight / (k + rank)`` with a one-based rank, so a chunk
that both arms rank highly outranks one that only a single arm found. The
fusion is a pure function so the ranking maths is testable without a store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

DEFAULT_K = 60


@dataclass(frozen=True)
class FusedHit:
    chunk_id: str
    score: float


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]],
    *,
    k: int = DEFAULT_K,
    weights: Sequence[float] | None = None,
) -> list[FusedHit]:
    """Fuse ranked chunk-id lists into one list ordered by fused score."""

    if k < 1:
        raise ValueError("k must be at least 1")
    resolved = list(weights) if weights is not None else [1.0] * len(rankings)
    resolved.extend([1.0] * (len(rankings) - len(resolved)))
    scores: dict[str, float] = {}
    for arm, ranking in enumerate(rankings):
        weight = float(resolved[arm])
        seen: set[str] = set()
        for position, chunk_id in enumerate(ranking, start=1):
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + position)
    fused = [
        FusedHit(chunk_id=chunk_id, score=round(score, 6))
        for chunk_id, score in scores.items()
    ]
    fused.sort(key=lambda hit: (-hit.score, hit.chunk_id))
    return fused
