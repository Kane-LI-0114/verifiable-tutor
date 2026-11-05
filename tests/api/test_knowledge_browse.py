"""Knowledge browse seam: folders, files, search, PDF bytes, and organization.

Every assertion goes through the HTTP API. Documents are seeded through the
store in the fixture, which is setup, not the behaviour under test.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
STAMP = "2026-11-05T12:00:00+00:00"


def _chunk(doc_id: str, page_no: int, text: str, section: str | None = None) -> dict:
    return {
        "schema": "vt-chunk-record/1",
        "chunker_version": "vt-chunker/1",
        "chunk_id": f"{doc_id}:p{page_no:03d}:c00",
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_index": 0,
        "section_title": section,
        "text": text,
        "embed_text": text,
        "block_ids": [1],
        "label_types": ["text"],
        "bbox_norm": [0.1, 0.1, 0.9, 0.2],
        "token_estimate": len(text) // 4,
        "oversize": False,
    }


def _seed(api, doc_id: str, *, chunks: list[dict], **overrides) -> None:
    pdf = api.settings.corpus_pdf_dir / f"{doc_id}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 minimal")
    document = {
        "id": doc_id,
        "title": doc_id,
        "filename": f"{doc_id}.pdf",
        "pdf_sha256": f"sha-{doc_id}",
        "byte_size": 16,
        "page_count": max((chunk["page_no"] for chunk in chunks), default=1),
        "pdf_path": str(pdf),
        "thumbnail_path": None,
        "status": "ready",
        "indexed_at": STAMP,
        "created_at": STAMP,
        "updated_at": STAMP,
    }
    document.update(overrides)
    api.app.state.knowledge_store.upsert_document(document, chunks)


def _two_documents(api) -> None:
    _seed(
        api,
        "ACS_Lecture_1_2026F",
        chunks=[
            _chunk("ACS_Lecture_1_2026F", 1, "The allreduce operation combines gradients."),
            _chunk("ACS_Lecture_1_2026F", 2, "Shared memory tiling reduces traffic."),
        ],
        summary="Collective communication on GPUs.",
    )
    _seed(
        api,
        "Tutorial_2",
        chunks=[_chunk("Tutorial_2", 1, "CUDA streams overlap kernel launches.")],
        summary="Tutorial on streams.",
    )


def test_browsing_requires_sign_in(api):
    assert api.client.get("/api/knowledge/folders").status_code == 401
    assert api.client.get("/api/knowledge/documents").status_code == 401


def test_the_root_lists_files_and_the_folder_tree(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)

    folders = api.client.get("/api/knowledge/folders").json()
    documents = api.client.get("/api/knowledge/documents").json()

    assert folders["folders"] == []
    assert folders["total_files"] == 2
    assert documents["total"] == 2
    assert {item["id"] for item in documents["documents"]} == {
        "ACS_Lecture_1_2026F",
        "Tutorial_2",
    }


def test_a_folder_can_be_created_and_renamed(api):
    api.create_active_account("alice@ust.hk")

    created = api.client.post(
        "/api/knowledge/folders", json={"name": "Lectures", "parent_id": None}
    )
    assert created.status_code == 201
    folder_id = created.json()["id"]

    renamed = api.client.patch(
        f"/api/knowledge/folders/{folder_id}", json={"name": "Lecture decks"}
    )

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Lecture decks"
    assert api.client.patch(
        f"/api/knowledge/folders/{folder_id}",
        json={"name": "Lectures", "parent_id": folder_id},
    ).status_code == 400


def test_a_document_can_be_moved_and_listed_in_its_new_folder(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)
    folder = api.client.post(
        "/api/knowledge/folders", json={"name": "Week 1", "parent_id": None}
    ).json()

    moved = api.client.patch(
        "/api/knowledge/documents/ACS_Lecture_1_2026F",
        json={"folder_id": folder["id"]},
    )

    assert moved.status_code == 200
    assert moved.json()["folder_id"] == folder["id"]
    inside = api.client.get(
        "/api/knowledge/documents", params={"folder_id": folder["id"]}
    ).json()
    assert [item["id"] for item in inside["documents"]] == ["ACS_Lecture_1_2026F"]
    root = api.client.get("/api/knowledge/documents").json()
    assert [item["id"] for item in root["documents"]] == ["Tutorial_2"]


def test_deleting_a_document_removes_its_chunks_and_mirror_file(api):
    api.create_active_account("bob@ust.hk")
    instructor = api.create_instructor("teacher@ust.hk")
    api.client.cookies.update(instructor)
    _two_documents(api)
    pdf = api.settings.corpus_pdf_dir / "ACS_Lecture_1_2026F.pdf"

    deleted = api.client.delete("/api/knowledge/documents/ACS_Lecture_1_2026F")

    assert deleted.status_code == 200
    assert api.client.get("/api/knowledge/documents/ACS_Lecture_1_2026F").status_code == 404
    assert not pdf.exists()
    assert api.app.state.knowledge_store.search_chunks("allreduce") == []


def test_a_student_cannot_delete_a_document(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)

    assert (
        api.client.delete("/api/knowledge/documents/Tutorial_2").status_code == 403
    )


def test_deleting_a_folder_removes_the_documents_inside_it(api):
    instructor = api.create_instructor("teacher@ust.hk")
    api.client.cookies.update(instructor)
    _two_documents(api)
    folder = api.client.post(
        "/api/knowledge/folders", json={"name": "Lectures", "parent_id": None}
    ).json()
    api.client.patch(
        f"/api/knowledge/documents/ACS_Lecture_1_2026F",
        json={"folder_id": folder["id"]},
    )

    deleted = api.client.delete(f"/api/knowledge/folders/{folder['id']}")

    assert deleted.status_code == 200
    assert deleted.json()["deleted_documents"] == 1
    assert api.client.get("/api/knowledge/documents/ACS_Lecture_1_2026F").status_code == 404


def test_search_reports_the_reason_and_the_highlight_ranges(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)

    content = api.client.get("/api/knowledge/search", params={"q": "allreduce"}).json()
    assert [item["id"] for item in content["documents"]] == ["ACS_Lecture_1_2026F"]
    match = content["documents"][0]["matches"][0]
    assert match["kind"] == "content"
    assert match["page_no"] == 1
    assert match["snippet"] == "The allreduce operation combines gradients."
    assert match["highlights"] == [[4, 13]]

    summary = api.client.get("/api/knowledge/search", params={"q": "collective"}).json()
    assert summary["documents"][0]["matches"][0]["kind"] == "summary"

    name = api.client.get("/api/knowledge/search", params={"q": "Tutorial"}).json()
    kinds = {match["kind"] for match in name["documents"][0]["matches"]}
    assert "filename" in kinds


def test_search_by_folder_name_matches_the_documents_inside(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)
    folder = api.client.post(
        "/api/knowledge/folders", json={"name": "Week one", "parent_id": None}
    ).json()
    api.client.patch(
        "/api/knowledge/documents/Tutorial_2", json={"folder_id": folder["id"]}
    )

    response = api.client.get("/api/knowledge/search", params={"q": "week"})

    assert [item["id"] for item in response.json()["documents"]] == ["Tutorial_2"]
    assert response.json()["documents"][0]["matches"][0]["kind"] == "folder"


def test_the_pdf_route_serves_the_mirror_file(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)

    response = api.client.get("/api/knowledge/documents/Tutorial_2/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 minimal"
    assert (
        api.client.get("/api/knowledge/documents/bad id!/file").status_code == 422
    )


def test_a_document_detail_carries_its_summary_and_counts(api):
    api.create_active_account("alice@ust.hk")
    _two_documents(api)

    detail = api.client.get("/api/knowledge/documents/ACS_Lecture_1_2026F").json()

    assert detail["summary"] == "Collective communication on GPUs."
    assert detail["page_count"] == 2
    assert detail["chunk_count"] == 2
    assert detail["pdf_url"] == "/api/knowledge/documents/ACS_Lecture_1_2026F/file"
    assert detail["thumbnail_url"] == "/api/corpus/ACS_Lecture_1_2026F/pages/1.webp"
