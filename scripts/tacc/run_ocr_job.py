#!/usr/bin/env python3
"""Local driver for the TACC batched OCR job.

Round trip: choose the documents of one corpus batch, write the
``vt-ocr-request/1`` manifest into a generated task directory, stage the shared
helpers, upload the batch PDFs to the ``USERDIR`` root, submit the ``tacc/ocr``
job, poll it, download the per-document page records, the document markdown, the
per-document logs, the job summary and one ``images.tar.gz``, then mirror the
pages and page images under ``data/corpus/``.

The job caps recognition at 1800 s and its whole body at 3300 s, so it records
which documents it finished; a resumed run submits only the rest.

Usage:
  .venv/bin/python scripts/tacc/run_ocr_job.py --batch lectures
  .venv/bin/python scripts/tacc/run_ocr_job.py --batch lectures --dry-run
  .venv/bin/python scripts/tacc/run_ocr_job.py --batch tutorials --resume
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import yaml  # noqa: E402

JOB_TEMPLATE = REPO_ROOT / "tacc" / "ocr"
SUBMIT_HELPER = REPO_ROOT / "scripts" / "tacc" / "submit.sh"
CONFIG_PATH = REPO_ROOT / "config" / "knowledge.yaml"
PDF_ROOT = REPO_ROOT / "data" / "corpus" / "corpus-pdf"
TCLOUD = shutil.which("tcloud") or (
    str(Path.home() / ".local" / "bin" / "tcloud")
    if (Path.home() / ".local" / "bin" / "tcloud").is_file()
    else "tcloud"
)
FINISHED_STATES = {"CD", "CA", "F", "TO", "NF", "OOM", "BF", "PR"}
REQUEST_SCHEMA = "vt-ocr-request/1"
SUMMARY_SCHEMA = "vt-ocr-batch/1"
MANIFEST_SCHEMA = "vt-ocr-manifest/1"
JOB_FILES = ("job.sh", "ocr_batch.py", "tuxiv.conf")
PAGES_STORE = REPO_ROOT / "data" / "corpus" / "pages"
IMAGES_STORE = REPO_ROOT / "data" / "corpus" / "images"
DOCUMENT_STORE = REPO_ROOT / "data" / "corpus" / "ocr"

#: The parsed course corpus, in three jobs. PDFs come from
#: ``data/corpus/corpus-pdf`` (or the ``--pdf-root`` override); the page counts
#: are the ones the course PDFs actually have, and the job records them again
#: from the render manifest.
BATCHES: dict[str, list[dict]] = {
    "lectures": [
        {"doc_id": "ACS_Lecture_0_2026F", "pdf": "ACS_Lecture_0_2026F.pdf", "expected_pages": 11},
        {"doc_id": "ACS_Lecture_1_2026F", "pdf": "ACS_Lecture_1_2026F.pdf", "expected_pages": 67},
        {"doc_id": "ACS_lecture_2_2026F", "pdf": "ACS_lecture_2_2026F.pdf", "expected_pages": 69},
    ],
    "tutorials": [
        {"doc_id": "Tutorial_1", "pdf": "Tutorial_1.pdf", "expected_pages": 16},
        {"doc_id": "Tutorial_2", "pdf": "Tutorial_2.pdf", "expected_pages": 25},
        {"doc_id": "Tutorial_3", "pdf": "Tutorial_3.pdf", "expected_pages": 28},
        {"doc_id": "Tutorial_4", "pdf": "Tutorial_4.pdf", "expected_pages": 40},
        {"doc_id": "Tutorial_5", "pdf": "Tutorial_5.pdf", "expected_pages": 33},
        {"doc_id": "Tutorial_6", "pdf": "Tutorial_6.pdf", "expected_pages": 23},
        {"doc_id": "TACC_Toturial", "pdf": "TACC_Toturial.pdf", "expected_pages": 34},
    ],
    "misc": [
        {"doc_id": "Assignment_1_final", "pdf": "Assignment_1_final.pdf", "expected_pages": 6},
        {"doc_id": "Assignment_2", "pdf": "Assignment_2.pdf", "expected_pages": 5},
    ],
}

#: Parsed by the week-one demo job 27884; ingestion copies its page records
#: instead of parsing the file again (see docs/tacc-notes.md).
ALREADY_PARSED = {
    "course_project": {
        "pages": 8,
        "pdf": "course_project.pdf",
        "pages_path": REPO_ROOT / "data" / "corpus" / "pdf-parse" / "pages-27884.jsonl",
    }
}


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------- request
def batch_documents(batch: str) -> list[dict]:
    """Return the document specifications of one batch."""

    if batch not in BATCHES:
        raise SystemExit(f"unknown batch {batch!r}; choose from {sorted(BATCHES)}")
    return [dict(document) for document in BATCHES[batch]]


def documents_to_ocr(
    documents: list[dict], state: dict, *, resume: bool, force: bool
) -> list[dict]:
    """Choose the documents a job still has to parse."""

    if force or not resume:
        return list(documents)
    remaining: list[dict] = []
    for document in documents:
        record = state.get(document["doc_id"]) or {}
        status = (record.get("ocr") or {}).get("status")
        if status == "done":
            log(f"[ocr] {document['doc_id']} already parsed; skipping")
            continue
        remaining.append(document)
    return remaining


def build_ocr_request(
    *,
    batch_id: str,
    batch: str,
    documents: list[dict],
    userdir: str,
    dpi: int = 200,
    ocr_stage_seconds: int = 1800,
    body_deadline_seconds: int = 3300,
) -> dict:
    """Return the manifest object the ``tacc/ocr`` job reads."""

    if not documents:
        raise ValueError("an OCR request needs at least one document")
    userdir = userdir.rstrip("/")
    return {
        "schema": REQUEST_SCHEMA,
        "batch_id": batch_id,
        "batch": batch,
        "documents": [
            {
                "doc_id": str(document["doc_id"]),
                "pdf": str(document["pdf"]),
                "expected_pages": int(document.get("expected_pages") or 0),
            }
            for document in documents
        ],
        "pdf_dir": f"{userdir}/corpus-pdf",
        "out_dir": f"{userdir}/ocr/{batch_id}",
        "dpi": int(dpi),
        "ocr_stage_seconds": int(ocr_stage_seconds),
        "body_deadline_seconds": int(body_deadline_seconds),
        "created_at": now_iso(),
    }


def prepare_job(
    *,
    batch: str,
    batch_id: str,
    documents: list[dict],
    userdir: str,
    config: dict,
    force: bool = False,
    pdf_root: Path | None = None,
) -> dict:
    """Write the local request and task directory. No TACC access."""

    ocr_config = config["jobs"]["ocr"]
    local_root = REPO_ROOT / "data" / "caches" / "ocr-requests" / batch_id
    if local_root.exists() and not force:
        raise SystemExit(
            f"{local_root} already exists; pass --batch-id or --force to replace it"
        )
    request = build_ocr_request(
        batch_id=batch_id,
        batch=batch,
        documents=documents,
        userdir=userdir,
        dpi=int(ocr_config.get("dpi", 200)),
        ocr_stage_seconds=int(ocr_config.get("ocr_stage_seconds", 1800)),
        body_deadline_seconds=int(ocr_config.get("body_deadline_seconds", 3300)),
    )
    task_dir = local_root / "task"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name in JOB_FILES:
        shutil.copyfile(JOB_TEMPLATE / name, task_dir / name)
    return {
        "batch": batch,
        "batch_id": batch_id,
        "request": request,
        "documents": documents,
        "local_root": local_root,
        "task_dir": task_dir,
        "userdir": userdir,
        "job_name": ocr_config.get("name", "vt-ocr"),
        "pdf_root": Path(pdf_root or PDF_ROOT),
    }


def upload_pdfs(job: dict) -> dict:
    """Upload the batch PDFs to the USERDIR root; the job finds either copy."""

    uploaded: list[str] = []
    missing: list[str] = []
    for document in job["documents"]:
        source = job["pdf_root"] / document["pdf"]
        if not source.is_file():
            missing.append(str(source))
            continue
        text = ""
        for attempt in range(1, 4):
            try:
                result = run([TCLOUD, "upload", str(source), "."], timeout=900)
            except subprocess.TimeoutExpired as exc:
                text = f"timeout: {exc}"
            else:
                text = result.stdout + result.stderr
                if result.returncode == 0 and "[Tcloud Error]" not in text and "Failed to" not in text:
                    uploaded.append(document["pdf"])
                    break
            log(f"[ocr] upload attempt {attempt} failed for {source.name}; retrying")
            time.sleep(10 * attempt)
        else:
            raise SystemExit(f"upload failed for {source}:\n{text}")
    if missing:
        log(f"[ocr] pdfs not in {job['pdf_root']}: {', '.join(missing)}")
    log(f"[ocr] uploaded {len(uploaded)} pdf(s) to {job['userdir']}/")
    return {"uploaded": uploaded, "missing": missing}


# -------------------------------------------------------------------- TACC run
def submit_job(job: dict) -> dict:
    staging = run(
        ["bash", str(SUBMIT_HELPER), str(job["task_dir"]), "--no-submit"], timeout=120
    )
    if staging.returncode != 0:
        raise SystemExit(f"staging failed:\n{staging.stdout}\n{staging.stderr}")
    preflight_task_dir(job["task_dir"])
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
        log(f"[ocr] submit attempt {attempt} failed; retrying in {15 * attempt}s")
        time.sleep(15 * attempt)
    if not match:
        raise SystemExit(f"submit failed:\n{submit_text}")
    job_id = match.group(1)
    log(f"[ocr] submitted job {job_id} (batch {job['batch_id']})")
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
            log(f"[ocr] job {job_id}: status query failed; retrying")
            time.sleep(poll_s)
            continue
        row = [
            line
            for line in status_text.splitlines()
            if line.strip().startswith(job_id)
        ]
        if not row:
            log(f"[ocr] job {job_id} left the queue")
            return
        fields = row[0].split()
        state = fields[4] if len(fields) > 4 else ""
        log(f"[ocr] job {job_id} state={state} elapsed={int(time.time() - started)}s")
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


def extract_artifacts(archive: Path, target: Path) -> list[Path]:
    """Extract the job's pages/document/logs archive into ``target``."""

    extracted: list[Path] = []
    target = Path(target)
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            name = member.name
            if not member.isfile() or name.startswith("/") or ".." in Path(name).parts:
                continue
            if not name.startswith(("pages/", "document/", "logs/")):
                continue
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(member)
            if source is None:
                continue
            destination.write_bytes(source.read())
            extracted.append(destination)
    return extracted


