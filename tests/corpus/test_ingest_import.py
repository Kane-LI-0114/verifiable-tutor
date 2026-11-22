"""The offline import seam.

Seam: ``import_index`` and the knowledge-store state it leaves behind. It
catches a tracked vector matrix that does not line up with the chunks the
tracked page records produce, and a fresh checkout that stays without a local
knowledge store after the import; it does not catch an embedding that is
numerically poor or a TACC job that failed (the drivers report those).
"""

from __future__ import annotations

import importlib.util
import json
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ID = "course_project"
MODEL = "BAAI/bge-m3"
BUILT_AT = "2026-11-06T08:32:30+00:00"
SUMMARY_TEXT = "The project brief asks for an end-to-end agent system."


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


def page(page_no: int, text: str) -> dict:
    return {
        "schema": "vt-page-record/1",
        "doc_id": DOC_ID,
        "pdf": f"{DOC_ID}.pdf",
        "pdf_sha256": f"sha-{DOC_ID}",
        "page_no": page_no,
        "text": text,
        "blocks": [
            {
                "block_id": 0,
                "block_order": 0,
                "label": "text",
                "content": text,
                "bbox_norm": [0.1, 0.1, 0.9, 0.2],
            }
        ],
    }


def write_pages(pages_dir: Path, pages: list[dict]) -> Path:
    pages_dir.mkdir(parents=True, exist_ok=True)
    path = pages_dir / f"{DOC_ID}.jsonl"
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in pages), encoding="utf-8"
    )
    return path


def write_npy(path: Path, rows: list[list[float]]) -> None:
    dimension = len(rows[0])
    header = "{'descr': '<f4', 'fortran_order': False, 'shape': (%d, %d), }" % (
        len(rows),
        dimension,
    )
    padding = 16 - (10 + len(header) + 1) % 16
    header_bytes = (header + " " * padding + "\n").encode("latin1")
    with path.open("wb") as handle:
        handle.write(b"\x93NUMPY\x01\x00")
        handle.write(struct.pack("<H", len(header_bytes)))
        handle.write(header_bytes)
        for row in rows:
            handle.write(struct.pack("<%df" % dimension, *row))


