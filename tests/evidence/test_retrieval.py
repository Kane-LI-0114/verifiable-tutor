"""Hybrid retrieval seam: lexical plus dense fused by reciprocal rank.

The expected order is computed by hand from the two arm rankings, so it does not
repeat the fusion algorithm.
"""

from __future__ import annotations

from datetime import datetime, timezone

import struct

from verifiable_tutor.corpus.store import KnowledgeStore
from verifiable_tutor.evidence.query import fallback_plan
from verifiable_tutor.evidence.retrieval import HybridRetriever
from verifiable_tutor.storage import Storage

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-11-05T12:00:00+00:00"


def _vector(*values: float) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def _seed(store: KnowledgeStore, doc_id: str, chunks: list[tuple[str, str, str]]) -> None:
    document = {
        "id": doc_id,
        "title": doc_id,
        "filename": f"{doc_id}.pdf",
        "pdf_sha256": f"sha-{doc_id}",
        "page_count": 1,
        "pdf_path": f"pdf/{doc_id}.pdf",
        "status": "ready",
        "indexed_at": STAMP,
        "created_at": STAMP,
        "updated_at": STAMP,
    }
    records = [
        {
            "schema": "vt-chunk-record/1",
            "chunker_version": "vt-chunker/1",
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "page_no": 1,
            "chunk_index": index,
            "section_title": None,
            "text": text,
            "embed_text": text,
            "block_ids": [index],
            "label_types": ["text"],
            "bbox_norm": [0.0, 0.0, 1.0, 1.0],
            "token_estimate": 4,
            "oversize": False,
        }
        for index, (chunk_id, text, _) in enumerate(chunks)
    ]
    store.upsert_document(document, records)
    store.set_embeddings(
        doc_id,
        {chunk_id: _vector(*[1.0, 0.0]) for chunk_id, _, _ in chunks},
        model="fake",
        built_at=STAMP,
    )


def _store_with_three_chunks(tmp_path) -> KnowledgeStore:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    store = KnowledgeStore(storage)
    _seed(
        store,
        "ACS_Lecture_1_2026F",
        [
            ("ACS_Lecture_1_2026F:p001:c00", "GPU scheduling and occupancy.", "dense"),
            ("ACS_Lecture_1_2026F:p001:c01", "The allreduce operation.", "both"),
            ("ACS_Lecture_1_2026F:p001:c02", "allreduce latency on shared memory.", "lexical"),
        ],
    )
    # Dense order: A=[1,0] then B=[0.6,0.8] then C=[0,1].
    store.set_embeddings(
        "ACS_Lecture_1_2026F",
        {
            "ACS_Lecture_1_2026F:p001:c00": _vector(1.0, 0.0),
            "ACS_Lecture_1_2026F:p001:c01": _vector(0.6, 0.8),
            "ACS_Lecture_1_2026F:p001:c02": _vector(0.0, 1.0),
        },
        model="fake",
        built_at=STAMP,
    )
    return store


class FakeEmbedder:
    def __init__(self) -> None:
        self.available = True

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


def test_a_chunk_both_arms_rank_beats_a_chunk_only_the_dense_arm_found(tmp_path) -> None:
    store = _store_with_three_chunks(tmp_path)
    retriever = HybridRetriever(store=store, embedder=FakeEmbedder())

    result = retriever.search(fallback_plan("allreduce"), k=3)

    # Lexical: [c01, c02]; dense: [c00, c01, c02].
    # c01 = 1/62 + 1/62 = 0.032258, c02 = 1/63 + 1/63 = 0.031746, c00 = 1/61.
    assert [chunk["chunk_id"] for chunk in result.chunks] == [
        "ACS_Lecture_1_2026F:p001:c01",
        "ACS_Lecture_1_2026F:p001:c02",
        "ACS_Lecture_1_2026F:p001:c00",
    ]
    assert result.lexical is True
    assert result.dense is True
    assert "dense" in result.chunks[0]["sources"]
    assert "lexical" in result.chunks[0]["sources"]
    assert result.chunks[0]["page_no"] == 1
    assert result.chunks[0]["doc_id"] == "ACS_Lecture_1_2026F"


def test_without_vectors_retrieval_falls_back_to_the_lexical_arm(tmp_path) -> None:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    store = KnowledgeStore(storage)
    _seed(
        store,
        "Tutorial_2",
        [("Tutorial_2:p001:c00", "Shared memory tiling.", "lexical")],
    )

    result = HybridRetriever(store=store, embedder=None).search(
        fallback_plan("tiling"), k=3
    )

    assert [chunk["chunk_id"] for chunk in result.chunks] == ["Tutorial_2:p001:c00"]
    assert result.lexical is True
    assert result.dense is False
