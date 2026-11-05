#!/usr/bin/env python3
"""Local driver for the TACC BGE-M3 embedding-index job.

Round trip: collect the chunks to embed, write the ``vt-index-request/1``
manifest and an input JSONL, stage the ``tacc/index`` task directory, upload the
input to the ``USERDIR`` root, submit the GPU job, poll it, download
``vectors.npy``, ``row_map.jsonl`` and ``summary.json``, validate that every
chunk got exactly one vector, and store the vectors in the local knowledge store
(``kb_chunks.embedding``, the one owner per ADR-0015).

The job reads the BGE-M3 weights from ``$HOME/models/bge-m3`` on TACC and
downloads them through the Hugging Face mirror when they are missing; this
laptop never downloads model weights.

Usage:
  .venv/bin/python scripts/tacc/run_index_job.py --input data/index/index-input.jsonl
  .venv/bin/python scripts/tacc/run_index_job.py --input data/index/index-input.jsonl --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import yaml  # noqa: E402

JOB_TEMPLATE = REPO_ROOT / "tacc" / "index"
SUBMIT_HELPER = REPO_ROOT / "scripts" / "tacc" / "submit.sh"
CONFIG_PATH = REPO_ROOT / "config" / "knowledge.yaml"
INDEX_STORE = REPO_ROOT / "data" / "index"
TCLOUD = shutil.which("tcloud") or (
    str(Path.home() / ".local" / "bin" / "tcloud")
    if (Path.home() / ".local" / "bin" / "tcloud").is_file()
    else "tcloud"
)
FINISHED_STATES = {"CD", "CA", "F", "TO", "NF", "OOM", "BF", "PR"}
INDEX_REQUEST_SCHEMA = "vt-index-request/1"
INDEX_SUMMARY_SCHEMA = "vt-index-summary/1"
INPUT_DIR = "index/requests"
RESULT_DIR = "index/results"
JOB_FILES = ("job.sh", "index_worker.py", "tuxiv.conf")
NPY_MAGIC = b"\x93NUMPY"


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


def canonical_line(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def corpus_hash(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(canonical_line(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_rows(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("an index request needs at least one chunk")
    seen: set[str] = set()
    for row in rows:
        chunk_id = str(row.get("chunk_id") or "")
        if not chunk_id:
            raise ValueError("every index input row needs a chunk_id")
        if chunk_id in seen:
            raise ValueError(f"duplicate chunk id in the index input: {chunk_id}")
        seen.add(chunk_id)
        if not str(row.get("doc_id") or ""):
            raise ValueError(f"chunk {chunk_id} has no doc_id")
        if not str(row.get("text") or "").strip():
            raise ValueError(f"chunk {chunk_id} has no text")


def build_index_request(
    *,
    batch_id: str,
    rows: list[dict],
    userdir: str,
    model_config: dict,
    created_at: str | None = None,
) -> dict:
    """Return the ``vt-index-request/1`` manifest the job reads."""

    _validate_rows(rows)
    userdir = userdir.rstrip("/")
    return {
        "schema": INDEX_REQUEST_SCHEMA,
        "batch_id": batch_id,
        "input_path": f"{userdir}/{INPUT_DIR}/{batch_id}/input.jsonl",
        "out_dir": f"{userdir}/{RESULT_DIR}/{batch_id}",
        "model": str(model_config.get("model", "BAAI/bge-m3")),
        "model_path": str(model_config.get("model_path", "~/models/bge-m3")),
        "dimension": int(model_config.get("dimension", 1024)),
        "batch_size": int(model_config.get("batch_size", 16)),
        "max_length": int(model_config.get("max_length", 512)),
        "device": str(model_config.get("device", "cuda")),
        "chunks": len(rows),
        "corpus_hash": corpus_hash(rows),
        "created_at": created_at or now_iso(),
    }


def index_input_upload_name(batch_id: str) -> str:
    """Return the USERDIR root filename the driver uploads and the worker moves."""

    return f"{batch_id}-index-input.jsonl"


def write_index_input(rows: list[dict], path: Path) -> None:
    """Write the input JSONL the job embeds."""

    _validate_rows(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_line(row) + "\n")


def read_index_input(path: Path) -> list[dict]:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    _validate_rows(rows)
    return rows


def read_npy(path: Path) -> dict:
    """Read a C-order float32 ``.npy`` matrix without NumPy."""

    raw = Path(path).read_bytes()
    if not raw.startswith(NPY_MAGIC):
        raise ValueError(f"{path} is not a .npy file")
    major = raw[6]
    if major == 1:
        header_length = struct.unpack("<H", raw[8:10])[0]
        header_start = 10
    elif major in (2, 3):
        header_length = struct.unpack("<I", raw[8:12])[0]
        header_start = 12
    else:
        raise ValueError(f"{path} has an unsupported .npy version {major}")
    header_text = raw[header_start : header_start + header_length].decode("latin1")
    header = _parse_npy_header(header_text)
    if header["descr"] not in ("<f4", "=f4", "|f4"):
        raise ValueError(f"{path} is not a float32 matrix: {header['descr']}")
    if header["fortran_order"]:
        raise ValueError(f"{path} is Fortran ordered; the job writes C order")
    if len(header["shape"]) != 2:
        raise ValueError(f"{path} is not a matrix: shape {header['shape']}")
    rows, dimension = header["shape"]
    body = raw[header_start + header_length :]
    row_bytes = dimension * 4
    if len(body) != rows * row_bytes:
        raise ValueError(
            f"{path} holds {len(body)} bytes, expected {rows * row_bytes}"
        )
    return {
        "rows": rows,
        "dimension": dimension,
        "dtype": "float32",
        "vectors": [body[index * row_bytes : (index + 1) * row_bytes] for index in range(rows)],
    }


def _parse_npy_header(text: str) -> dict:
    """Parse the ``{'descr': ..., 'fortran_order': ..., 'shape': ...}`` dict."""

    result: dict = {}
    descr = re.search(r"'descr'\s*:\s*'([^']+)'", text)
    order = re.search(r"'fortran_order'\s*:\s*(True|False)", text)
    shape = re.search(r"'shape'\s*:\s*\(([^)]*)\)", text)
    if not descr or not order or not shape:
        raise ValueError("unreadable .npy header")
    result["descr"] = descr.group(1)
    result["fortran_order"] = order.group(1) == "True"
    dims = [part.strip() for part in shape.group(1).split(",") if part.strip()]
    result["shape"] = tuple(int(part) for part in dims)
    return result


def validate_index_result(rows: list[dict], row_map: list[dict], matrix: dict) -> list[str]:
    """Return the contract violations of one index result (empty is valid)."""

    issues: list[str] = []
    input_ids = [str(row["chunk_id"]) for row in rows]
    if len(row_map) != len(rows):
        issues.append(f"row map has {len(row_map)} rows, the input has {len(rows)}")
    if matrix["rows"] != len(row_map):
        issues.append(
            f"vectors.npy has {matrix['rows']} rows, the row map has {len(row_map)}"
        )
    seen: set[str] = set()
    for index, entry in enumerate(row_map):
        chunk_id = str(entry.get("chunk_id") or "")
        if chunk_id not in input_ids:
            issues.append(f"row map row {index} names chunk {chunk_id!r} that was not in the input")
        if chunk_id in seen:
            issues.append(f"row map repeats chunk {chunk_id}")
        seen.add(chunk_id)
        row = entry.get("row")
        if not isinstance(row, int) or isinstance(row, bool) or row != index:
            issues.append(f"row map row {index} has row index {row!r}")
        vector = matrix["vectors"][index] if index < len(matrix["vectors"]) else b""
        if len(vector) != matrix["dimension"] * 4:
            issues.append(
                f"row map row {index} points at a vector of {len(vector)} bytes"
            )
    for chunk_id in input_ids:
        if chunk_id not in seen:
            issues.append(f"the input chunk {chunk_id} has no vector")
    return issues


def vectors_by_chunk(row_map: list[dict], matrix: dict) -> dict[str, bytes]:
    """Map chunk id to its raw ``float32`` vector bytes."""

    if len(row_map) != matrix["rows"]:
        raise ValueError("the row map and the vector matrix have different lengths")
    vectors: dict[str, bytes] = {}
    for entry in row_map:
        row = entry.get("row")
        chunk_id = str(entry.get("chunk_id") or "")
        if not isinstance(row, int) or isinstance(row, bool) or not 0 <= row < matrix["rows"]:
            raise ValueError(f"row map entry {entry!r} has no usable row index")
        if not chunk_id:
            raise ValueError(f"row map entry {entry!r} has no chunk_id")
        vectors[chunk_id] = matrix["vectors"][row]
    return vectors


# --------------------------------------------------------------------- request
def prepare_job(
    *,
    batch_id: str,
    rows: list[dict],
    userdir: str,
    config: dict,
    force: bool = False,
) -> dict:
    """Write the local request, input and task directory. No TACC access."""

    local_root = REPO_ROOT / "data" / "caches" / "index-requests" / batch_id
    if local_root.exists() and not force:
        raise SystemExit(
            f"{local_root} already exists; pass --batch-id or --force to replace it"
        )
    embedding_config = config.get("embedding") or {}
    request = build_index_request(
        batch_id=batch_id,
        rows=rows,
        userdir=userdir,
        model_config=embedding_config,
    )
    request_path = local_root / "request.json"
    input_path = local_root / "input.jsonl"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_index_input(rows, input_path)
    task_dir = local_root / "task"
    task_dir.mkdir(parents=True, exist_ok=True)
    for name in JOB_FILES:
        shutil.copyfile(JOB_TEMPLATE / name, task_dir / name)
    shutil.copyfile(request_path, task_dir / "request.json")
    # The job falls back to task-directory copies when the USERDIR root upload
    # does not land; keep them next to the request.
    shutil.copyfile(input_path, task_dir / "input.jsonl")
    return {
        "batch_id": batch_id,
        "request": request,
        "rows": rows,
        "local_root": local_root,
        "request_path": request_path,
        "input_path": input_path,
        "task_dir": task_dir,
        "userdir": userdir,
        "job_name": (config.get("jobs", {}).get("index") or {}).get("name", "vt-index"),
    }


def upload_input(job: dict) -> dict:
    """Upload the input JSONL to the USERDIR root; the worker moves it."""

    remote_name = index_input_upload_name(job["batch_id"])
    # tcloud upload keeps the local basename, so stage the build-scoped name
    # that the job looks for at the USERDIR root.
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
        log(f"[index] upload attempt {attempt} failed; retrying")
        time.sleep(10 * attempt)
    else:
        log(f"[index] upload failed: {text.strip()[-300:]}")
        return {"mode": "task_dir", "remote_name": ""}
    log(f"[index] uploaded {remote_name} to {job['userdir']}/")
    return {"mode": "userdir_root", "remote_name": remote_name}


# -------------------------------------------------------------------- TACC run
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
        log(f"[index] submit attempt {attempt} failed; retrying in {15 * attempt}s")
        time.sleep(15 * attempt)
    if not match:
        raise SystemExit(f"submit failed:\n{submit_text}")
    job_id = match.group(1)
    log(f"[index] submitted job {job_id} (batch {job['batch_id']})")
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
            log(f"[index] job {job_id}: status query failed; retrying")
            time.sleep(poll_s)
            continue
        row = [
            line
            for line in status_text.splitlines()
            if line.strip().startswith(job_id)
        ]
        if not row:
            log(f"[index] job {job_id} left the queue")
            return
        fields = row[0].split()
        state = fields[4] if len(fields) > 4 else ""
        log(f"[index] job {job_id} state={state} elapsed={int(time.time() - started)}s")
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
    local_dir = REPO_ROOT / "data" / "caches" / "index-results" / job["batch_id"]
    local_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = f"{RESULT_DIR}/{job['batch_id']}"
    for name in ("vectors.npy", "row_map.jsonl", "summary.json"):
        download_artifact(f"{remote_dir}/{name}", local_dir / name)
    return local_dir


def load_row_map(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"missing artifact: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def store_vectors(job: dict, results_dir: Path, summary: dict) -> dict:
    """Validate the downloaded index result and store it in the knowledge store."""

    from verifiable_tutor.corpus.store import KnowledgeStore
    from verifiable_tutor.storage import Storage

    matrix = read_npy(results_dir / "vectors.npy")
    row_map = load_row_map(results_dir / "row_map.jsonl")
    issues = validate_index_result(job["rows"], row_map, matrix)
    if matrix["dimension"] != int(job["request"]["dimension"]):
        issues.append(
            f"vectors have dimension {matrix['dimension']}, the request recorded "
            f"{job['request']['dimension']}"
        )
    if issues:
        return {"stored": False, "issues": issues, "matrix": matrix}

    built_at = str(summary.get("generated_at") or now_iso())
    model = str(job["request"]["model"])
    by_doc: dict[str, dict[str, bytes]] = {}
    for entry, vector in zip(row_map, matrix["vectors"]):
        by_doc.setdefault(str(entry["doc_id"]), {})[str(entry["chunk_id"])] = vector
    config = load_config()
    database_path = REPO_ROOT / "data" / "app" / "app.sqlite3"
    app_config = REPO_ROOT / "config" / "app.yaml"
    if app_config.is_file():
        app = yaml.safe_load(app_config.read_text(encoding="utf-8")) or {}
        database_path = REPO_ROOT / str((app.get("data") or {}).get("database_path", database_path))
    store = KnowledgeStore(Storage(database_path))
    for doc_id, vectors in by_doc.items():
        store.set_embeddings(doc_id, vectors, model=model, built_at=built_at)

    INDEX_STORE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(results_dir / "vectors.npy", INDEX_STORE / "vectors.npy")
    shutil.copyfile(results_dir / "row_map.jsonl", INDEX_STORE / "row_map.jsonl")
    shutil.copyfile(results_dir / "summary.json", INDEX_STORE / "summary.json")
    return {
        "stored": True,
        "issues": [],
        "documents": {doc_id: len(vectors) for doc_id, vectors in by_doc.items()},
        "vectors": len(row_map),
        "dimension": matrix["dimension"],
        "index_state": store.index_state(),
        "config": config,
    }


def run_index(
    *,
    rows: list[dict],
    state: dict,
    resume: bool = False,
    force: bool = False,
    batch_id: str | None = None,
    dry_run: bool = False,
    timeout_s: int | None = None,
    poll_s: int | None = None,
) -> dict:
    """Run one index job end to end and return the report the ingest CLI stores."""

    config = load_config()
    if resume and not force:
        embedded_docs = {
            doc_id
            for doc_id, record in state.items()
            if (record.get("index") or {}).get("status") == "done"
        }
        if embedded_docs:
            rows = [row for row in rows if row["doc_id"] not in embedded_docs]
            log(f"[index] resuming: {len(embedded_docs)} document(s) already embedded")
    if not rows:
        return {
            "ok": True,
            "batch_id": batch_id or "",
            "job_id": "",
            "skipped_index": True,
            "vectors": 0,
        }
    batch_id = batch_id or datetime.now(timezone.utc).strftime("index-%Y%m%d-%H%M%S")
    userdir = tacc_paths()
    job = prepare_job(
        batch_id=batch_id, rows=rows, userdir=userdir, config=config, force=force
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "batch_id": batch_id,
            "task_dir": str(job["task_dir"]),
            "request": job["request"],
            "chunks": len(rows),
        }
    upload = upload_input(job)
    submission = submit_job(job)
    job["job_id"] = submission["job_id"]
    index_config = config.get("jobs", {}).get("index") or {}
    if timeout_s is None:
        timeout_s = int(index_config.get("queue_timeout_s", 3600))
    if poll_s is None:
        poll_s = int(index_config.get("poll_interval_s", 30))
    try:
        poll_job(submission["job_id"], timeout_s=timeout_s, poll_s=poll_s)
    finally:
        job_log = fetch_log(job, submission["job_id"])
        log(f"[index] job log: {job_log}")
    results_dir = download_results(job, submission["job_id"])
    summary_path = results_dir / "summary.json"
    if not summary_path.is_file():
        raise SystemExit(
            f"job {submission['job_id']} wrote no summary.json; see {job_log}"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    stored = store_vectors(job, results_dir, summary)
    job_started = float(summary.get("job_started_epoch") or submission["submitted_epoch"])
    return {
        "ok": bool(stored["stored"]) and int(summary.get("rows", 0)) == len(job["rows"]),
        "batch_id": batch_id,
        "job_id": submission["job_id"],
        "upload_mode": upload["mode"],
        "chunks": len(job["rows"]),
        "vectors": stored.get("vectors", 0),
        "dimension": stored.get("dimension"),
        "documents": stored.get("documents", {}),
        "issues": stored.get("issues", []),
        "index_state": stored.get("index_state"),
        "timings": {
            "queue_seconds": round(
                max(0.0, job_started - submission["submitted_epoch"]), 3
            ),
            "download_seconds": summary.get("download_seconds"),
            "load_seconds": summary.get("load_seconds"),
            "embed_seconds": summary.get("embed_seconds"),
            "elapsed_seconds": summary.get("elapsed_seconds"),
            "wall_seconds": round(
                max(0.0, time.time() - submission["submitted_epoch"]), 3
            ),
        },
        "summary_path": str(summary_path),
        "vectors_path": str(INDEX_STORE / "vectors.npy"),
        "row_map_path": str(INDEX_STORE / "row_map.jsonl"),
        "job_log": str(job_log),
        "task_dir": str(job["task_dir"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="index input JSONL, one row per chunk")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--state", default=None, help="ingest state JSON to resume from")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--poll-seconds", type=int, default=None)
    args = parser.parse_args(argv)

    rows = read_index_input(Path(args.input))
    state: dict = {}
    if args.state:
        state = json.loads(Path(args.state).read_text(encoding="utf-8")).get(
            "documents", {}
        )
    report = run_index(
        rows=rows,
        state=state,
        resume=args.resume,
        force=args.force,
        batch_id=args.batch_id,
        dry_run=args.dry_run,
        timeout_s=args.timeout,
        poll_s=args.poll_seconds,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