def write_index_dir(
    index_dir: Path, chunk_ids: list[str], *, dimension: int = 4
) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "row_map.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "row": row,
                    "chunk_id": chunk_id,
                    "doc_id": DOC_ID,
                    "page_no": int(chunk_id.split(":p")[1][:3]),
                }
            )
            + "\n"
            for row, chunk_id in enumerate(chunk_ids)
        ),
        encoding="utf-8",
    )
    write_npy(
        index_dir / "vectors.npy",
        [[float(row), 1.0, 2.0, 3.0] for row in range(len(chunk_ids))],
    )
    (index_dir / "summary.json").write_text(
        json.dumps(
            {
                "schema": "vt-index-summary/1",
                "job_id": "28320",
                "model": MODEL,
                "generated_at": BUILT_AT,
            }
        ),
        encoding="utf-8",
    )
    (index_dir / "summaries.json").write_text(
        json.dumps(
            {
                "schema": "vt-doc-summaries/1",
                "documents": {
                    DOC_ID: {
                        "summary": SUMMARY_TEXT,
                        "model": "qwen3.8-27b",
                        "created_at": "2026-11-05T02:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return index_dir


def document() -> dict:
    return {
        "doc_id": DOC_ID,
        "pdf": f"{DOC_ID}.pdf",
        "expected_pages": 2,
        "batch": "already-parsed",
    }


def test_import_restores_chunks_vectors_and_summary_without_tacc(tmp_path: Path) -> None:
    ingest = load_ingest()
    store = make_store(tmp_path)
    pages_dir = tmp_path / "pages"
    write_pages(pages_dir, [page(1, "Page one text."), page(2, "Page two text.")])
    index_dir = write_index_dir(
        tmp_path / "index", ["course_project:p001:c00", "course_project:p002:c00"]
    )
    state = ingest.empty_state()

    report = ingest.import_index(
        store=store,
        documents=[document()],
        state=state,
        index_dir=index_dir,
        pages_dir=pages_dir,
    )

    assert report["ok"] is True
    assert report["documents"] == {DOC_ID: {"chunks": 2, "vectors": 2}}
    assert report["model"] == MODEL
    assert report["issues"] == []
    assert report["state_changed"] is True
    stored = store.get_document(DOC_ID)
    assert stored["status"] == "ready"
    assert stored["summary"] == SUMMARY_TEXT
    assert stored["chunk_count"] == 2
    state_index = store.index_state()
    assert state_index["chunks"] == 2
    assert state_index["dimension"] == 4
    assert state_index["model"] == MODEL
    assert state_index["built_at"] == BUILT_AT
    rows = ingest.status_rows(state, tmp_path / "app.sqlite3")
    assert ingest.status_totals(rows)["ok"] is True


def test_a_chunk_without_a_tracked_vector_leaves_the_document_unstored(
    tmp_path: Path,
) -> None:
    ingest = load_ingest()
    store = make_store(tmp_path)
    pages_dir = tmp_path / "pages"
    write_pages(pages_dir, [page(1, "Page one text."), page(2, "Page two text.")])
    index_dir = write_index_dir(tmp_path / "index", ["course_project:p001:c00"])
    state = ingest.empty_state()

    report = ingest.import_index(
        store=store,
        documents=[document()],
        state=state,
        index_dir=index_dir,
        pages_dir=pages_dir,
    )

    assert report["ok"] is False
    assert report["documents"] == {}
    assert any("course_project:p002:c00" in issue for issue in report["issues"])
    assert store.get_document(DOC_ID) is None
    assert store.index_state()["chunks"] == 0


def test_the_summary_export_round_trips_into_a_second_store(tmp_path: Path) -> None:
    ingest = load_ingest()
    pages_dir = tmp_path / "pages"
    write_pages(pages_dir, [page(1, "Page one text."), page(2, "Page two text.")])
    index_dir = write_index_dir(
        tmp_path / "index", ["course_project:p001:c00", "course_project:p002:c00"]
    )
    source = make_store(tmp_path / "source")
    ingest.import_index(
        store=source,
        documents=[document()],
        state=ingest.empty_state(),
        index_dir=index_dir,
        pages_dir=pages_dir,
    )
    export_path = tmp_path / "export" / "summaries.json"

    payload = ingest.export_summaries(store=source, path=export_path)

    assert json.loads(export_path.read_text(encoding="utf-8")) == payload
    assert payload["schema"] == "vt-doc-summaries/1"
    assert payload["documents"][DOC_ID]["summary"] == SUMMARY_TEXT
    assert payload["documents"][DOC_ID]["model"] == "qwen3.8-27b"
    assert payload["documents"][DOC_ID]["created_at"] == "2026-11-05T02:00:00+00:00"
    target = make_store(tmp_path / "target")
    ingest.import_index(
        store=target,
        documents=[document()],
        state=ingest.empty_state(),
        index_dir=index_dir,
        pages_dir=pages_dir,
        summaries_path=export_path,
    )
    assert target.get_document(DOC_ID)["summary"] == SUMMARY_TEXT


def test_import_keeps_the_finished_stage_records_of_the_tracked_state(
    tmp_path: Path,
) -> None:
    ingest = load_ingest()
    store = make_store(tmp_path)
    pages_dir = tmp_path / "pages"
    write_pages(pages_dir, [page(1, "Page one text."), page(2, "Page two text.")])
    index_dir = write_index_dir(
        tmp_path / "index", ["course_project:p001:c00", "course_project:p002:c00"]
    )
    state = ingest.empty_state()
    ingest.record_ocr(
        state,
        DOC_ID,
        {"status": "done", "job_id": "27884", "pages": 2, "pages_ok": 2},
        batch="already-parsed",
    )
    ingest.record_chunks(state, DOC_ID, count=2, chunker_version="vt-chunker/1")
    ingest.record_index(state, DOC_ID, vectors=2, model=MODEL, job_id="28320")
    ingest.record_summary(
        state, DOC_ID, model="qwen3.8-27b", build_id="summary-1", page_count=2
    )

    report = ingest.import_index(
        store=store,
        documents=[document()],
        state=state,
        index_dir=index_dir,
        pages_dir=pages_dir,
    )

    assert report["ok"] is True
    assert report["state_changed"] is False
    record = state["documents"][DOC_ID]
    assert record["ocr"]["job_id"] == "27884"
    assert record["index"]["job_id"] == "28320"
    assert record["summary"]["build_id"] == "summary-1"
