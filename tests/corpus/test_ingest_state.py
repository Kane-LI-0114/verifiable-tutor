"""The ingest-state and status seam.

Seam: ``load_state``/``save_state``, ``record_ocr``, ``documents_for_stage`` and
``status_rows``. They catch a second run that re-parses finished documents, an
ingest state that loses the job or log that produced a document, and a status
line that disagrees with the knowledge store; they do not catch a TACC job that
fails for a platform reason (the driver reports that).
"""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_ingest():
    path = REPO_ROOT / "scripts" / "ingest_corpus.py"
    spec = importlib.util.spec_from_file_location("ingest_corpus", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_store(tmp_path: Path):
    from verifiable_tutor.corpus.store import KnowledgeStore
    from verifiable_tutor.storage import Storage

    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    return KnowledgeStore(storage)


def chunk(doc_id: str, page_no: int, index: int) -> dict:
    return {
        "chunk_id": f"{doc_id}:p{page_no:03d}:c{index:02d}",
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_index": index,
        "section_title": None,
        "text": f"text {doc_id} p{page_no}",
        "embed_text": f"text {doc_id} p{page_no}",
        "block_ids": [0],
        "bbox_norm": None,
        "token_estimate": 4,
        "oversize": False,
        "chunker_version": "vt-chunker/1",
    }


def document(doc_id: str, page_count: int) -> dict:
    return {
        "id": doc_id,
        "filename": f"{doc_id}.pdf",
        "pdf_sha256": f"sha-{doc_id}",
        "pdf_path": f"data/corpus/corpus-pdf/{doc_id}.pdf",
        "title": doc_id,
        "page_count": page_count,
        "status": "ready",
        "created_at": "2026-11-05T00:00:00+00:00",
    }


def test_a_new_ingest_state_has_no_documents() -> None:
    ingest = load_ingest()

    state = ingest.empty_state()

    assert state["schema"] == "vt-ingest-state/1"
    assert state["documents"] == {}


def test_the_state_records_the_job_and_log_of_a_finished_document(tmp_path: Path) -> None:
    ingest = load_ingest()
    state = ingest.empty_state()
    report = {
        "status": "done",
        "job_id": "28201",
        "pages": 11,
        "pages_ok": 11,
        "seconds": 96.5,
        "pages_path": "data/corpus/pages/ACS_Lecture_0_2026F.jsonl",
        "log_path": "data/caches/ocr-results/b/logs/ACS_Lecture_0_2026F-28201.log",
    }

    ingest.record_ocr(state, "ACS_Lecture_0_2026F", report, batch="lectures")
    state_path = tmp_path / "ingest.json"
    ingest.save_state(state, state_path)
    reloaded = ingest.load_state(state_path)

    record = reloaded["documents"]["ACS_Lecture_0_2026F"]
    assert record["ocr"]["status"] == "done"
    assert record["ocr"]["job_id"] == "28201"
    assert record["ocr"]["log_path"].endswith("ACS_Lecture_0_2026F-28201.log")
    assert record["batch"] == "lectures"


def test_resume_skips_documents_that_already_finished() -> None:
    ingest = load_ingest()
    state = ingest.empty_state()
    ingest.record_ocr(
        state,
        "ACS_Lecture_0_2026F",
        {"status": "done", "job_id": "28201", "pages": 11, "pages_ok": 11},
        batch="lectures",
    )
    documents = [
        {"doc_id": "ACS_Lecture_0_2026F"},
        {"doc_id": "ACS_Lecture_1_2026F"},
    ]

    resumed = ingest.documents_for_stage(state, documents, "ocr", resume=True, force=False)
    forced = ingest.documents_for_stage(state, documents, "ocr", resume=False, force=True)

    assert [document["doc_id"] for document in resumed] == ["ACS_Lecture_1_2026F"]
    assert [document["doc_id"] for document in forced] == [
        "ACS_Lecture_0_2026F",
        "ACS_Lecture_1_2026F",
    ]


def test_status_reports_pages_chunks_vectors_and_summaries(tmp_path: Path) -> None:
    ingest = load_ingest()
    store = make_store(tmp_path)
    for doc_id, page_count in (("ACS_Lecture_0_2026F", 11), ("Tutorial_1", 16)):
        store.upsert_document(
            document(doc_id, page_count),
            [chunk(doc_id, page_no, 0) for page_no in range(1, page_count + 1)],
        )
    store.set_embeddings(
        "ACS_Lecture_0_2026F",
        {
            chunk("ACS_Lecture_0_2026F", page_no, 0)["chunk_id"]: b"\x00" * 4096
            for page_no in range(1, 12)
        },
        model="BAAI/bge-m3",
        built_at="2026-11-05T01:00:00+00:00",
    )
    store.set_document_summary(
        "Tutorial_1",
        summary="A tutorial summary.",
        model="qwen3.8-27b",
        created_at="2026-11-05T02:00:00+00:00",
        updated_at="2026-11-05T02:00:00+00:00",
    )
    state = ingest.empty_state()
    ingest.record_ocr(
        state,
        "ACS_Lecture_0_2026F",
        {"status": "done", "job_id": "28201", "pages": 11, "pages_ok": 11},
        batch="lectures",
    )
    ingest.record_ocr(
        state,
        "Tutorial_1",
        {"status": "done", "job_id": "28202", "pages": 16, "pages_ok": 16},
        batch="tutorials",
    )

    rows = ingest.status_rows(state, tmp_path / "app.sqlite3")
    totals = ingest.status_totals(rows)

    assert [row["doc_id"] for row in rows] == ["ACS_Lecture_0_2026F", "Tutorial_1"]
    assert totals["documents"] == 2
    assert totals["pages"] == 27
    assert totals["chunks"] == 27
    assert totals["vectors"] == 11
    assert totals["summaries"] == 1
    assert totals["ok"] is False


def test_status_names_the_log_of_a_failed_document(tmp_path: Path) -> None:
    ingest = load_ingest()
    store = make_store(tmp_path)
    store.upsert_document(
        document("Assignment_2", 5),
        [chunk("Assignment_2", page_no, 0) for page_no in range(1, 6)],
    )
    state = ingest.empty_state()
    ingest.record_ocr(
        state,
        "Assignment_2",
        {
            "status": "failed",
            "job_id": "28203",
            "error": "vLLM never became ready",
            "log_path": "data/caches/ocr-results/misc/logs/Assignment_2-28203.log",
        },
        batch="misc",
    )

    rows = ingest.status_rows(state, tmp_path / "app.sqlite3")
    totals = ingest.status_totals(rows)

    assert rows[0]["ocr_status"] == "failed"
    assert rows[0]["log_path"].endswith("Assignment_2-28203.log")
    assert totals["failed"] == 1
    assert totals["ok"] is False