def download_results(job: dict, job_id: str) -> dict:
    """Download the batch artifacts and per-document outputs."""

    local_dir = REPO_ROOT / "data" / "caches" / "ocr-results" / job["batch_id"]
    local_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = f"ocr/{job['batch_id']}"
    downloaded: dict[str, str] = {}
    for name in ("summary.json", "manifest.json", "images.tar.gz"):
        if download_artifact(f"{remote_dir}/{name}", local_dir / name):
            downloaded[name] = str(local_dir / name)
    if download_artifact(f"{remote_dir}/artifacts.tar.gz", local_dir / "artifacts.tar.gz"):
        for path in extract_artifacts(local_dir / "artifacts.tar.gz", local_dir):
            downloaded[str(path.relative_to(local_dir))] = str(path)
        return {"directory": local_dir, "downloaded": downloaded}
    # Older jobs wrote no archive; fall back to one download per file.
    for document in job["documents"]:
        doc_id = document["doc_id"]
        pages_target = local_dir / "pages" / f"{doc_id}.jsonl"
        if download_artifact(f"{remote_dir}/pages/{doc_id}.jsonl", pages_target):
            downloaded[f"pages/{doc_id}.jsonl"] = str(pages_target)
        md_target = local_dir / "document" / f"{doc_id}-ocr.md"
        if download_artifact(f"{remote_dir}/document/{doc_id}-ocr.md", md_target):
            downloaded[f"document/{doc_id}-ocr.md"] = str(md_target)
        log_target = local_dir / "logs" / f"{doc_id}-{job_id}.log"
        if download_artifact(f"{remote_dir}/logs/{doc_id}-{job_id}.log", log_target):
            downloaded[f"logs/{doc_id}-{job_id}.log"] = str(log_target)
    return {"directory": local_dir, "downloaded": downloaded}


