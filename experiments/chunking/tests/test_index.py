"""The experiment store exposes the four methods HybridRetriever needs."""

from __future__ import annotations

import numpy as np

from chunking_eval.index import EvalStore


def chunk(chunk_id: str, text: str, page_no: int = 1) -> dict:
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


def test_lexical_search_finds_a_term_and_falls_back_to_or(tmp_path) -> None:
    store = EvalStore(tmp_path / "index.db")
    store.add_chunks([chunk("c1", "alpha beta"), chunk("c2", "gamma delta")])

    assert [item["chunk_id"] for item in store.search_chunks("alpha")] == ["c1"]
    assert [item["chunk_id"] for item in store.search_chunks("alpha missing")] == ["c1"]


def test_get_chunks_keeps_the_page_mapping(tmp_path) -> None:
    store = EvalStore(tmp_path / "index.db")
    store.add_chunks([chunk("c1", "alpha", page_no=3)])

    item = store.get_chunks(["c1"])[0]

    assert item["page_nos"] == [3]
    assert item["section_title"] == "Section"


def test_vectors_and_index_state_round_trip(tmp_path) -> None:
    store = EvalStore(tmp_path / "index.db")
    store.add_chunks([chunk("c1", "alpha"), chunk("c2", "beta")])
    vector = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)

    store.set_embeddings(
        "doc",
        {"c1": vector.tobytes(), "c2": vector.tobytes()},
        model="fake",
        built_at="2026-11-18T00:00:00",
    )

    ids, blobs = store.stored_vectors()
    state = store.index_state()
    assert ids == ["c1", "c2"]
    assert len(blobs) == 2
    assert state["chunks"] == 2
    assert state["dimension"] == 3
    assert state["model"] == "fake"


def test_page_map_expands_multi_page_chunks(tmp_path) -> None:
    store = EvalStore(tmp_path / "index.db")
    first = chunk("c1", "alpha", page_no=1)
    first["page_nos"] = [1, 2]
    store.add_chunks([first])

    assert store.page_map() == {"c1": [("doc", 1), ("doc", 2)]}
