"""Knowledge store seam: documents, folders, chunks, full-text search, index state.

Expected values are literals from the contract in ``docs/physical-data-model.md``
and ``docs/knowledge-schema.md``, not values recomputed the way the store does.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from verifiable_tutor.corpus.store import KnowledgeStore
from verifiable_tutor.storage import SCHEMA_VERSION, Storage

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-11-05T12:00:00+00:00"


def make_store(tmp_path) -> KnowledgeStore:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    return KnowledgeStore(storage)


def document(doc_id: str = "ACS_Lecture_1_2026F", **overrides) -> dict:
    values = {
        "id": doc_id,
        "title": doc_id,
        "filename": f"{doc_id}.pdf",
        "pdf_sha256": f"sha-{doc_id}",
        "byte_size": 10_470_744,
        "page_count": 2,
        "pdf_path": f"data/corpus/pdf/{doc_id}.pdf",
        "thumbnail_path": f"data/corpus/images/{doc_id}.p001.webp",
        "status": "ready",
        "indexed_at": STAMP,
        "created_at": STAMP,
        "updated_at": STAMP,
    }
    values.update(overrides)
    return values


def chunk(doc_id: str, page_no: int, index: int, text: str, **overrides) -> dict:
    values = {
        "schema": "vt-chunk-record/1",
        "chunker_version": "vt-chunker/1",
        "chunk_id": f"{doc_id}:p{page_no:03d}:c{index:02d}",
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_index": index,
        "section_title": None,
        "text": text,
        "embed_text": text,
        "block_ids": [1],
        "label_types": ["text"],
        "bbox_norm": [0.1, 0.1, 0.9, 0.2],
        "token_estimate": len(text) // 4,
        "oversize": False,
    }
    values.update(overrides)
    return values


def test_initialize_creates_the_knowledge_tables_and_bumps_the_version(tmp_path) -> None:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()

    with sqlite3.connect(storage.path) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert {
        "kb_folders",
        "kb_documents",
        "kb_chunks",
        "kb_chunks_fts",
        "kb_index_state",
    } <= names
    assert version == SCHEMA_VERSION == 7


def test_a_stored_document_can_be_read_back_with_its_chunks(tmp_path) -> None:
    store = make_store(tmp_path)

    store.upsert_document(
        document(),
        [
            chunk("ACS_Lecture_1_2026F", 1, 0, "Dense retrieval maps queries to vectors."),
            chunk("ACS_Lecture_1_2026F", 2, 0, "BM25 ranks by term overlap."),
        ],
    )

    stored = store.get_document("ACS_Lecture_1_2026F")
    assert stored["title"] == "ACS_Lecture_1_2026F"
    assert stored["chunk_count"] == 2
    assert stored["page_count"] == 2
    assert stored["status"] == "ready"
    assert stored["folder_id"] is None
    assert [item["chunk_id"] for item in store.list_chunks("ACS_Lecture_1_2026F")] == [
        "ACS_Lecture_1_2026F:p001:c00",
        "ACS_Lecture_1_2026F:p002:c00",
    ]


def test_page_chunks_returns_one_page_in_reading_order(tmp_path) -> None:
    store = make_store(tmp_path)
    store.upsert_document(
        document(),
        [
            chunk("ACS_Lecture_1_2026F", 1, 0, "first part"),
            chunk("ACS_Lecture_1_2026F", 1, 1, "second part"),
            chunk("ACS_Lecture_1_2026F", 2, 0, "other page"),
        ],
    )

    page = store.page_chunks("ACS_Lecture_1_2026F", 1)

    assert [item["chunk_index"] for item in page] == [0, 1]
    assert [item["text"] for item in page] == ["first part", "second part"]
    assert store.page_chunks("ACS_Lecture_1_2026F", 9) == []


def test_storing_the_same_document_twice_replaces_its_chunks_and_search_rows(
    tmp_path,
) -> None:
    store = make_store(tmp_path)
    store.upsert_document(document(), [chunk("ACS_Lecture_1_2026F", 1, 0, "alpha beta")])
    store.upsert_document(document(), [chunk("ACS_Lecture_1_2026F", 1, 0, "gamma delta")])

    assert store.get_document("ACS_Lecture_1_2026F")["chunk_count"] == 1
    assert store.search_chunks("alpha", limit=5) == []
    assert len(store.search_chunks("gamma", limit=5)) == 1


def test_soft_deleting_a_folder_hides_rows_but_keeps_the_chunks(tmp_path) -> None:
    store = make_store(tmp_path)
    folder = store.create_folder(name="Lectures", parent_id=None, created_at=STAMP)
    store.upsert_document(
        document(), [chunk("ACS_Lecture_1_2026F", 1, 0, "dense vectors")]
    )
    store.set_document_folder("ACS_Lecture_1_2026F", folder["id"])

    hidden = store.delete_folder(folder["id"], deleted_at=STAMP)

    assert hidden == 1
    assert store.get_document("ACS_Lecture_1_2026F") is None
    assert store.get_folder(folder["id"]) is None
    assert store.search_chunks("dense", limit=5) == []
    assert len(store.list_chunks("ACS_Lecture_1_2026F")) == 1


def test_soft_deleting_a_document_keeps_its_row_and_chunks(tmp_path) -> None:
    store = make_store(tmp_path)
    store.upsert_document(document(), [chunk("ACS_Lecture_1_2026F", 1, 0, "kept text")])

    deleted = store.delete_document("ACS_Lecture_1_2026F", deleted_at=STAMP)

    assert deleted["id"] == "ACS_Lecture_1_2026F"
    assert store.get_document("ACS_Lecture_1_2026F") is None
    assert store.list_documents()[0] == []
    assert len(store.list_chunks("ACS_Lecture_1_2026F")) == 1


def test_search_returns_only_chunks_that_contain_the_term(tmp_path) -> None:
    store = make_store(tmp_path)
    store.upsert_document(
        document("ACS_lecture_2_2026F"),
        [
            chunk("ACS_lecture_2_2026F", 1, 0, "The allreduce operation combines gradients."),
            chunk("ACS_lecture_2_2026F", 2, 0, "Shared memory tiling reduces traffic."),
        ],
    )

    hits = store.search_chunks("allreduce", limit=5)

    assert [hit["chunk_id"] for hit in hits] == ["ACS_lecture_2_2026F:p001:c00"]
    assert hits[0]["doc_id"] == "ACS_lecture_2_2026F"
    assert hits[0]["page_no"] == 1


def test_search_falls_back_to_any_term_when_the_full_query_does_not_match(tmp_path) -> None:
    store = make_store(tmp_path)
    store.upsert_document(
        document("ACS_Lecture_1_2026F"),
        [chunk("ACS_Lecture_1_2026F", 1, 0, "The allreduce operation combines gradients.")],
    )

    # A rewritten query usually carries terms the slide does not contain; an
    # all-terms match would drop a hit that shares the important one.
    hits = store.search_chunks(
        "allreduce collective communication operation", limit=5
    )

    assert [hit["chunk_id"] for hit in hits] == ["ACS_Lecture_1_2026F:p001:c00"]


def test_a_folder_cannot_move_under_its_own_child(tmp_path) -> None:
    store = make_store(tmp_path)
    parent = store.create_folder(name="Lectures", parent_id=None, created_at=STAMP)
    child = store.create_folder(
        name="Week 1", parent_id=parent["id"], created_at=STAMP
    )

    with pytest.raises(ValueError, match="descendant"):
        store.move_folder(parent["id"], parent_id=child["id"])

    assert store.get_folder(parent["id"])["parent_id"] is None


def test_index_state_counts_the_chunks_that_carry_vectors(tmp_path) -> None:
    store = make_store(tmp_path)
    store.upsert_document(
        document(),
        [
            chunk("ACS_Lecture_1_2026F", 1, 0, "one"),
            chunk("ACS_Lecture_1_2026F", 2, 0, "two"),
        ],
    )
    store.set_embeddings(
        "ACS_Lecture_1_2026F",
        {"ACS_Lecture_1_2026F:p001:c00": b"\x00" * 8},
        model="BAAI/bge-m3",
        built_at=STAMP,
    )

    state = store.index_state()

    assert state["chunks"] == 1
    assert state["dimension"] == 2
    assert state["model"] == "BAAI/bge-m3"
    assert state["chunker_version"] == "vt-chunker/1"
