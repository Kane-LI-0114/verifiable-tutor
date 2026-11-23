"""Lexical, dense, and hybrid retrieval over the experiment store."""

from __future__ import annotations

import numpy as np

from chunking_eval.index import EvalStore
from chunking_eval.retrieval import search


class FakeEmbedder:
    def __init__(self) -> None:
        self._vectors = {
            "alpha": [1.0, 0.0],
            "beta": [0.0, 1.0],
        }

    def embed(self, texts):
        return [self._vectors[text] for text in texts]


def chunk(chunk_id: str, text: str, page_no: int) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": "doc",
        "page_no": page_no,
        "page_nos": [page_no],
        "chunk_index": 0,
        "section_title": "Section",
        "text": text,
        "embed_text": text,
        "token_estimate": 10,
        "oversize": False,
        "chunker_version": "eval/test/1",
    }


def build_store(tmp_path, embedder: FakeEmbedder) -> EvalStore:
    store = EvalStore(tmp_path / "index.db")
    store.add_chunks([chunk("c1", "alpha", 1), chunk("c2", "beta", 2)])
    store.set_embeddings(
        "doc",
        {
            "c1": np.asarray([1.0, 0.0], dtype=np.float32).tobytes(),
            "c2": np.asarray([0.0, 1.0], dtype=np.float32).tobytes(),
        },
        model="fake",
        built_at="2026-11-18T00:00:00",
    )
    return store


def test_lexical_dense_and_hybrid_rank_the_matching_chunk_first(tmp_path) -> None:
    embedder = FakeEmbedder()
    store = build_store(tmp_path, embedder)

    for mode in ("lexical", "dense", "hybrid"):
        hits = search(store, embedder, "alpha", mode=mode, k=2)
        assert hits[0]["chunk_id"] == "c1"


def test_hybrid_uses_both_arms(tmp_path) -> None:
    embedder = FakeEmbedder()
    store = build_store(tmp_path, embedder)

    hits = search(store, embedder, "alpha", mode="hybrid", k=2)

    assert len(hits) == 2
    assert hits[0]["chunk_id"] == "c1"


def test_hybrid_weights_choose_the_preferred_arm(tmp_path) -> None:
    embedder = FakeEmbedder()
    store = EvalStore(tmp_path / "weights.db")
    store.add_chunks([chunk("c1", "alpha", 1), chunk("c2", "beta", 2)])
    store.set_embeddings(
        "doc",
        {
            "c1": np.asarray([0.0, 1.0], dtype=np.float32).tobytes(),
            "c2": np.asarray([1.0, 0.0], dtype=np.float32).tobytes(),
        },
        model="fake",
        built_at="2026-11-18T00:00:00",
    )

    dense_heavy = search(
        store, embedder, "alpha", mode="hybrid", k=2, weights=(1.0, 1000.0)
    )
    lexical_heavy = search(
        store, embedder, "alpha", mode="hybrid", k=2, weights=(1000.0, 1.0)
    )

    assert dense_heavy[0]["chunk_id"] == "c2"
    assert lexical_heavy[0]["chunk_id"] == "c1"
