"""Retrieval endpoint seam: questions in, ranked chunks out, no prompt written."""

from __future__ import annotations

from datetime import datetime, timezone

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-11-05T12:00:00+00:00"


def _chunk(doc_id: str, page_no: int, text: str) -> dict:
    return {
        "schema": "vt-chunk-record/1",
        "chunker_version": "vt-chunker/1",
        "chunk_id": f"{doc_id}:p{page_no:03d}:c00",
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_index": 0,
        "section_title": None,
        "text": text,
        "embed_text": text,
        "block_ids": [1],
        "label_types": ["text"],
        "bbox_norm": [0.1, 0.1, 0.9, 0.2],
        "token_estimate": len(text) // 4,
        "oversize": False,
    }


def _seed(api, doc_id: str, chunks: list[dict]) -> None:
    document = {
        "id": doc_id,
        "title": doc_id,
        "filename": f"{doc_id}.pdf",
        "pdf_sha256": f"sha-{doc_id}",
        "page_count": 1,
        "pdf_path": str(api.settings.corpus_pdf_dir / f"{doc_id}.pdf"),
        "status": "ready",
        "indexed_at": STAMP,
        "created_at": STAMP,
        "updated_at": STAMP,
    }
    api.app.state.knowledge_store.upsert_document(document, chunks)


def test_retrieval_returns_ranked_chunks_with_page_metadata(api):
    api.create_active_account("alice@ust.hk")
    _seed(
        api,
        "Tutorial_2",
        [
            _chunk("Tutorial_2", 3, "Shared memory tiling reduces traffic."),
            _chunk("Tutorial_2", 4, "Warp divergence costs throughput."),
        ],
    )

    response = api.client.get(
        "/api/knowledge/retrieve", params={"q": "tiling", "k": 5}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lexical"] is True
    assert body["dense"] is False
    assert body["chunks"][0]["chunk_id"] == "Tutorial_2:p003:c00"
    assert body["chunks"][0]["page_no"] == 3
    assert body["chunks"][0]["doc_id"] == "Tutorial_2"
    assert body["chunks"][0]["sources"] == ["lexical"]
    assert body["chunks"][0]["bbox_norm"] == [0.1, 0.1, 0.9, 0.2]
    assert body["chunks"][0]["score"] > 0


def test_an_empty_question_returns_no_chunks(api):
    api.create_active_account("alice@ust.hk")

    body = api.client.get("/api/knowledge/retrieve", params={"q": "  "}).json()

    assert body["chunks"] == []
    assert body["need_retrieval"] is False


def test_retrieval_requires_sign_in(api):
    assert api.client.get("/api/knowledge/retrieve", params={"q": "tiling"}).status_code == 401


def test_k_is_bounded(api):
    api.create_active_account("alice@ust.hk")

    assert (
        api.client.get("/api/knowledge/retrieve", params={"q": "x", "k": 500}).status_code
        == 422
    )