# ------------------------------------------------------------------- artifacts
JOB_HERE_TEMPLATE = re.compile(r"\$HERE/([A-Za-z0-9_./-]+)")
JOB_STAGED_TEMPLATE = re.compile(r"(?<![/A-Za-z0-9_.-])_staged/([A-Za-z0-9_.-]+)")
JOB_ALWAYS_REQUIRED = ("job.sh", "ocr_batch.py", "tuxiv.conf", "request.json")
#: The shared stage helpers ``ocr_batch.py`` runs; ``submit.sh`` stages them.
STAGED_HELPERS = (
    "_staged/bootstrap.sh",
    "_staged/requirements.txt",
    "_staged/enumerate_pages.py",
    "_staged/render_pages.py",
    "_staged/ocr_pages.py",
    "_staged/assemble_document.py",
)


def required_task_files(task_dir: Path) -> list[str]:
    """Return every file the job script names, plus the job's own files."""

    task_dir = Path(task_dir)
    required = set(JOB_ALWAYS_REQUIRED) | set(STAGED_HELPERS)
    job_sh = task_dir / "job.sh"
    if job_sh.is_file():
        text = job_sh.read_text(encoding="utf-8")
        for match in JOB_HERE_TEMPLATE.finditer(text):
            required.add(match.group(1))
        for match in JOB_STAGED_TEMPLATE.finditer(text):
            required.add(f"_staged/{match.group(1)}")
    # ``$HERE/.`` and ``$HERE/_staged`` name directories, not files.
    required = {
        name
        for name in required
        if name in JOB_ALWAYS_REQUIRED or Path(name).suffix
    }
    return sorted(required)


