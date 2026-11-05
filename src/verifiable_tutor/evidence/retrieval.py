"""Hybrid retrieval: the FTS5 lexical arm and the BGE-M3 dense arm, fused.

The retriever returns chunks with their page and box metadata so a later stage
can turn a hit into a citation and inject excerpts into the prompt. It never
writes a citation and never touches a model prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ..corpus.store import KnowledgeStore
from .rrf import DEFAULT_K, reciprocal_rank_fusion
from .query import QueryPlan

#: Candidates each arm contributes before fusion.
ARM_LIMIT = 30


@dataclass
class RetrievalResult:
    chunks: list[dict[str, Any]] = field(default_factory=list)
    lexical: bool = False
    dense: bool = False
    plan: QueryPlan | None = None


class HybridRetriever:
    """Search the local store with both arms and return the fused top-k."""

    def __init__(
        self,
        *,
        store: KnowledgeStore,
        embedder: Any | None = None,
        k_rrf: int = DEFAULT_K,
        weights: Sequence[float] = (1.0, 1.0),
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._k = k_rrf
        self._weights = tuple(weights)
        self._cache_key: tuple[Any, ...] | None = None
        self._chunk_ids: list[str] = []
        self._matrix: np.ndarray | None = None

    def search(
        self, plan: QueryPlan, *, k: int = 8, doc_id: str | None = None
    ) -> RetrievalResult:
        if not plan.need_retrieval:
            return RetrievalResult(plan=plan)

        lexical_ids = [
            hit["chunk_id"]
            for hit in self._store.search_chunks(
                plan.keyword_query or plan.question,
                limit=ARM_LIMIT,
                doc_id=doc_id,
            )
        ]

        dense_ids: list[str] = []
        matrix = self._dense_matrix()
        if matrix is not None and self._embedder is not None and plan.semantic_queries:
            try:
                query = np.asarray(
                    self._embedder.embed([plan.semantic_queries[0]])[0],
                    dtype=np.float32,
                )
            except Exception:  # the dense arm is best effort
                query = None
            if query is not None and query.shape[0] == matrix.shape[1]:
                norm = float(np.linalg.norm(query))
                if norm > 0.0:
                    scores = matrix @ (query / norm)
                    order = np.argsort(-scores)[:ARM_LIMIT]
                    dense_ids = [self._chunk_ids[index] for index in order]

        if not lexical_ids and not dense_ids:
            return RetrievalResult(plan=plan)

        fused = reciprocal_rank_fusion(
            [lexical_ids, dense_ids], k=self._k, weights=self._weights
        )
        sources: dict[str, list[str]] = {}
        for chunk_id in lexical_ids:
            sources.setdefault(chunk_id, []).append("lexical")
        for chunk_id in dense_ids:
            sources.setdefault(chunk_id, []).append("dense")

        ordered = [hit.chunk_id for hit in fused[:k]]
        by_id = {chunk["chunk_id"]: chunk for chunk in self._store.get_chunks(ordered)}
        scores = {hit.chunk_id: hit.score for hit in fused}
        chunks = []
        for chunk_id in ordered:
            chunk = by_id.get(chunk_id)
            if chunk is None:
                continue
            chunks.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "doc_id": chunk["doc_id"],
                    "page_no": chunk["page_no"],
                    "section": chunk.get("section_title"),
                    "text": chunk["text"],
                    "bbox_norm": chunk.get("bbox_norm"),
                    "score": scores[chunk_id],
                    "sources": sources.get(chunk_id, []),
                }
            )
        return RetrievalResult(
            chunks=chunks,
            lexical=bool(lexical_ids),
            dense=bool(dense_ids),
            plan=plan,
        )

    # -- dense matrix ------------------------------------------------------
    def _dense_matrix(self) -> np.ndarray | None:
        state = self._store.index_state()
        key = (
            state.get("chunks"),
            state.get("dimension"),
            state.get("model"),
            state.get("chunker_version"),
            state.get("built_at"),
        )
        if key != self._cache_key:
            self._cache_key = key
            self._chunk_ids, self._matrix = self._load_matrix()
        return self._matrix

    def _load_matrix(self) -> tuple[list[str], np.ndarray | None]:
        chunk_ids, blobs = self._store.stored_vectors()
        if not blobs:
            return [], None
        rows = [np.frombuffer(blob, dtype=np.float32) for blob in blobs]
        if len({row.shape[0] for row in rows}) != 1:
            return [], None
        matrix = np.vstack(rows).astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return chunk_ids, matrix / norms
