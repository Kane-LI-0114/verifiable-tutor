#!/usr/bin/env python3
"""Local interface for one PDF parse request against the TACC OCR job.

Round trip: take a local PDF (optionally a page subset), upload it to the TACC
user directory, generate a task directory that points at it, submit the
`tacc/pdf-parse` job, poll until it leaves the queue, download the result
artifacts, and print one JSON object describing the outcome.

This is the interface the demo backend can call or wrap. Stdlib only, so it runs
with either the local 3.11 interpreter or the project venv.

Usage:
  python3 scripts/tacc/parse_pdf.py --pdf ../../course_project.pdf --pages 1-3
  python3 scripts/tacc/parse_pdf.py --pdf in.pdf --pages 1,2 --timeout 2400
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JOB_TEMPLATE = REPO_ROOT / "tacc" / "pdf-parse"
TCLOUD = shutil.which("tcloud") or "tcloud"
FINISHED_STATES = {"CD", "CA", "F", "TO", "NF", "OOM", "BF", "PR"}


def log(message):
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


def tacc_paths():
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


def parse_page_list(spec):
    """Parse 1-3 / 1,2,5 into a list of ints; empty spec means all pages."""
    if not spec:
        return []
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--pages", default="", help="page subset such as 1-3 or 1,2,5; default all pages")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--timeout", type=int, default=2700, help="seconds to wait for the job to leave the queue")
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        raise SystemExit(f"pdf not found: {pdf_path}")
    pages = parse_page_list(args.pages)
    userdir = tacc_paths()

    request_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + f"{int(time.time() * 1000) % 1000:03d}"
    work_root = REPO_ROOT / "data" / "caches" / "parse-requests" / request_id
    upload_dir = work_root / "upload"
    task_dir = work_root / "task"
    output_dir = Path(args.output_dir) if args.output_dir else REPO_ROOT / "data" / "caches" / "parse-results" / request_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    task_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    remote_pdf_name = f"{request_id}-{pdf_path.name}"
    local_upload = upload_dir / remote_pdf_name
    shutil.copyfile(pdf_path, local_upload)

    doc_id = pdf_path.stem
    request = {
        "request_id": request_id,
        "pdf_name": remote_pdf_name,
        "pdf_dir": userdir,
        "doc_id": doc_id,
        "out_dir": f"parse-requests/{request_id}",
        # A compact comma string keeps the shell job able to parse it with sed;
        # an empty string means all pages.
        "pages": ",".join(str(page) for page in pages),
        "local_pdf": str(pdf_path),
    }
    (task_dir / "request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
    for name in ("job.sh",):
        shutil.copyfile(JOB_TEMPLATE / name, task_dir / name)
    job_name = f"vt-parse-{request_id}"
    (task_dir / "tuxiv.conf").write_text(
        "entrypoint:\n"
        "  - bash ${TACC_WORKDIR}/job.sh\n"
        "environment:\n"
        "  name: mpi-gemm-v1\n"
        "  channels:\n"
        "    - nodefaults\n"
        "  dependencies:\n"
        '    - "{}"\n'
        "job:\n"
        f"  name: {job_name}\n"
        "  general:\n"
        "    - partition=tacc\n"
        "    - nodes=1\n"
        "    - ntasks=1\n"
        "    - cpus-per-task=8\n"
        "    - gres=gpu:1\n"
        "    - time=00:59:00\n"
        f"    - output=${{TACC_SLURM_USERLOG}}/{job_name}-%j.log\n",
        encoding="utf-8",
    )

    log(f"[parse] request {request_id}: pdf={pdf_path.name} pages={pages or 'all'} work={work_root}")
    if args.dry_run:
        log(f"[parse] dry run; upload {local_upload} to {userdir}/")
        log(f"[parse] would submit {task_dir}")
        print(json.dumps({"ok": True, "dry_run": True, "request_id": request_id, "task_dir": str(task_dir)}, indent=2))
        return 0

    upload = run([TCLOUD, "upload", str(local_upload), "."], cwd=REPO_ROOT, timeout=600)
    if upload.returncode != 0:
        raise SystemExit(f"upload failed:\n{upload.stdout}\n{upload.stderr}")
    log(f"[parse] uploaded {remote_pdf_name} to {userdir}/")

    stage = run(["bash", str(REPO_ROOT / "scripts" / "tacc" / "submit.sh"), str(task_dir), "--no-submit"], timeout=120)
    if stage.returncode != 0:
        raise SystemExit(f"staging failed:\n{stage.stdout}\n{stage.stderr}")

    submit = run([TCLOUD, "submit"], cwd=task_dir, timeout=300)
    match = re.search(r"Submitted batch job\s+(\d+)", submit.stdout + submit.stderr)
    if not match:
        raise SystemExit(f"submit failed:\n{submit.stdout}\n{submit.stderr}")
    job_id = match.group(1)
    log(f"[parse] submitted job {job_id}")

    started = time.time()
    state = ""
    while True:
        if time.time() - started > args.timeout:
            raise SystemExit(
                f"job {job_id} did not finish within {args.timeout}s (last state {state or 'unknown'})"
            )
        status = run([TCLOUD, "ps", "-j", job_id], timeout=120)
        text = status.stdout + status.stderr
        row = [line for line in text.splitlines() if line.strip().startswith(job_id)]
        if not row:
            log(f"[parse] job {job_id} left the queue")
            break
        fields = row[0].split()
        state = fields[4] if len(fields) > 4 else ""
        log(f"[parse] job {job_id} state={state} elapsed={int(time.time() - started)}s")
        if state in FINISHED_STATES:
            break
        time.sleep(args.poll_seconds)

    log_path = f"slurm_log/{job_name}-{job_id}.log"
    job_log = ""
    for _ in range(6):
        cat = run([TCLOUD, "cat", log_path], timeout=120)
        if cat.returncode == 0 and cat.stdout.strip():
            job_log = cat.stdout
            (work_root / f"job-{job_id}.log").write_text(job_log, encoding="utf-8")
            break
        time.sleep(3)

    remote_out = f"parse-requests/{request_id}"
    artifacts = {
        "summary.json": output_dir / "summary.json",
        "records.json": output_dir / "records.json",
        "pages.jsonl": output_dir / "pages.jsonl",
    }
    for name, target in artifacts.items():
        for _ in range(5):
            result = run([TCLOUD, "download", f"{remote_out}/{name}", str(target)], timeout=180)
            if result.returncode == 0 and target.is_file():
                break
            time.sleep(2)

    document_target = output_dir / f"{doc_id}-ocr.md"
    for _ in range(5):
        result = run(
            [TCLOUD, "download", f"{remote_out}/document/{doc_id}-ocr.md", str(document_target)],
            timeout=180,
        )
        if result.returncode == 0 and document_target.is_file():
            break
        time.sleep(2)

    summary = {}
    if (output_dir / "summary.json").is_file():
        summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    output = {
        "ok": bool(summary) and int(summary.get("fail", 1)) == 0 and int(summary.get("pages_ok", 0) or 0) > 0,
        "request_id": request_id,
        "job_id": job_id,
        "pdf": pdf_path.name,
        "pages_requested": pages or "all",
        "pages_returned": summary.get("pages"),
        "pages": summary.get("pages"),
        "pages_ok": summary.get("pages_ok"),
        "blocks_total": summary.get("blocks_total"),
        "chars_total": summary.get("chars_total"),
        "median_page_seconds": summary.get("median_page_seconds"),
        "vllm_startup_seconds": summary.get("vllm_startup_seconds"),
        "document_markdown": str(document_target) if document_target.is_file() else "",
        "pages_jsonl": str(output_dir / "pages.jsonl") if (output_dir / "pages.jsonl").is_file() else "",
        "summary_json": str(output_dir / "summary.json") if (output_dir / "summary.json").is_file() else "",
        "job_log": str(work_root / f"job-{job_id}.log") if (work_root / f"job-{job_id}.log").is_file() else "",
        "task_dir": str(task_dir),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if not output["ok"]:
        if job_log:
            log("[parse] last log lines:\n" + "\n".join(job_log.splitlines()[-25:]))
        return 1
    log(f"[parse] done: {output['pages_ok']}/{output['pages']} pages, document={document_target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