def preflight_task_dir(task_dir: Path) -> list[str]:
    """Assert every script the job will run exists in the staged task tree."""

    task_dir = Path(task_dir)
    required = required_task_files(task_dir)
    missing = [name for name in required if not (task_dir / name).is_file()]
    if missing:
        raise SystemExit(
            f"task directory {task_dir} is missing {', '.join(missing)};"
            " run scripts/tacc/submit.sh --no-submit first"
        )
    return [str(task_dir / name) for name in required]


def parse_job_summary(summary: dict) -> dict[str, dict]:
    """Map document id to the job's record for it."""

    if not isinstance(summary, dict):
        raise ValueError("job summary must be a JSON object")
    if summary.get("schema") not in (None, SUMMARY_SCHEMA, MANIFEST_SCHEMA):
        raise ValueError(
            f"job summary schema must be {SUMMARY_SCHEMA} or {MANIFEST_SCHEMA}"
        )
    records: dict[str, dict] = {}
    for record in summary.get("documents") or []:
        doc_id = str(record.get("doc_id") or "")
        if not doc_id:
            continue
        records[doc_id] = record
    return records


def extract_page_images(archive: Path, target: Path) -> list[Path]:
    """Extract ``images/<doc>.pNNN.webp`` from the archive into ``target``."""

    target.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            if not member.isfile() or not member.name.endswith(".webp"):
                continue
            name = Path(member.name).name
            destination = target / name
            source = handle.extractfile(member)
            if source is None:
                continue
            destination.write_bytes(source.read())
            extracted.append(destination)
    return extracted


def store_artifacts(
    job: dict, results: dict, documents: dict[str, dict]
) -> dict[str, dict]:
    """Mirror the pages, document markdown and images under ``data/corpus``."""

    PAGES_STORE.mkdir(parents=True, exist_ok=True)
    DOCUMENT_STORE.mkdir(parents=True, exist_ok=True)
    stored: dict[str, dict] = {}
    for document in job["documents"]:
        doc_id = document["doc_id"]
        record = {"pages_path": None, "document_md": None, "log_path": None}
        job_record = documents.get(doc_id) or {}
        pages_source = results["directory"] / "pages" / f"{doc_id}.jsonl"
        if pages_source.is_file():
            target = PAGES_STORE / f"{doc_id}.jsonl"
            shutil.copyfile(pages_source, target)
            record["pages_path"] = str(target)
        md_source = results["directory"] / "document" / f"{doc_id}-ocr.md"
        if md_source.is_file():
            target = DOCUMENT_STORE / f"{doc_id}-ocr.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(md_source, target)
            record["document_md"] = str(target)
        log_source = results["directory"] / "logs" / f"{doc_id}-{job['job_id']}.log"
        if log_source.is_file():
            record["log_path"] = str(log_source)
        elif job_record.get("log_path"):
            record["log_path"] = (
                f"{job['userdir']}/ocr/{job['batch_id']}/{job_record['log_path']}"
            )
        stored[doc_id] = record
    archive = results["directory"] / "images.tar.gz"
    images = extract_page_images(archive, IMAGES_STORE) if archive.is_file() else []
    return {"documents": stored, "images": [str(path) for path in images]}


