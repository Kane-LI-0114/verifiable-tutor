#!/usr/bin/env python3
"""Local driver for the TACC Qwen document-summary job.

The ``tacc/serve`` job serves Qwen once and answers either a
``vt-kb-request/1`` card batch or a ``vt-summary-request/1`` document-summary
batch. This driver owns the summary phase: it builds one input line per document
(outline plus the first two pages), uploads the request, submits the job, polls
it, downloads the summaries, validates them against
``docs/knowledge-schema.md`` section 6, and stores one summary per document in
the local knowledge store. Course text never leaves the platform.

Usage:
  .venv/bin/python scripts/tacc/run_summary_job.py --input data/index/summary-input.jsonl
  .venv/bin/python scripts/tacc/run_summary_job.py --input data/index/summary-input.jsonl --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import yaml  # noqa: E402

from verifiable_tutor.knowledge.request import build_summary_request  # noqa: E402
from verifiable_tutor.knowledge.schema import validate_document_summary  # noqa: E402

JOB_TEMPLATE = REPO_ROOT / "tacc" / "serve"
SUBMIT_HELPER = REPO_ROOT / "scripts" / "tacc" / "submit.sh"
CONFIG_PATH = REPO_ROOT / "config" / "knowledge.yaml"
SUMMARY_PROMPT = REPO_ROOT / "src" / "verifiable_tutor" / "prompts" / "kb_doc_summary_v1.md"
TCLOUD = shutil.which("tcloud") or (
    str(Path.home() / ".local" / "bin" / "tcloud")
    if (Path.home() / ".local" / "bin" / "tcloud").is_file()
    else "tcloud"
)
FINISHED_STATES = {"CD", "CA", "F", "TO", "NF", "OOM", "BF", "PR"}
SUMMARY_REQUEST_SCHEMA = "vt-summary-request/1"
JOB_FILES = ("job.sh", "kb_worker.py", "tuxiv.conf")
PROMPT_STAGED_NAME = "kb_doc_summary_v1.md"


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(command, cwd=None, timeout=None, check=False):
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(map(str, command))}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def tacc_paths() -> str:
    userconfig = Path.home() / ".tcloud" / ".userconfig"
    clusterconfig = Path.home() / ".tcloud" / ".clusterconfig"
    user = json.loads(userconfig.read_text()).get("UserName", "")
    cluster = json.loads(clusterconfig.read_text())
    home = cluster.get("homedir", "/mnt/home")
    userdir = cluster.get("dirs", {}).get("userdir", "USERDIR")
    if not user:
        raise SystemExit("no tcloud user configured; run tcloud config first")
    return f"{home}/{user}/{userdir}"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def prepare_job(
    *, build_id: str, documents: list[dict], userdir: str, config: dict, force: bool = False
) -> dict:
    """Write the local request, input and task directory. No TACC access."""

    local_root = REPO_ROOT / "data" / "caches" / "summary-requests" / build_id
    if local_root.exists() and not force:
        raise SystemExit(
            f"{local_root} already exists; pass --build-id or --force to replace it"
        )
    summary_config = config.get("summary") or {}
    request = build_summary_request(
        build_id=build_id,
        documents=documents,
        userdir=userdir,
        prompt_version=str(summary_config.get("prompt_version", "doc-summary-v1")),
        model=str(summary_config.get("model", "qwen3.8-27b")),
        params={
            "temperature": float(summary_config.get("temperature", 0.0)),
            "max_output_tokens": int(summary_config.get("max_output_tokens", 1024)),
            "document_count": len(documents),
            "max_repair_attempts": int(summary_config.get("max_repair_attempts", 1)),
        },
    )
    request_path = local_root / "request.json"
    input_path = local_root / "input.jsonl"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_jsonl(input_path, documents)
    task_dir = local_root / "task"
    task_dir.mkdir(parents=True, exist_ok=True)
    for name in JOB_FILES:
        shutil.copyfile(JOB_TEMPLATE / name, task_dir / name)
    shutil.copyfile(SUMMARY_PROMPT, task_dir / PROMPT_STAGED_NAME)
    shutil.copyfile(request_path, task_dir / "request.json")
    shutil.copyfile(input_path, task_dir / "input.jsonl")
    return {
        "build_id": build_id,
        "request": request,
        "documents": documents,
        "local_root": local_root,
        "request_path": request_path,
        "input_path": input_path,
        "task_dir": task_dir,
        "userdir": userdir,
        "job_name": (config.get("jobs", {}).get("summary") or {}).get("name", "vt-kb"),
    }


def upload_input(job: dict) -> dict:
    """Upload the summary input to the USERDIR root; the worker moves it."""

    remote_name = f"{job['build_id']}-summary-input.jsonl"
    # tcloud upload keeps the local basename, so stage the build-scoped name
    # that the worker looks for at the USERDIR root.
    upload_source = job["local_root"] / remote_name
    shutil.copyfile(job["input_path"], upload_source)
    text = ""
    for attempt in range(1, 4):
        try:
            result = run([TCLOUD, "upload", str(upload_source), "."], timeout=900)
        except subprocess.TimeoutExpired as exc:
            text = f"timeout: {exc}"
        else:
            text = result.stdout + result.stderr
            if result.returncode == 0 and "[Tcloud Error]" not in text and "Failed to" not in text:
                break
        log(f"[summary] upload attempt {attempt} failed; retrying")
        time.sleep(10 * attempt)
    else:
        log(f"[summary] upload failed: {text.strip()[-300:]}")
        return {"mode": "task_dir", "remote_name": ""}
    log(f"[summary] uploaded {remote_name} to {job['userdir']}/")
    return {"mode": "userdir_root", "remote_name": remote_name}


def submit_job(job: dict) -> dict:
    staging = run(
        ["bash", str(SUBMIT_HELPER), str(job["task_dir"]), "--no-submit"], timeout=120
    )
    if staging.returncode != 0:
        raise SystemExit(f"staging failed:\n{staging.stdout}\n{staging.stderr}")
    started = time.time()
    submit_text = ""
    match = None
    for attempt in range(1, 4):
        try:
            submit = run([TCLOUD, "submit"], cwd=job["task_dir"], timeout=420)
            submit_text = submit.stdout + submit.stderr
        except subprocess.TimeoutExpired as exc:
            submit_text = f"timeout: {exc}"
        match = re.search(r"Submitted batch job\s+(\d+)", submit_text)
        if match:
            break
        log(f"[summary] submit attempt {attempt} failed; retrying in {15 * attempt}s")
        time.sleep(15 * attempt)
    if not match:
        raise SystemExit(f"submit failed:\n{submit_text}")
    job_id = match.group(1)
    log(f"[summary] submitted job {job_id} (build {job['build_id']})")
    return {"job_id": job_id, "submitted_epoch": started}


def poll_job(job_id: str, *, timeout_s: int, poll_s: int) -> None:
    started = time.time()
    state = ""
    while True:
        if time.time() - started > timeout_s:
            run([TCLOUD, "cancel", "-j", job_id], timeout=120)
            raise SystemExit(
                f"job {job_id} did not finish within {timeout_s}s "
                f"(last state {state or 'unknown'}); cancelled"
            )
        try:
            status = run([TCLOUD, "ps", "-j", job_id], timeout=120)
            status_text = status.stdout + status.stderr
        except subprocess.TimeoutExpired:
            status_text = "timeout"
        if "Tcloud Error" in status_text or status_text.strip() == "timeout":
            log(f"[summary] job {job_id}: status query failed; retrying")
            time.sleep(poll_s)
            continue
        row = [
            line
            for line in status_text.splitlines()
            if line.strip().startswith(job_id)
        ]
        if not row:
            log(f"[summary] job {job_id} left the queue")
            return
        fields = row[0].split()
        state = fields[4] if len(fields) > 4 else ""
        log(f"[summary] job {job_id} state={state} elapsed={int(time.time() - started)}s")
        if state in FINISHED_STATES:
            return
        time.sleep(poll_s)


def fetch_log(job: dict, job_id: str) -> Path:
    log_path = f"slurm_log/{job['job_name']}-{job_id}.log"
    target = job["local_root"] / f"job-{job_id}.log"
    for _ in range(6):
        try:
            result = run([TCLOUD, "cat", log_path], timeout=120)
        except subprocess.TimeoutExpired:
            time.sleep(3)
            continue

        if result.returncode == 0 and result.stdout.strip():
            target.write_text(result.stdout, encoding="utf-8")
            return target
        time.sleep(3)
    return target


def download_artifact(remote: str, target: Path, *, timeout_s: int = 900) -> bool:
    """Download one file, retrying timeouts and discarding partial copies.

    The platform gateway can take minutes per file and a timed-out ``tcloud
    download`` leaves a truncated file behind; neither may kill the driver or
    masquerade as a finished artifact.
    """

    target.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        if target.exists():
            target.unlink()
        try:
            result = run([TCLOUD, "download", remote, str(target)], timeout=timeout_s)
        except subprocess.TimeoutExpired:
            time.sleep(3)
            continue
        if result.returncode == 0 and target.is_file():
            return True
        time.sleep(3)
    return False


def download_results(job: dict, job_id: str) -> Path:
    local_dir = REPO_ROOT / "data" / "caches" / "summary-results" / job["build_id"]
    local_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = f"kb/results/{job['build_id']}"
    for name in ("summaries.jsonl", "progress.json", "summary.json"):
        download_artifact(f"{remote_dir}/{name}", local_dir / name)
    return local_dir


def store_summaries(results_dir: Path, documents: list[dict], request: dict) -> dict:
    """Validate the downloaded summaries and store the valid ones."""

    from verifiable_tutor.corpus.store import KnowledgeStore
    from verifiable_tutor.storage import Storage

    summaries_path = results_dir / "summaries.jsonl"
    if not summaries_path.is_file():
        raise SystemExit(f"missing artifact: {summaries_path}")
    records = [
        json.loads(line)
        for line in summaries_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected = {str(document["doc_id"]): document for document in documents}
    seen: set[str] = set()
    valid: dict[str, dict] = {}
    invalid: list[dict] = []
    for record in records:
        doc_id = str(record.get("doc_id") or "")
        issues = validate_document_summary(record, doc_ids=sorted(expected))
        if doc_id not in expected:
            issues.append(f"doc_id {doc_id!r} was not in the request")
        if doc_id in seen:
            issues.append(f"duplicate summary for {doc_id}")
        seen.add(doc_id)
        if record.get("corpus_hash") != request["corpus_hash"]:
            issues.append("corpus_hash does not match the request")
        if doc_id in expected and int(record.get("page_count") or 0) != int(
            expected[doc_id].get("page_count") or 0
        ):
            issues.append("page_count does not match the summary input")
        if issues:
            invalid.append({"doc_id": doc_id, "issues": issues})
        else:
            valid[doc_id] = record
    missing = sorted(set(expected) - set(valid) - {item["doc_id"] for item in invalid})

    store = None
    database_path = REPO_ROOT / "data" / "app" / "app.sqlite3"
    app_config = REPO_ROOT / "config" / "app.yaml"
    if app_config.is_file():
        app = yaml.safe_load(app_config.read_text(encoding="utf-8")) or {}
        database_path = REPO_ROOT / str(
            (app.get("data") or {}).get("database_path", database_path)
        )
    if valid:
        store = KnowledgeStore(Storage(database_path))
        for doc_id, record in valid.items():
            store.set_document_summary(
                doc_id,
                summary=str(record["summary"]),
                model=str(record["model"]),
                created_at=str(record["created_at"]),
                updated_at=now_iso(),
            )
    return {
        "documents": valid,
        "invalid": invalid,
        "missing": missing,
        "downloaded": len(records),
        "expected": len(expected),
    }


def run_summary(
    *,
    documents: list[dict],
    state: dict,
    resume: bool = False,
    force: bool = False,
    build_id: str | None = None,
    dry_run: bool = False,
    timeout_s: int | None = None,
    poll_s: int | None = None,
) -> dict:
    """Run one document-summary job end to end and return the ingest report."""

    config = load_config()
    if resume and not force:
        done = {
            doc_id
            for doc_id, record in state.items()
            if (record.get("summary") or {}).get("status") == "done"
        }
        if done:
            documents = [
                document for document in documents if document["doc_id"] not in done
            ]
            log(f"[summary] resuming: {len(done)} document(s) already summarised")
    if not documents:
        return {"ok": True, "build_id": build_id or "", "job_id": "", "skipped": True}
    build_id = build_id or datetime.now(timezone.utc).strftime("sum-%Y%m%d-%H%M%S")
    userdir = tacc_paths()
    job = prepare_job(
        build_id=build_id,
        documents=documents,
        userdir=userdir,
        config=config,
        force=force,
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "build_id": build_id,
            "task_dir": str(job["task_dir"]),
            "request": job["request"],
            "documents": [document["doc_id"] for document in documents],
        }
    upload = upload_input(job)
    submission = submit_job(job)
    job["job_id"] = submission["job_id"]
    summary_config = config.get("jobs", {}).get("summary") or {}
    if timeout_s is None:
        timeout_s = int(summary_config.get("queue_timeout_s", 3600))
    if poll_s is None:
        poll_s = int(summary_config.get("poll_interval_s", 30))
    try:
        poll_job(submission["job_id"], timeout_s=timeout_s, poll_s=poll_s)
    finally:
        job_log = fetch_log(job, submission["job_id"])
        log(f"[summary] job log: {job_log}")
    results_dir = download_results(job, submission["job_id"])
    job_summary_path = results_dir / "summary.json"
    if not job_summary_path.is_file():
        raise SystemExit(
            f"job {submission['job_id']} wrote no summary.json; see {job_log}"
        )
    job_summary = json.loads(job_summary_path.read_text(encoding="utf-8"))
    stored = store_summaries(results_dir, documents, job["request"])
    job_started = float(job_summary.get("job_started_epoch") or submission["submitted_epoch"])
    ok = (
        not stored["invalid"]
        and not stored["missing"]
        and len(stored["documents"]) == len(documents)
    )
    return {
        "ok": ok,
        "build_id": build_id,
        "job_id": submission["job_id"],
        "upload_mode": upload["mode"],
        "documents_requested": len(documents),
        "summaries_downloaded": stored["downloaded"],
        "summaries_valid": len(stored["documents"]),
        "invalid": stored["invalid"],
        "missing": stored["missing"],
        "documents": {
            doc_id: {
                "page_count": int(record.get("page_count") or 0),
                "model": record.get("model"),
                "created_at": record.get("created_at"),
            }
            for doc_id, record in stored["documents"].items()
        },
        "timings": {
            "queue_seconds": round(
                max(0.0, job_started - submission["submitted_epoch"]), 3
            ),
            "vllm_startup_seconds": job_summary.get("vllm_startup_seconds"),
            "build_seconds": job_summary.get("build_seconds"),
            "elapsed_seconds": job_summary.get("total_seconds"),
            "wall_seconds": round(
                max(0.0, time.time() - submission["submitted_epoch"]), 3
            ),
        },
        "results_dir": str(results_dir),
        "job_log": str(job_log),
        "task_dir": str(job["task_dir"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        help="summary input JSONL, one line per document with doc_id, page_count, outline, excerpt",
    )
    parser.add_argument("--build-id", default=None)
    parser.add_argument("--state", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--poll-seconds", type=int, default=None)
    args = parser.parse_args(argv)

    documents = [
        json.loads(line)
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    state: dict = {}
    if args.state:
        state = json.loads(Path(args.state).read_text(encoding="utf-8")).get(
            "documents", {}
        )
    report = run_summary(
        documents=documents,
        state=state,
        resume=args.resume,
        force=args.force,
        build_id=args.build_id,
        dry_run=args.dry_run,
        timeout_s=args.timeout,
        poll_s=args.poll_seconds,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
