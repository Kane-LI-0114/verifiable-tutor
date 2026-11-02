#!/usr/bin/env python3
"""Local interface for one TACC Qwen knowledge-base job (spike 10).

Round trip: turn OCR page records into knowledge-base input chunks, write the
``vt-kb-request/1`` manifest, upload the request and input to ``USERDIR``,
submit the ``tacc/serve`` GPU job, poll it, download the records, progress and
summary, validate them against ``docs/knowledge-schema.md``, and store the
canonical JSONL under ``data/kb/``.

The TACC job only writes results; this driver decides whether the build passed.

Usage:
  .venv/bin/python scripts/tacc/run_kb_job.py --pages \
      data/caches/parse-results/20261029-203110-360/pages.jsonl --max-chunks 8
  .venv/bin/python scripts/tacc/run_kb_job.py --pages <pages.jsonl> --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
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

from verifiable_tutor.knowledge import (  # noqa: E402
    build_request,
    chunks_from_pages,
    normalize_doc_id,
    validate_progress,
    validate_record,
)

JOB_TEMPLATE = REPO_ROOT / "tacc" / "serve"
SUBMIT_HELPER = REPO_ROOT / "scripts" / "tacc" / "submit.sh"
CONFIG_PATH = REPO_ROOT / "config" / "knowledge.yaml"
TCLOUD = shutil.which("tcloud") or "tcloud"
FINISHED_STATES = {"CD", "CA", "F", "TO", "NF", "OOM", "BF", "PR"}
JOB_FILES = ("job.sh", "kb_worker.py", "prompt_kb_v1.md", "tuxiv.conf")
REQUEST_UPLOAD_DIR = "kb/requests"
RESULT_UPLOAD_DIR = "kb/results"


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def tacc_paths() -> str:
    """Read the tcloud config to build the absolute USERDIR path."""

    userconfig = Path.home() / ".tcloud" / ".userconfig"
    clusterconfig = Path.home() / ".tcloud" / ".clusterconfig"
    user = json.loads(userconfig.read_text()).get("UserName", "")
    cluster = json.loads(clusterconfig.read_text())
    home = cluster.get("homedir", "/mnt/home")
    userdir = cluster.get("dirs", {}).get("userdir", "USERDIR")
    if not user:
        raise SystemExit("no tcloud user configured; run tcloud config first")
    return f"{home}/{user}/{userdir}"


def load_pages(path: Path) -> list[dict]:
    pages = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            page = json.loads(line)
            if page.get("schema") != "vt-page-record/1":
                raise SystemExit(
                    f"{path} line {line_number}: expected vt-page-record/1"
                )
            pages.append(page)
    if not pages:
        raise SystemExit(f"no page records in {path}")
    return pages


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def prepare_build(args, config: dict) -> dict:
    """Write the local request, input and task directory. No TACC access."""

    pages = load_pages(Path(args.pages))
    chunks = chunks_from_pages(
        pages, doc_id=args.doc_id, max_chunks=args.max_chunks
    )
    if not chunks:
        raise SystemExit("no chunks with text were produced from the page records")
    build_id = args.build_id or datetime.now(timezone.utc).strftime("kb-%Y%m%d-%H%M%S")
    local_root = REPO_ROOT / "data" / "caches" / "kb-requests" / build_id
    if local_root.exists() and not args.force:
        raise SystemExit(
            f"{local_root} already exists; pass --build-id or --force to replace it"
        )
    userdir = tacc_paths()
    params = {
        "temperature": 0.0,
        "max_output_tokens": 1024,
        "chunk_count": len(chunks),
        "max_repair_attempts": 1,
    }
    request = build_request(
        build_id=build_id,
        chunks=chunks,
        userdir=userdir,
        prompt_version=config["build"]["prompt_version"],
        model=config["model"]["name"],
        params=params,
    )
    request_path = local_root / "request.json"
    input_path = local_root / "input.jsonl"
    write_json(request_path, request)
    write_jsonl(input_path, chunks)
    task_dir = local_root / "task"
    task_dir.mkdir(parents=True, exist_ok=True)
    for name in JOB_FILES:
        shutil.copyfile(JOB_TEMPLATE / name, task_dir / name)
    shutil.copyfile(request_path, task_dir / "request.json")
    shutil.copyfile(input_path, task_dir / "input.jsonl")
    return {
        "build_id": build_id,
        "request": request,
        "chunks": chunks,
        "local_root": local_root,
        "request_path": request_path,
        "input_path": input_path,
        "task_dir": task_dir,
        "userdir": userdir,
        "job_name": config["job"]["name"],
    }


def tcloud_failed(result) -> bool:
    """The CLI can print a transfer error and still exit 0."""

    text = result.stdout + result.stderr
    return result.returncode != 0 or "[Tcloud Error]" in text or "Failed to" in text


def upload_request(build: dict) -> dict:
    """Upload the request and input to USERDIR and report the round trip.

    ``tcloud upload`` cannot create a nested remote directory, so the files go
    to the USERDIR root with build-scoped names and the job moves them into the
    canonical ``kb/requests/<build_id>/`` layout. If even that upload fails the
    job falls back to the task-directory copies.
    """

    build_id = build["build_id"]
    remote_names = {
        "request": f"{build_id}-request.json",
        "input": f"{build_id}-input.jsonl",
    }
    for local, name in (
        (build["request_path"], remote_names["request"]),
        (build["input_path"], remote_names["input"]),
    ):
        result = run([TCLOUD, "upload", str(local), "."], timeout=600)
        if tcloud_failed(result):
            log(
                f"[kb] upload failed for {name}: "
                f"{(result.stdout + result.stderr).strip()[-300:]}"
            )
            log("[kb] falling back to the staged task directory; the job will relocate")
            return {"mode": "task_dir_relocated", "remote_names": {}}
    log(
        f"[kb] uploaded request and input to {build['userdir']}/ "
        f"({remote_names['request']}, {remote_names['input']})"
    )
    return {"mode": "userdir_root", "remote_names": remote_names}


def submit_job(build: dict) -> dict:
    staging = run(
        ["bash", str(SUBMIT_HELPER), str(build["task_dir"]), "--no-submit"],
        timeout=120,
    )
    if staging.returncode != 0:
        raise SystemExit(
            f"staging failed:\n{staging.stdout}\n{staging.stderr}"
        )
    started = time.time()
    submit = run([TCLOUD, "submit"], cwd=build["task_dir"], timeout=300)
    match = re.search(r"Submitted batch job\s+(\d+)", submit.stdout + submit.stderr)
    if not match:
        raise SystemExit(
            f"submit failed:\n{submit.stdout}\n{submit.stderr}"
        )
    job_id = match.group(1)
    log(f"[kb] submitted job {job_id} (build {build['build_id']})")
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
        status = run([TCLOUD, "ps", "-j", job_id], timeout=120)
        text = status.stdout + status.stderr
        row = [line for line in text.splitlines() if line.strip().startswith(job_id)]
        if not row:
            log(f"[kb] job {job_id} left the queue")
            return
        fields = row[0].split()
        state = fields[4] if len(fields) > 4 else ""
        log(
            f"[kb] job {job_id} state={state} "
            f"elapsed={int(time.time() - started)}s"
        )
        if state in FINISHED_STATES:
            return
        time.sleep(poll_s)


def fetch_log(build: dict, job_id: str) -> Path:
    log_path = f"slurm_log/{build['job_name']}-{job_id}.log"
    target = build["local_root"] / f"job-{job_id}.log"
    for _ in range(6):
        result = run([TCLOUD, "cat", log_path], timeout=120)
        if result.returncode == 0 and result.stdout.strip():
            target.write_text(result.stdout, encoding="utf-8")
            return target
        time.sleep(3)
    return target


def download_results(build: dict) -> Path:
    local_dir = REPO_ROOT / "data" / "caches" / "kb-results" / build["build_id"]
    local_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = f"{RESULT_UPLOAD_DIR}/{build['build_id']}"
    for name in ("records.jsonl", "progress.json", "summary.json"):
        target = local_dir / name
        for _ in range(5):
            result = run([TCLOUD, "download", f"{remote_dir}/{name}", str(target)], timeout=180)
            if result.returncode == 0 and target.is_file():
                break
            time.sleep(2)
    return local_dir


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"missing artifact: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_build(build: dict, results_dir: Path, summary: dict) -> dict:
    request = build["request"]
    chunks = build["chunks"]
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    pages = {(chunk["doc_id"], chunk["page_no"]): chunk["text"] for chunk in chunks}
    records = load_jsonl(results_dir / "records.jsonl")
    progress = load_json(results_dir / "progress.json")

    invalid = []
    seen: set[str] = set()
    valid = 0
    for record in records:
        chunk_id = str(record.get("chunk_id", ""))
        issues = validate_record(record, pages)
        if chunk_id not in chunk_by_id:
            issues.append(f"chunk_id {chunk_id!r} was not in the input batch")
        if chunk_id in seen:
            issues.append(f"duplicate record for {chunk_id}")
        seen.add(chunk_id)
        if record.get("corpus_hash") != request["corpus_hash"]:
            issues.append("corpus_hash does not match the request")
        if issues:
            invalid.append({"chunk_id": chunk_id, "issues": issues})
        else:
            valid += 1
    progress_issues = validate_progress(progress)
    if progress.get("status") != "done":
        progress_issues.append("progress status is not done")
    if progress.get("done_chunks") != len(chunks):
        progress_issues.append("progress done_chunks does not match the chunk count")

    hashes = {
        "request": sha256_file(build["request_path"]),
        "input": sha256_file(build["input_path"]),
    }
    for name in ("records.jsonl", "progress.json", "summary.json"):
        path = results_dir / name
        if path.is_file():
            hashes[name] = sha256_file(path)

    passed = (
        len(records) == len(chunks)
        and valid == len(chunks)
        and not progress_issues
    )
    return {
        "chunks": len(chunks),
        "records_downloaded": len(records),
        "records_valid": valid,
        "invalid_records": invalid,
        "progress": progress,
        "progress_issues": progress_issues,
        "artifact_hashes": hashes,
        "pass": passed,
    }


def store_build(
    build: dict,
    results_dir: Path,
    summary: dict,
    validation: dict,
    *,
    revalidated: bool = False,
    queue_seconds: float | None = None,
) -> dict:
    kb_records = REPO_ROOT / "data" / "kb" / "records" / f"{build['build_id']}.jsonl"
    kb_builds = REPO_ROOT / "data" / "kb" / "builds" / f"{build['build_id']}.json"
    kb_records.parent.mkdir(parents=True, exist_ok=True)
    kb_builds.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(results_dir / "records.jsonl", kb_records)
    job_summary = summary["job_summary"]
    if queue_seconds is None:
        job_started = float(job_summary.get("job_started_epoch", 0.0))
        queue_seconds = round(max(0.0, job_started - summary["submitted_epoch"]), 3)
    else:
        queue_seconds = round(float(queue_seconds), 3)
    if revalidated:
        wall_seconds = job_summary.get("total_seconds")
    else:
        wall_seconds = round(time.time() - summary["submitted_epoch"], 3)
    record = {
        "schema": "vt-kb-build/1",
        "build_id": build["build_id"],
        "job_id": summary["job_id"],
        "request": build["request"],
        "upload_mode": summary["upload_mode"],
        "revalidated": revalidated,
        "job_summary": job_summary,
        "queue_seconds": queue_seconds,
        "wall_seconds": wall_seconds,
        "validation": validation,
        "remote": {
            "request_dir": f"{build['userdir']}/{REQUEST_UPLOAD_DIR}/{build['build_id']}",
            "result_dir": f"{build['userdir']}/{RESULT_UPLOAD_DIR}/{build['build_id']}",
            "log": f"slurm_log/{build['job_name']}-{summary['job_id']}.log",
        },
        "local": {
            "records": str(kb_records),
            "task_dir": str(build["task_dir"]),
            "downloads": str(results_dir),
        },
    }
    write_json(kb_builds, record)
    return record


def load_existing_build(build_id: str, config: dict) -> dict:
    """Load a prepared build from the local cache for revalidation."""

    local_root = REPO_ROOT / "data" / "caches" / "kb-requests" / build_id
    if not local_root.is_dir():
        raise SystemExit(f"no prepared build at {local_root}")
    request_path = local_root / "request.json"
    input_path = local_root / "input.jsonl"
    if not request_path.is_file() or not input_path.is_file():
        raise SystemExit(f"incomplete build directory: {local_root}")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    chunks = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    userdir = str(request["input_path"]).split("/kb/requests/")[0]
    return {
        "build_id": build_id,
        "request": request,
        "chunks": chunks,
        "local_root": local_root,
        "request_path": request_path,
        "input_path": input_path,
        "task_dir": local_root / "task",
        "userdir": userdir,
        "job_name": config["job"]["name"],
    }


def finalize_build(
    build: dict,
    results_dir: Path,
    job_summary: dict,
    *,
    submitted_epoch: float,
    upload_mode: str,
    upload: dict,
    revalidated: bool = False,
    queue_seconds: float | None = None,
) -> tuple[dict, dict, dict]:
    """Validate one downloaded result set, store it, and build the report."""

    validation = validate_build(build, results_dir, job_summary)
    summary = {
        "job_id": job_summary.get("job_id", ""),
        "submitted_epoch": submitted_epoch,
        "upload_mode": upload_mode,
        "upload": upload,
        "revalidated": revalidated,
        "queue_seconds": queue_seconds,
        "job_summary": job_summary,
    }
    build_record = store_build(
        build,
        results_dir,
        summary,
        validation,
        revalidated=revalidated,
        queue_seconds=queue_seconds,
    )
    output = {
        "ok": validation["pass"],
        "build_id": build["build_id"],
        "job_id": summary["job_id"],
        "upload_mode": upload_mode,
        "revalidated": revalidated,
        "launcher": job_summary.get("launcher"),
        "chunks": validation["chunks"],
        "records_valid": validation["records_valid"],
        "invalid_records": validation["invalid_records"],
        "progress_status": validation["progress"].get("status"),
        "timings": {
            "queue_seconds": build_record["queue_seconds"],
            "vllm_startup_seconds": job_summary.get("vllm_startup_seconds"),
            "build_seconds": job_summary.get("build_seconds"),
            "total_seconds": job_summary.get("total_seconds"),
            "wall_seconds": build_record["wall_seconds"],
        },
        "artifact_hashes": validation["artifact_hashes"],
        "records_path": build_record["local"]["records"],
        "build_summary_path": str(
            REPO_ROOT / "data" / "kb" / "builds" / f"{build['build_id']}.json"
        ),
        "job_log": str(build["local_root"] / f"job-{summary['job_id']}.log"),
    }
    return output, validation, build_record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", default=None, help="page-record JSONL from an OCR parse")
    parser.add_argument("--max-chunks", type=int, default=8)
    parser.add_argument("--doc-id", default=None)
    parser.add_argument("--build-id", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="revalidate downloaded artifacts without touching TACC",
    )
    parser.add_argument(
        "--upload-mode",
        default="userdir_root",
        help="upload mode recorded by --validate-only",
    )
    parser.add_argument(
        "--queue-seconds",
        type=float,
        default=None,
        help="queue time recorded by --validate-only",
    )
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--poll-seconds", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    if args.upload_mode not in ("userdir_root", "task_dir_relocated"):
        raise SystemExit("--upload-mode must be userdir_root or task_dir_relocated")

    if args.validate_only:
        if not args.build_id:
            raise SystemExit("--validate-only needs --build-id")
        build = load_existing_build(args.build_id, config)
        results_dir = REPO_ROOT / "data" / "caches" / "kb-results" / args.build_id
        job_summary = load_json(results_dir / "summary.json")
        job_started = float(job_summary.get("job_started_epoch") or 0.0)
        queue_seconds = args.queue_seconds
        if queue_seconds is None:
            queue_seconds = 2.0
        output, validation, _record = finalize_build(
            build,
            results_dir,
            job_summary,
            submitted_epoch=job_started - queue_seconds,
            upload_mode=args.upload_mode,
            upload={"mode": args.upload_mode, "remote_names": {}},
            revalidated=True,
            queue_seconds=queue_seconds,
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if not validation["pass"]:
            log("[kb] validation did not pass")
            return 1
        log(
            f"[kb] spike pass (revalidated): {validation['records_valid']}/"
            f"{validation['chunks']} records valid, job {output['job_id']}"
        )
        return 0

    if not args.pages:
        raise SystemExit("--pages is required unless --validate-only is used")
    if args.timeout is None:
        args.timeout = int(config["build"]["queue_timeout_s"])
    if args.poll_seconds is None:
        args.poll_seconds = int(config["build"]["poll_interval_s"])
    if args.max_chunks <= 0 or args.max_chunks > int(config["build"]["max_chunks_per_job"]):
        raise SystemExit(
            f"--max-chunks must be between 1 and {config['build']['max_chunks_per_job']}"
        )
    if not shutil.which("tcloud"):
        raise SystemExit("tcloud is not on PATH")
    for config_file in ("userconfig", "clusterconfig"):
        if not (Path.home() / ".tcloud" / f".{config_file}").is_file():
            raise SystemExit(f"~/.tcloud/.{config_file} is missing; run tcloud config first")

    build = prepare_build(args, config)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "build_id": build["build_id"],
                    "task_dir": str(build["task_dir"]),
                    "request": build["request"],
                    "chunks": build["chunks"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    upload = upload_request(build)
    upload_mode = upload["mode"]
    submission = submit_job(build)
    job_id = submission["job_id"]
    try:
        poll_job(job_id, timeout_s=args.timeout, poll_s=args.poll_seconds)
    finally:
        log_file = fetch_log(build, job_id)
        if log_file.is_file():
            log(f"[kb] job log: {log_file}")
    results_dir = download_results(build)
    job_summary = load_json(results_dir / "summary.json")
    output, validation, _record = finalize_build(
        build,
        results_dir,
        job_summary,
        submitted_epoch=submission["submitted_epoch"],
        upload_mode=upload_mode,
        upload=upload,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not validation["pass"]:
        log("[kb] validation did not pass; inspected artifacts were kept locally")
        return 1
    log(
        f"[kb] spike pass: {validation['records_valid']}/{validation['chunks']} records "
        f"valid, job {output['job_id']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
