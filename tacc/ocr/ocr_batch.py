#!/usr/bin/env python3
"""Run the per-document OCR stages of one ``vt-ocr-request/1`` batch.

This script runs inside the submitted ``tacc/ocr`` GPU job, after the job has
bootstrapped the project layer and started the PaddleOCR-VL vLLM server. It
walks the documents of the manifest in order and, for each one, runs the shared
stages: enumerate pages, render at 200 DPI, recognise through the local
OpenAI endpoint, and assemble one document markdown. It stops starting new
documents when the OCR stage cap or the whole-body deadline is reached and
records which documents it finished, so a resumed run only parses the rest.

Artifacts land under ``out_dir`` (on ``USERDIR``)::

    pages/<doc>.jsonl           one vt-page-record/1 per page
    document/<doc>-ocr.md       assembled document markdown
    images/<doc>.pNNN.webp      page image for the citation panel
    logs/<doc>-<job>.log        stage output for one document
    manifest.json               per-document status, written as work proceeds
    summary.json                job totals and timings

It uses the Python standard library only; the shared stage scripts it calls run
under the project interpreter it is given with ``--vt-python``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_SCHEMA = "vt-ocr-manifest/1"
SUMMARY_SCHEMA = "vt-ocr-batch/1"
REQUEST_SCHEMA = "vt-ocr-request/1"
#: A document that cannot get this much budget is marked skipped, not failed.
MIN_DOCUMENT_SECONDS = 60
#: Reserve for teardown, image copy and tar after the last recognition call.
BODY_RESERVE_SECONDS = 90


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[ocr-batch] {message}", flush=True)


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ocr_stage_exhausted(ocr_seconds_total: float, stage_seconds: float) -> bool:
    """True when the summed recognition time has reached the OCR stage cap."""

    return float(ocr_seconds_total) >= float(stage_seconds)


def count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def run_stage(
    command: list[str], *, log_path: Path, timeout: float
) -> tuple[int, float]:
    """Run one stage, appending its output to the document log."""

    started = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n$ {' '.join(command)}\n")
        handle.flush()
        try:
            completed = subprocess.run(
                command,
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=max(30.0, timeout),
            )
            code = completed.returncode
        except subprocess.TimeoutExpired:
            handle.write(f"\n[stage] timeout after {timeout:.0f}s\n")
            code = 124
    return code, round(time.time() - started, 3)


def resolve_pdf(pdf_name: str, *, pdf_dir: Path, userdir: Path, task_dir: Path) -> Path | None:
    """Find one uploaded PDF: batch directory first, then the USERDIR root."""

    for candidate in (
        pdf_dir / pdf_name,
        userdir / pdf_name,
        task_dir / pdf_name,
    ):
        if candidate.is_file():
            return candidate
    return None


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def skipped_record(doc: dict, *, error: str, log_path: str) -> dict:
    return {
        "doc_id": doc["doc_id"],
        "pdf": doc["pdf"],
        "status": "skipped",
        "pages": 0,
        "pages_ok": 0,
        "seconds": 0.0,
        "error": error,
        "log_path": log_path,
    }


def process_document(
    doc: dict,
    *,
    request: dict,
    out_dir: Path,
    task_dir: Path,
    staged: Path,
    args: argparse.Namespace,
    ocr_remaining: float,
    body_deadline: float,
) -> dict:
    """Run every stage for one document and return its manifest record."""

    started = time.time()
    doc_id = doc["doc_id"]
    pdf_name = doc["pdf"]
    work = out_dir / "work" / doc_id
    work.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "logs" / f"{doc_id}-{args.job_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"=== {doc_id} {pdf_name} {now_iso()} ===\n", encoding="utf-8")
    record = {
        "doc_id": doc_id,
        "pdf": pdf_name,
        "status": "failed",
        "pages": 0,
        "pages_ok": 0,
        "blocks": 0,
        "chars": 0,
        "seconds": 0.0,
        "pages_path": f"pages/{doc_id}.jsonl",
        "document_md": f"document/{doc_id}-ocr.md",
        "log_path": f"logs/{doc_id}-{args.job_id}.log",
        "error": None,
    }

    source = resolve_pdf(
        pdf_name,
        pdf_dir=Path(request["pdf_dir"]),
        userdir=Path(args.userdir),
        task_dir=task_dir,
    )
    if source is None:
        record["error"] = f"pdf not found in {request['pdf_dir']} or {args.userdir}"
        return record

    input_pdf = work / "input" / pdf_name
    input_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, input_pdf)
    doc_sha = sha256_file(input_pdf)
    doc_pages = work / "doc-pages.json"

    code, seconds = run_stage(
        [
            args.vt_python,
            str(staged / "enumerate_pages.py"),
            "--pdf",
            str(input_pdf),
            "--out",
            str(doc_pages),
        ],
        log_path=log_path,
        timeout=300,
    )
    if code != 0 or not doc_pages.is_file():
        record["error"] = f"enumerate_pages rc={code}"
        record["seconds"] = round(time.time() - started, 3)
        return record
    page_count = len(json.loads(doc_pages.read_text(encoding="utf-8")))
    record["pages"] = int(page_count)

    render_budget = min(900.0, body_deadline - time.time() - BODY_RESERVE_SECONDS)
    if render_budget < MIN_DOCUMENT_SECONDS:
        record["status"] = "skipped"
        record["error"] = "body deadline reached before render"
        record["seconds"] = round(time.time() - started, 3)
        return record
    code, _seconds = run_stage(
        [
            args.vt_python,
            str(staged / "render_pages.py"),
            "--pages",
            str(doc_pages),
            "--pdf-root",
            str(work / "input"),
            "--out-dir",
            str(work),
            "--dpi",
            str(request.get("dpi", 200)),
        ],
        log_path=log_path,
        timeout=render_budget,
    )
    render_manifest = work / "render-manifest.json"
    rendered = 0
    if render_manifest.is_file():
        rendered = sum(
            1
            for entry in json.loads(render_manifest.read_text(encoding="utf-8"))
            if entry.get("status") == "ok"
        )
    if code != 0 or rendered != page_count or page_count == 0:
        record["error"] = f"render_pages rc={code} rendered={rendered}/{page_count}"
        record["seconds"] = round(time.time() - started, 3)
        return record

    ocr_budget = min(
        1800.0,
        ocr_remaining,
        body_deadline - time.time() - BODY_RESERVE_SECONDS,
    )
    if ocr_budget < MIN_DOCUMENT_SECONDS:
        record["status"] = "skipped"
        record["error"] = "ocr stage budget exhausted"
        record["seconds"] = round(time.time() - started, 3)
        return record
    pages_jsonl = out_dir / "pages" / f"{doc_id}.jsonl"
    pages_jsonl.parent.mkdir(parents=True, exist_ok=True)
    records_json = work / f"records-{args.job_id}.json"
    code, ocr_seconds = run_stage(
        [
            args.vt_python,
            str(staged / "ocr_pages.py"),
            "--manifest",
            str(render_manifest),
            "--server-url",
            args.server_url,
            "--api-model-name",
            args.served_name,
            "--layout-model-dir",
            args.layout_model_dir,
            "--pipeline-version",
            args.pipeline_version,
            "--device",
            args.device,
            "--max-concurrency",
            str(args.max_concurrency),
            "--out-jsonl",
            str(pages_jsonl),
            "--out-summary",
            str(records_json),
            "--out-dir",
            str(work),
        ],
        log_path=log_path,
        timeout=ocr_budget,
    )
    record["ocr_seconds"] = ocr_seconds
    pages_ok = 0
    if records_json.is_file():
        summary = json.loads(records_json.read_text(encoding="utf-8"))
        pages_ok = int(summary.get("pages_ok") or 0)
        record["blocks"] = int(summary.get("blocks_total") or 0)
    record["pages_ok"] = pages_ok
    if code != 0 or pages_ok != page_count:
        record["error"] = f"ocr_pages rc={code} pages_ok={pages_ok}/{page_count}"
        record["seconds"] = round(time.time() - started, 3)
        return record

    document_md = out_dir / "document" / f"{doc_id}-ocr.md"
    document_md.parent.mkdir(parents=True, exist_ok=True)
    code, _seconds = run_stage(
        [
            args.vt_python,
            str(staged / "assemble_document.py"),
            "--jsonl",
            str(pages_jsonl),
            "--out",
            str(document_md),
            "--doc-id",
            doc_id,
            "--pdf",
            pdf_name,
            "--pdf-sha256",
            doc_sha,
        ],
        log_path=log_path,
        timeout=300,
    )
    if code != 0 or not document_md.is_file():
        record["error"] = f"assemble_document rc={code}"
        record["seconds"] = round(time.time() - started, 3)
        return record

    images_source = work / "images"
    if images_source.is_dir():
        images_target = out_dir / "images"
        images_target.mkdir(parents=True, exist_ok=True)
        for image in images_source.glob("*.webp"):
            shutil.copyfile(image, images_target / image.name)

    if pages_jsonl.is_file():
        with pages_jsonl.open(encoding="utf-8") as handle:
            record["chars"] = sum(
                len(json.loads(line).get("text") or "")
                for line in handle
                if line.strip()
            )
    record["status"] = "done"
    record["seconds"] = round(time.time() - started, 3)
    log(f"done {doc_id}: pages={pages_ok}/{page_count} seconds={record['seconds']}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--staged", default=None)
    parser.add_argument("--vt-python", required=True)
    parser.add_argument("--server-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--served-name", default="PaddleOCR-VL-1.6-0.9B")
    parser.add_argument("--layout-model-dir", default="")
    parser.add_argument("--pipeline-version", default="v1.6")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-concurrency", type=int, default=8)
    parser.add_argument("--job-id", default=os.environ.get("SLURM_JOB_ID", "manual"))
    parser.add_argument("--job-started-epoch", type=float, default=None)
    parser.add_argument("--vllm-startup-seconds", type=float, default=0.0)
    parser.add_argument("--launcher", default="direct")
    parser.add_argument(
        "--userdir",
        default=os.environ.get("TACC_USERDIR", os.environ.get("HOME", "")),
    )
    args = parser.parse_args()

    worker_started = time.time()
    job_started = args.job_started_epoch or worker_started
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if request.get("schema") != REQUEST_SCHEMA:
        raise SystemExit(f"request schema must be {REQUEST_SCHEMA}")
    out_dir = Path(args.out_dir or request["out_dir"])
    staged = Path(args.staged or (Path(args.request).parent / "_staged"))
    task_dir = Path(args.request).resolve().parent
    for name in ("pages", "document", "images", "logs", "work"):
        (out_dir / name).mkdir(parents=True, exist_ok=True)

    body_deadline_seconds = float(request.get("body_deadline_seconds", 3300))
    body_deadline = job_started + body_deadline_seconds
    ocr_stage_seconds = float(request.get("ocr_stage_seconds", 1800))
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "batch_id": request.get("batch_id", ""),
        "job_id": args.job_id,
        "out_dir": str(out_dir),
        "started_at": now_iso(),
        "documents": [],
    }
    manifest_path = out_dir / "manifest.json"
    log(
        f"batch={request.get('batch', '')} docs={len(request.get('documents') or [])} "
        f"out={out_dir} body_budget={body_deadline - worker_started:.0f}s "
        f"ocr_stage_budget={ocr_stage_seconds:.0f}s"
    )

    ocr_seconds_total = 0.0
    for doc in request.get("documents") or []:
        if time.time() > body_deadline - BODY_RESERVE_SECONDS:
            record = skipped_record(
                doc,
                error="body deadline reached before the document started",
                log_path=f"logs/{doc['doc_id']}-{args.job_id}.log",
            )
            log(f"skip {doc['doc_id']}: body deadline")
        elif ocr_stage_exhausted(ocr_seconds_total, ocr_stage_seconds):
            record = skipped_record(
                doc,
                error="ocr stage budget exhausted before the document started",
                log_path=f"logs/{doc['doc_id']}-{args.job_id}.log",
            )
            log(f"skip {doc['doc_id']}: ocr stage budget")
        else:
            record = process_document(
                doc,
                request=request,
                out_dir=out_dir,
                task_dir=task_dir,
                staged=staged,
                args=args,
                ocr_remaining=max(0.0, ocr_stage_seconds - ocr_seconds_total),
                body_deadline=body_deadline,
            )
        ocr_seconds_total += float(record.get("ocr_seconds") or 0.0)
        manifest["documents"].append(record)
        write_json(manifest_path, manifest)

    documents = manifest["documents"]
    done = sum(1 for record in documents if record["status"] == "done")
    skipped = sum(1 for record in documents if record["status"] == "skipped")
    failed = sum(1 for record in documents if record["status"] == "failed")
    summary = {
        "schema": SUMMARY_SCHEMA,
        "batch_id": request.get("batch_id", ""),
        "batch": request.get("batch", ""),
        "job_id": args.job_id,
        "host": os.uname().nodename,
        "out_dir": str(out_dir),
        "generated_at": now_iso(),
        "request": request,
        "documents": documents,
        "documents_total": len(documents),
        "documents_done": done,
        "documents_skipped": skipped,
        "documents_failed": failed,
        "pages_total": sum(int(record["pages"]) for record in documents),
        "pages_ok": sum(int(record["pages_ok"]) for record in documents),
        "blocks_total": sum(int(record.get("blocks") or 0) for record in documents),
        "chars_total": sum(int(record.get("chars") or 0) for record in documents),
        "ocr_seconds": round(ocr_seconds_total, 3),
        "vllm_startup_seconds": round(args.vllm_startup_seconds, 3),
        "launcher": args.launcher,
        "elapsed_seconds": round(time.time() - job_started, 3),
        "pass": done,
        "fail": failed + skipped,
    }
    write_json(out_dir / "summary.json", summary)
    log(
        f"finished done={done} skipped={skipped} failed={failed} "
        f"pages_ok={summary['pages_ok']}/{summary['pages_total']}"
    )
    return 0 if done > 0 and failed + skipped == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