def finalize_job(
    job: dict, results: dict, *, submission: dict, job_log: Path
) -> dict:
    """Read the job summary, store the artifacts and build the report."""

    summary_path = results["directory"] / "summary.json"
    manifest_path = results["directory"] / "manifest.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    elif manifest_path.is_file():
        # A job that stopped at the hour cap writes only the incremental
        # manifest; the finished documents stay recorded and resumable.
        summary = json.loads(manifest_path.read_text(encoding="utf-8"))
        log(
            f"[ocr] job {submission['job_id']} wrote no summary.json; "
            f"reading the partial manifest"
        )
    else:
        raise SystemExit(
            f"job {submission['job_id']} wrote no summary.json; see {job_log}"
        )
    job_documents = parse_job_summary(summary)
    stored = store_artifacts(job, results, job_documents)

    documents: dict[str, dict] = {}
    for document in job["documents"]:
        doc_id = document["doc_id"]
        record = dict(job_documents.get(doc_id) or {})
        record.setdefault("status", "missing")
        record["expected_pages"] = int(document.get("expected_pages") or 0)
        record["pages_path"] = stored["documents"][doc_id]["pages_path"]
        record["document_md"] = stored["documents"][doc_id]["document_md"]
        record["log_path"] = stored["documents"][doc_id]["log_path"]
        documents[doc_id] = record

    done = [record for record in documents.values() if record["status"] == "done"]
    job_started = float(summary.get("job_started_epoch") or submission["submitted_epoch"])
    return {
        "ok": len(done) == len(documents) and bool(documents),
        "batch": job["batch"],
        "batch_id": job["batch_id"],
        "job_id": submission["job_id"],
        "upload_mode": "userdir_root",
        "documents": documents,
        "totals": {
            "documents": len(documents),
            "done": len(done),
            "skipped": sum(
                1 for record in documents.values() if record["status"] == "skipped"
            ),
            "failed": sum(
                1 for record in documents.values() if record["status"] == "failed"
            ),
            "pages": sum(int(record.get("pages") or 0) for record in documents.values()),
            "pages_ok": sum(
                int(record.get("pages_ok") or 0) for record in documents.values()
            ),
            "blocks": sum(
                int(record.get("blocks") or 0) for record in documents.values()
            ),
            "chars": sum(int(record.get("chars") or 0) for record in documents.values()),
        },
        "timings": {
            "vllm_startup_seconds": summary.get("vllm_startup_seconds"),
            "elapsed_seconds": summary.get("elapsed_seconds"),
            "queue_seconds": round(
                max(0.0, job_started - submission["submitted_epoch"]), 3
            ),
            "wall_seconds": round(
                max(0.0, time.time() - submission["submitted_epoch"]), 3
            ),
        },
        "images": len(stored["images"]),
        "summary_path": str(summary_path),
        "job_log": str(job_log),
        "results_dir": str(results["directory"]),
        "request_path": str(job["local_root"] / "task" / "request.json"),
        "task_dir": str(job["task_dir"]),
    }


def load_prepared_job(batch_id: str) -> dict:
    """Load the staged request of a batch that was already submitted."""

    config = load_config()
    local_root = REPO_ROOT / "data" / "caches" / "ocr-requests" / batch_id
    task_dir = local_root / "task"
    request_path = task_dir / "request.json"
    if not request_path.is_file():
        raise SystemExit(f"no prepared batch at {request_path}")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    return {
        "batch": request.get("batch", ""),
        "batch_id": batch_id,
        "request": request,
        "documents": request.get("documents") or [],
        "local_root": local_root,
        "task_dir": task_dir,
        "userdir": str(request["out_dir"]).split("/ocr/")[0],
        "job_name": (config.get("jobs", {}).get("ocr") or {}).get("name", "vt-ocr"),
    }


