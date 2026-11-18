"""Three retrieval modes over the experiment store.

Hybrid reuses the production ``HybridRetriever`` unchanged. Lexical and dense
are implemented here so the ablation uses the same store, tokenizer, embedding
model, and top-k convention as the hybrid arm. The dense matrix and the hybrid
retriever are built once per cell and reused across questions; rebuilding them
per question would dominate the run time.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from verifiable_tutor.evidence.query import fallback_plan
from verifiable_tutor.evidence.retrieval import HybridRetriever

from .index import EvalStore


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


class DenseSearcher:
    """One materialised dense matrix for a cell."""

    def __init__(self, store: EvalStore, embedder: Any) -> None:
        self.store = store
        self.embedder = embedder
        self.chunk_ids, blobs = store.stored_vectors()
        rows = [np.frombuffer(blob, dtype=np.float32) for blob in blobs]
        self.matrix = None
        if rows and len({row.shape[0] for row in rows}) == 1:
            self.matrix = _normalise(np.vstack(rows).astype(np.float32))

    def search(
        self, query: str, *, k: int, doc_id: str | None = None
    ) -> list[dict[str, Any]]:
        if self.matrix is None or not self.chunk_ids:
            return []
        vector = np.asarray(self.embedder.embed([query])[0], dtype=np.float32)
        if vector.shape[0] != self.matrix.shape[1]:
            return []
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return []
        scores = self.matrix @ (vector / norm)
        order = np.argsort(-scores)
        if doc_id is not None:
            metadata = self.store.get_chunks(self.chunk_ids)
            allowed = {item["chunk_id"] for item in metadata if item["doc_id"] == doc_id}
            order = [index for index in order if self.chunk_ids[index] in allowed]
        ordered_ids = [self.chunk_ids[index] for index in order[:k]]
        return self.store.get_chunks(ordered_ids)


def make_hybrid(store: EvalStore, embedder: Any) -> HybridRetriever:
    return HybridRetriever(store=store, embedder=embedder)


def search_lexical(store: EvalStore, query: str, *, k: int) -> list[dict[str, Any]]:
    return store.search_chunks(query, limit=k)


def search(
    store: EvalStore,
    embedder: Any,
    query: str,
    *,
    mode: str,
    k: int,
    doc_id: str | None = None,
    dense: DenseSearcher | None = None,
    hybrid: HybridRetriever | None = None,
) -> list[dict[str, Any]]:
    if mode == "lexical":
        return search_lexical(store, query, k=k)
    if mode == "dense":
        searcher = dense or DenseSearcher(store, embedder)
        return searcher.search(query, k=k, doc_id=doc_id)
    if mode == "hybrid":
        retriever = hybrid or make_hybrid(store, embedder)
        result = retriever.search(fallback_plan(query), k=k, doc_id=doc_id)
        return list(result.chunks)
    raise ValueError(f"unknown retrieval mode: {mode!r}")
