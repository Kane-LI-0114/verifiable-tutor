#!/usr/bin/env python3
"""Ingest the course corpus into the local knowledge store through TACC jobs.

Three stages, run in order:

``ocr``
    Parse the corpus PDFs in three batched TACC GPU jobs (Lectures, Tutorials,
    Misc). ``course_project.pdf`` is already parsed: its week-one page records
    are copied instead of parsed again.
``index``
    Chunk the page records locally with the page-first chunker, store the
    documents and chunks, then embed every chunk with BGE-M3 in one TACC GPU
    job and store the vectors.
``summarize``
    Write one Qwen document summary per document in one TACC GPU job.

Per-document progress lives in ``data/index/ingest.json``, so a rerun continues
from the last finished stage; ``--force`` redoes a stage and ``--only`` limits a
run to named documents.

Usage:
  .venv/bin/python scripts/ingest_corpus.py status
  .venv/bin/python scripts/ingest_corpus.py ocr --batch lectures
  .venv/bin/python scripts/ingest_corpus.py index --resume
  .venv/bin/python scripts/ingest_corpus.py summarize --resume
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

STATE_PATH = REPO_ROOT / "data" / "index" / "ingest.json"
DB_PATH = REPO_ROOT / "data" / "app" / "app.sqlite3"
STATE_SCHEMA = "vt-ingest-state/1"
PAGES_DIR = REPO_ROOT / "data" / "corpus" / "pages"
IMAGES_DIR = REPO_ROOT / "data" / "corpus" / "images"
DOCUMENT_DIR = REPO_ROOT / "data" / "corpus" / "ocr"
CORPUS_PDF_DIR = REPO_ROOT / "data" / "corpus" / "corpus-pdf"
SCRIPTS_TACC = REPO_ROOT / "scripts" / "tacc"
STAGES = ("ocr", "chunks", "index", "summary")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


# ------------------------------------------------------------------ state file
def empty_state() -> dict:
    """Return the empty per-document ingest state."""

    return {"schema": STATE_SCHEMA, "updated_at": now_iso(), "documents": {}}


def load_state(path: Path = STATE_PATH) -> dict:
    path = Path(path)
    if not path.is_file():
        return empty_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != STATE_SCHEMA:
        raise SystemExit(f"{path}: expected schema {STATE_SCHEMA}")
    state.setdefault("documents", {})
    return state


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path = Path(path)
    state["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _document_state(state: dict, doc_id: str) -> dict:
    record = state["documents"].setdefault(
        doc_id,
        {"doc_id": doc_id, "ocr": {}, "chunks": {}, "index": {}, "summary": {}},
    )
    for stage in STAGES:
        record.setdefault(stage, {})
    return record


def record_ocr(state: dict, doc_id: str, report: dict, *, batch: str) -> dict:
    """Record one OCR result on a document."""

    record = _document_state(state, doc_id)
    record["batch"] = batch
    record["ocr"] = {
        "status": str(report.get("status") or "failed"),
        "job_id": str(report.get("job_id") or ""),
        "pages": int(report.get("pages") or 0),
        "pages_ok": int(report.get("pages_ok") or 0),
        "seconds": report.get("seconds"),
        "pages_path": report.get("pages_path"),
        "log_path": report.get("log_path"),
        "error": report.get("error"),
        "source": report.get("source"),
        "finished_at": now_iso(),
    }
    return record


def record_chunks(state: dict, doc_id: str, *, count: int, chunker_version: str) -> dict:
    record = _document_state(state, doc_id)
    record["chunks"] = {
        "status": "done",
        "count": int(count),
        "chunker_version": chunker_version,
        "finished_at": now_iso(),
    }
    return record


def record_index(state: dict, doc_id: str, *, vectors: int, model: str, job_id: str) -> dict:
    record = _document_state(state, doc_id)
    record["index"] = {
        "status": "done",
        "vectors": int(vectors),
        "model": model,
        "job_id": job_id,
        "finished_at": now_iso(),
    }
    return record


def record_summary(
    state: dict, doc_id: str, *, model: str, build_id: str, page_count: int
) -> dict:
    record = _document_state(state, doc_id)
    record["summary"] = {
        "status": "done",
        "model": model,
        "build_id": build_id,
        "page_count": int(page_count),
        "finished_at": now_iso(),
    }
    return record


def documents_for_stage(
    state: dict, documents: list[dict], stage: str, *, resume: bool, force: bool
) -> list[dict]:
    """Return the documents a rerun still has to process for ``stage``."""

    if not resume or force:
        return list(documents)
    remaining = []
    for document in documents:
        record = (state.get("documents") or {}).get(document["doc_id"]) or {}
        if (record.get(stage) or {}).get("status") == "done":
            continue
        remaining.append(document)
    return remaining


# --------------------------------------------------------------------- status
def _count_rows(
    connection: sqlite3.Connection, sql: str, parameters: tuple = ()
) -> dict[str, int]:
    try:
        return {str(row[0]): int(row[1]) for row in connection.execute(sql, parameters)}
    except sqlite3.Error:
        return {}


def status_rows(state: dict, db_path: Path = DB_PATH) -> list[dict]:
    """Merge the ingest state with the knowledge store into one row per document."""

    state_documents = state.get("documents") or {}
    db_documents: dict[str, dict] = {}
    chunk_counts: dict[str, int] = {}
    vector_counts: dict[str, int] = {}
    if Path(db_path).is_file():
        connection = sqlite3.connect(db_path)
        try:
            connection.row_factory = sqlite3.Row
            try:
                rows = connection.execute(
                    "SELECT id, page_count, chunk_count, status, summary, status_detail"
                    " FROM kb_documents"
                ).fetchall()
            except sqlite3.Error:
                rows = []
            db_documents = {str(row["id"]): dict(row) for row in rows}
            chunk_counts = _count_rows(
                connection, "SELECT doc_id, COUNT(*) FROM kb_chunks GROUP BY doc_id"
            )
            vector_counts = _count_rows(
                connection,
                "SELECT doc_id, COUNT(*) FROM kb_chunks"
                " WHERE embedding IS NOT NULL GROUP BY doc_id",
            )
        finally:
            connection.close()

    rows: list[dict] = []
    for doc_id, record in state_documents.items():
        rows.append(_status_row(doc_id, record, db_documents.get(doc_id), chunk_counts, vector_counts))
    for doc_id, db_record in db_documents.items():
        if doc_id in state_documents:
            continue
        rows.append(
            _status_row(
                doc_id, {"doc_id": doc_id}, db_record, chunk_counts, vector_counts
            )
        )
    return rows


def _status_row(
    doc_id: str,
    record: dict,
    db_record: dict | None,
    chunk_counts: dict[str, int],
    vector_counts: dict[str, int],
) -> dict:
    ocr = record.get("ocr") or {}
    db_record = db_record or {}
    summary_stage = record.get("summary") or {}
    chunks = int(chunk_counts.get(doc_id) or db_record.get("chunk_count") or 0)
    vectors = int(vector_counts.get(doc_id) or 0)
    return {
        "doc_id": doc_id,
        "batch": record.get("batch"),
        "ocr_status": ocr.get("status") or "pending",
        "pages": int(ocr.get("pages") or db_record.get("page_count") or 0),
        "pages_ok": int(ocr.get("pages_ok") or 0),
        "chunks": chunks,
        "vectors": vectors,
        "summary": bool(db_record.get("summary")) or summary_stage.get("status") == "done",
        "doc_status": db_record.get("status"),
        "status_detail": db_record.get("status_detail"),
        "log_path": ocr.get("log_path"),
        "error": ocr.get("error"),
    }


def status_totals(rows: list[dict]) -> dict:
    """Summarise the per-document rows for the acceptance line."""

    failed = sum(
        1
        for row in rows
        if row["ocr_status"] == "failed" or row["doc_status"] == "failed"
    )
    done = sum(
        1
        for row in rows
        if row["ocr_status"] == "done"
        and row["chunks"] > 0
        and row["vectors"] == row["chunks"]
        and row["summary"]
    )
    return {
        "documents": len(rows),
        "pages": sum(row["pages"] for row in rows),
        "chunks": sum(row["chunks"] for row in rows),
        "vectors": sum(row["vectors"] for row in rows),
        "summaries": sum(1 for row in rows if row["summary"]),
        "done": done,
        "failed": failed,
        "ok": bool(rows) and done == len(rows) and failed == 0,
    }


# -------------------------------------------------------------------- drivers
def load_driver(name: str, relative: str):
    path = REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _only(only: str) -> list[str]:
    return [part.strip() for part in (only or "").split(",") if part.strip()]


def corpus_documents(ocr_driver) -> list[dict]:
    """Every corpus document, with its batch and expected page count."""

    documents: list[dict] = []
    for batch, items in ocr_driver.BATCHES.items():
        for item in items:
            documents.append({**item, "batch": batch})
    for doc_id, info in ocr_driver.ALREADY_PARSED.items():
        documents.append(
            {
                "doc_id": doc_id,
                "pdf": info["pdf"],
                "expected_pages": info["pages"],
                "batch": "already-parsed",
            }
        )
    return documents


def ensure_already_parsed(state: dict, ocr_driver, *, force: bool = False) -> None:
    """Stage the week-one course_project parse instead of parsing it again."""

    for doc_id, info in ocr_driver.ALREADY_PARSED.items():
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        target = PAGES_DIR / f"{doc_id}.jsonl"
        source = Path(info["pages_path"])
        if source.is_file() and (force or not target.is_file()):
            shutil.copyfile(source, target)
        status = "done" if target.is_file() else "failed"
        record = _document_state(state, doc_id)
        record["batch"] = "already-parsed"
        record["ocr"] = {
            "status": status,
            "job_id": "27884",
            "pages": int(info["pages"]),
            "pages_ok": int(info["pages"]),
            "seconds": None,
            "pages_path": str(target),
            "log_path": None,
            "error": None if status == "done" else f"missing {source}",
            "source": f"data/corpus/pdf-parse/pages-27884.jsonl (job 27884, reused)",
            "finished_at": now_iso(),
        }
        log(
            f"[ingest] {doc_id}: copied {info['pages']} page records from "
            f"{source.relative_to(REPO_ROOT) if source.is_relative_to(REPO_ROOT) else source} "
            "(already parsed as job 27884)"
        )


# ------------------------------------------------------------------------ ocr
def ingest_ocr(args) -> int:
    driver = load_driver("run_ocr_job", "scripts/tacc/run_ocr_job.py")
    state = load_state()
    ensure_already_parsed(state, driver, force=args.force)
    save_state(state)
    if args.finish_batch_id:
        report = driver.finish_batch(args.finish_batch_id, job_id=args.job_id)
        for doc_id, record in (report.get("documents") or {}).items():
            record_ocr(state, doc_id, record, batch=report.get("batch") or "unknown")
        save_state(state)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report.get("ok") else 1
    batches = ["lectures", "tutorials", "misc"] if args.batch == "all" else [args.batch]
    only = _only(args.only)
    ok = True
    reports = []
    for batch in batches:
        report = driver.run_batch(
            batch=batch,
            state=state.get("documents", {}),
            resume=args.resume,
            force=args.force,
            only=only or None,
            batch_id=args.batch_id if len(batches) == 1 else None,
            dry_run=args.dry_run,
        )
        reports.append(report)
        if report.get("dry_run") or report.get("skipped_batch"):
            continue
        for doc_id, record in (report.get("documents") or {}).items():
            record_ocr(state, doc_id, record, batch=batch)
        save_state(state)
        ok = ok and bool(report.get("ok"))
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0 if ok else 1


# ---------------------------------------------------------------------- index
def _document_row(document: dict, pages: list[dict]) -> dict:
    doc_id = document["doc_id"]
    pdf_path = CORPUS_PDF_DIR / document["pdf"]
    sha = next(
        (str(page.get("pdf_sha256")) for page in pages if page.get("pdf_sha256")),
        "",
    ) or hashlib.sha256(doc_id.encode("utf-8")).hexdigest()
    thumbnail = IMAGES_DIR / f"{doc_id}.p001.webp"
    created_at = now_iso()
    return {
        "id": doc_id,
        "title": doc_id,
        "filename": document["pdf"],
        "pdf_sha256": sha,
        "byte_size": pdf_path.stat().st_size if pdf_path.is_file() else None,
        "page_count": len(pages),
        "pdf_path": str(pdf_path),
        "thumbnail_path": str(thumbnail) if thumbnail.is_file() else None,
        "status": "processing",
        "created_at": created_at,
        "updated_at": created_at,
    }


def ingest_index(args) -> int:
    from verifiable_tutor.corpus.chunker import (
        CHUNKER_VERSION,
        chunks_from_pages,
    )
    from verifiable_tutor.corpus.pages import read_pages
    from verifiable_tutor.corpus.store import KnowledgeStore
    from verifiable_tutor.storage import Storage

    ocr_driver = load_driver("run_ocr_job", "scripts/tacc/run_ocr_job.py")
    index_driver = load_driver("run_index_job", "scripts/tacc/run_index_job.py")
    state = load_state()
    ensure_already_parsed(state, ocr_driver, force=args.force)
    save_state(state)
    only = _only(args.only)
    documents = corpus_documents(ocr_driver)
    if only:
        documents = [document for document in documents if document["doc_id"] in only]
    documents = documents_for_stage(
        state, documents, "index", resume=args.resume, force=args.force
    )
    if not documents:
        log("[ingest] every selected document already has vectors")
        print(json.dumps({"ok": True, "skipped": True}, indent=2))
        return 0

    storage = Storage(DB_PATH)
    storage.initialize()
    store = KnowledgeStore(storage)
    rows: list[dict] = []
    prepared: list[str] = []
    for document in documents:
        doc_id = document["doc_id"]
        record = _document_state(state, doc_id)
        if (record.get("ocr") or {}).get("status") != "done":
            log(f"[ingest] {doc_id}: OCR has not finished; skipping")
            continue
        chunks_done = (record.get("chunks") or {}).get("status") == "done"
        if chunks_done and not args.force and not args.dry_run:
            chunks = store.list_chunks(doc_id)
            log(f"[ingest] {doc_id}: reusing {len(chunks)} stored chunks")
        else:
            pages_path = PAGES_DIR / f"{doc_id}.jsonl"
            if not pages_path.is_file():
                log(f"[ingest] {doc_id}: missing page records at {pages_path}")
                continue
            pages = read_pages(pages_path)
            chunks = chunks_from_pages(pages)
            if not args.dry_run:
                store.upsert_document(_document_row(document, pages), chunks)
                record_chunks(state, doc_id, count=len(chunks), chunker_version=CHUNKER_VERSION)
                log(
                    f"[ingest] {doc_id}: stored {len(pages)} pages as {len(chunks)} chunks"
                )
        rows.extend(
            {
                "chunk_id": chunk["chunk_id"],
                "doc_id": doc_id,
                "page_no": int(chunk["page_no"]),
                "text": chunk.get("embed_text") or chunk["text"],
            }
            for chunk in chunks
        )
        prepared.append(doc_id)
    if not args.dry_run:
        save_state(state)
    if not rows:
        log("[ingest] no chunks to embed; run the ocr stage first")
        print(json.dumps({"ok": False, "reason": "no chunks"}, indent=2))
        return 1

    report = index_driver.run_index(
        rows=rows,
        state=state.get("documents", {}),
        resume=args.resume,
        force=args.force,
        batch_id=args.batch_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("dry_run") or report.get("skipped_index"):
        return 0
    model = (report.get("index_state") or {}).get("model") or ""
    for doc_id, vectors in (report.get("documents") or {}).items():
        record_index(
            state,
            doc_id,
            vectors=int(vectors),
            model=model,
            job_id=str(report.get("job_id") or ""),
        )
        chunk_count = int(
            ((state["documents"].get(doc_id) or {}).get("chunks") or {}).get("count") or 0
        )
        if int(vectors) == chunk_count:
            store.set_document_status(
                doc_id, "ready", detail=None, updated_at=now_iso()
            )
    if not args.dry_run:
        save_state(state)
    return 0 if report.get("ok") else 1


# ------------------------------------------------------------------ summarize
def ingest_summarize(args) -> int:
    from verifiable_tutor.corpus.pages import read_pages
    from verifiable_tutor.knowledge.request import summary_input_from_pages

    ocr_driver = load_driver("run_ocr_job", "scripts/tacc/run_ocr_job.py")
    summary_driver = load_driver("run_summary_job", "scripts/tacc/run_summary_job.py")
    state = load_state()
    ensure_already_parsed(state, ocr_driver, force=args.force)
    save_state(state)
    only = _only(args.only)
    documents = corpus_documents(ocr_driver)
    if only:
        documents = [document for document in documents if document["doc_id"] in only]
    documents = documents_for_stage(
        state, documents, "summary", resume=args.resume, force=args.force
    )
    inputs = []
    for document in documents:
        doc_id = document["doc_id"]
        pages_path = PAGES_DIR / f"{doc_id}.jsonl"
        if not pages_path.is_file():
            log(f"[ingest] {doc_id}: missing page records at {pages_path}")
            continue
        inputs.append(summary_input_from_pages(read_pages(pages_path)))
    if not inputs:
        log("[ingest] every selected document already has a summary")
        print(json.dumps({"ok": True, "skipped": True}, indent=2))
        return 0
    report = summary_driver.run_summary(
        documents=inputs,
        state=state.get("documents", {}),
        resume=args.resume,
        force=args.force,
        build_id=args.build_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("dry_run") or report.get("skipped"):
        return 0
    for doc_id, record in (report.get("documents") or {}).items():
        record_summary(
            state,
            doc_id,
            model=str(record.get("model") or ""),
            build_id=str(report.get("build_id") or ""),
            page_count=int(record.get("page_count") or 0),
        )
    if not args.dry_run:
        save_state(state)
    return 0 if report.get("ok") else 1


# --------------------------------------------------------------------- status
def print_status(rows: list[dict], totals: dict, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"totals": totals, "documents": rows}, ensure_ascii=False, indent=2))
        return 0 if totals["ok"] else 1
    header = (
        f"{'doc_id':<26} {'batch':<14} {'pages':>5} {'ok':>5} "
        f"{'chunks':>7} {'vectors':>7} {'summary':>8} {'store':<10} log"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['doc_id']:<26} {str(row['batch'] or '-'):<14} {row['pages']:>5} "
            f"{row['pages_ok']:>5} {row['chunks']:>7} {row['vectors']:>7} "
            f"{'yes' if row['summary'] else 'no':>8} {str(row['doc_status'] or '-'):<10} "
            f"{row['log_path'] or ''}"
        )
        if row["ocr_status"] == "failed" or row["doc_status"] == "failed":
            print(
                f"  FAILED {row['doc_id']}: log={row['log_path'] or '<no log>'}"
                f" error={row['error'] or row['status_detail'] or 'unknown'}"
            )
    print("-" * len(header))
    print(
        f"documents={totals['documents']} pages={totals['pages']} "
        f"chunks={totals['chunks']} vectors={totals['vectors']} "
        f"summaries={totals['summaries']} done={totals['done']} "
        f"failed={totals['failed']} ok={'true' if totals['ok'] else 'false'}"
    )
    return 0 if totals["ok"] else 1


# ------------------------------------------------------------------------ CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "--resume",
            action="store_true",
            help="continue from data/index/ingest.json and skip finished documents",
        )
        sub.add_argument("--only", default="", help="comma separated document ids")
        sub.add_argument("--force", action="store_true", help="redo the stage")
        sub.add_argument("--dry-run", action="store_true", help="prepare without TACC")
        sub.add_argument("--state", default=None, help="alternate ingest state path")

    ocr = subparsers.add_parser("ocr", help="parse the corpus PDFs in TACC batches")
    ocr.add_argument(
        "--batch", default="all", choices=["all", "lectures", "tutorials", "misc"]
    )
    ocr.add_argument("--batch-id", default=None)
    ocr.add_argument(
        "--finish-batch-id",
        default=None,
        help="download and record an already submitted batch without resubmitting",
    )
    ocr.add_argument(
        "--job-id",
        default=None,
        help="job id to finish when no local summary was downloaded yet",
    )
    add_common(ocr)

    index = subparsers.add_parser("index", help="chunk locally and embed on TACC")
    index.add_argument("--batch-id", default=None)
    add_common(index)

    summarize = subparsers.add_parser("summarize", help="Qwen document summaries on TACC")
    summarize.add_argument("--build-id", default=None)
    add_common(summarize)

    status = subparsers.add_parser("status", help="per-document page, chunk, vector and summary counts")
    status.add_argument("--json", action="store_true")
    status.add_argument("--state", default=None)
    status.add_argument("--db", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "state", None):
        globals()["STATE_PATH"] = Path(args.state)
    if args.command == "status":
        state = load_state(Path(args.state) if args.state else STATE_PATH)
        db_path = Path(args.db) if args.db else DB_PATH
        rows = status_rows(state, db_path)
        return print_status(rows, status_totals(rows), as_json=args.json)
    if args.command == "ocr":
        return ingest_ocr(args)
    if args.command == "index":
        return ingest_index(args)
    if args.command == "summarize":
        return ingest_summarize(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