def finish_batch(batch_id: str, job_id: str | None = None) -> dict:
    """Finish a submitted batch whose job already left the queue.

    Used when the job completed but the local download failed (gateway timeout)
    or the driver process died: the GPU work is not repeated, only the artifact
    transfer.
    """

    job = load_prepared_job(batch_id)
    results_dir = REPO_ROOT / "data" / "caches" / "ocr-results" / batch_id
    job_id = str(job_id or "")
    if not job_id:
        for name in ("summary.json", "manifest.json"):
            path = results_dir / name
            if path.is_file():
                job_id = str(
                    json.loads(path.read_text(encoding="utf-8")).get("job_id") or ""
                )
                if job_id:
                    break
    if not job_id:
        raise SystemExit(
            f"no job id recorded for batch {batch_id}; cannot finish without resubmitting"
        )
    job["job_id"] = job_id
    job_log = fetch_log(job, job_id)
    results = download_results(job, job_id)
    return finalize_job(
        job,
        results,
        submission={"job_id": job_id, "submitted_epoch": time.time()},
        job_log=job_log,
    )


def run_batch(
    *,
    batch: str,
    state: dict,
    resume: bool = False,
    force: bool = False,
    only: list[str] | None = None,
    batch_id: str | None = None,
    pdf_root: Path | None = None,
    dry_run: bool = False,
    timeout_s: int | None = None,
    poll_s: int | None = None,
) -> dict:
    """Run one batch end to end and return the report the ingest CLI stores."""

    config = load_config()
    documents = batch_documents(batch)
    if only:
        documents = [
            document for document in documents if document["doc_id"] in only
        ]
    documents = documents_to_ocr(documents, state, resume=resume, force=force)
    if not documents:
        return {
            "ok": True,
            "batch": batch,
            "batch_id": batch_id or "",
            "job_id": "",
            "documents": {},
            "skipped_batch": True,
            "totals": {"documents": 0},
        }
    batch_id = batch_id or datetime.now(timezone.utc).strftime(
        f"ocr-{batch}-%Y%m%d-%H%M%S"
    )
    userdir = tacc_paths()
    job = prepare_job(
        batch=batch,
        batch_id=batch_id,
        documents=documents,
        userdir=userdir,
        config=config,
        force=force,
        pdf_root=pdf_root,
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "batch": batch,
            "batch_id": batch_id,
            "task_dir": str(job["task_dir"]),
            "request": job["request"],
            "documents": [
                {"doc_id": document["doc_id"], "pdf": document["pdf"]}
                for document in documents
            ],
        }
    upload = upload_pdfs(job)
    job["upload"] = upload
    submission = submit_job(job)
    job["job_id"] = submission["job_id"]
    if timeout_s is None:
        timeout_s = int(config["jobs"]["ocr"].get("queue_timeout_s", 3600))
    if poll_s is None:
        poll_s = int(config["jobs"]["ocr"].get("poll_interval_s", 30))
    try:
        poll_job(submission["job_id"], timeout_s=timeout_s, poll_s=poll_s)
    finally:
        job_log = fetch_log(job, submission["job_id"])
        log(f"[ocr] job log: {job_log}")
    results = download_results(job, submission["job_id"])
    return finalize_job(job, results, submission=submission, job_log=job_log)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, choices=sorted(BATCHES))
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--pdf-root", default=None, help="directory holding the corpus PDFs")
    parser.add_argument("--resume", action="store_true", help="skip documents already done")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--state", default=None, help="ingest state JSON to resume from")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--poll-seconds", type=int, default=None)
    args = parser.parse_args(argv)

    state: dict = {}
    if args.state:
        state = json.loads(Path(args.state).read_text(encoding="utf-8")).get(
            "documents", {}
        )
    if not args.dry_run and not shutil.which("tcloud") and not Path(TCLOUD).is_file():
        raise SystemExit(f"tcloud is not on PATH and {TCLOUD} does not exist")
    report = run_batch(
        batch=args.batch,
        state=state,
        resume=args.resume,
        force=args.force,
        batch_id=args.batch_id,
        pdf_root=Path(args.pdf_root) if args.pdf_root else None,
        dry_run=args.dry_run,
        timeout_s=args.timeout,
        poll_s=args.poll_seconds,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
