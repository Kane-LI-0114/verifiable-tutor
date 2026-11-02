#!/usr/bin/env python3
"""Generate knowledge-base records for one chunk batch with in-job Qwen.

This script runs inside the submitted ``tacc/serve`` GPU job, after the job has
started vLLM and waited for the local endpoint. It reads the ``vt-kb-request/1``
manifest, calls the local OpenAI-compatible endpoint once per chunk, parses a
strict JSON answer, and writes ``records.jsonl``, ``progress.json`` and
``summary.json`` into ``USERDIR``. It uses only the Python standard library so
the public environment needs no extra packages.

The job is the writer; the local driver is the validator.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROMPT_PATH = Path(__file__).with_name("prompt_kb_v1.md")
USER_MARKER = "%%USER%%"
RECORD_SCHEMA = "vt-kb-record/1"
PROGRESS_SCHEMA = "vt-kb-progress/1"
SUMMARY_SCHEMA = "vt-kb-summary/1"
REPAIR_INSTRUCTION = (
    "The previous answer was not a valid JSON object. Reply with exactly one JSON "
    "object and nothing else: keys summary, key_terms, study_questions, citations. "
    "Every citations item is an object with doc_id, page_no and quote, and every "
    "quote must be copied verbatim from the page text above."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[kb-worker] {message}", flush=True)


def load_prompt(path: Path) -> tuple[str, str]:
    text = Path(path).read_text(encoding="utf-8")
    if USER_MARKER not in text:
        raise SystemExit(f"prompt template has no {USER_MARKER} marker: {path}")
    system, user = text.split(USER_MARKER, 1)
    return system.strip(), user.strip()


def render_user_prompt(template: str, chunk: dict) -> str:
    section = chunk.get("section") or ""
    return (
        template.replace("{{DOC_ID}}", str(chunk.get("doc_id", "")))
        .replace("{{PAGE_NO}}", str(chunk.get("page_no", "")))
        .replace("{{SECTION}}", str(section))
        .replace("{{TEXT}}", str(chunk.get("text", "")))
    )


def extract_json_object(answer: str) -> dict:
    """Return the first JSON object in an answer, or raise ValueError."""

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("empty answer")
    cleaned = answer.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("answer has no JSON object")
    try:
        obj, _end = json.JSONDecoder().raw_decode(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"answer has invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("answer JSON is not an object")
    return obj


def check_answer_shape(answer: dict) -> None:
    """Check the keys the record writer needs; the local driver checks policy."""

    problems: list[str] = []
    if not isinstance(answer.get("summary"), str) or not answer["summary"].strip():
        problems.append("summary must be a non-empty string")
    for field in ("key_terms", "study_questions"):
        value = answer.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            problems.append(f"{field} must be a list of strings")
    citations = answer.get("citations")
    if not isinstance(citations, list):
        problems.append("citations must be a list")
    else:
        for index, citation in enumerate(citations):
            if not isinstance(citation, dict):
                problems.append(f"citations[{index}] must be an object")
                continue
            if not isinstance(citation.get("doc_id"), str) or not citation["doc_id"].strip():
                problems.append(f"citations[{index}].doc_id must be a non-empty string")
            page_no = citation.get("page_no")
            if isinstance(page_no, bool) or not isinstance(page_no, (int, str)):
                problems.append(f"citations[{index}].page_no must be an integer")
            elif isinstance(page_no, str) and not page_no.strip().isdigit():
                problems.append(f"citations[{index}].page_no must be an integer")
            if not isinstance(citation.get("quote"), str) or not citation["quote"].strip():
                problems.append(f"citations[{index}].quote must be a non-empty string")
    if problems:
        raise ValueError("; ".join(problems))


def post_chat(server_url: str, body: dict, timeout_s: float = 180.0) -> str:
    request = urllib.request.Request(
        server_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        payload = json.loads(response.read().decode("utf-8"))
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("endpoint returned no choices")
    message = choices[0].get("message") or {}
    return message.get("content") or ""


def chat_with_retry(server_url: str, body: dict, timeout_s: float = 180.0) -> str:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return post_chat(server_url, body, timeout_s=timeout_s)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(3)
    raise RuntimeError(f"chat request failed: {last_error}")


def build_messages(
    system: str, user: str, *, repair: bool = False
) -> list[dict]:
    content = user
    if repair:
        content = f"{user}\n\n{REPAIR_INSTRUCTION}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]


def build_record(
    chunk: dict,
    answer: dict,
    *,
    build_id: str,
    job_id: str,
    model: str,
    prompt_version: str,
    corpus_hash: str,
) -> dict:
    citations = []
    for citation in answer["citations"]:
        page_no = citation["page_no"]
        citations.append(
            {
                "doc_id": citation["doc_id"].strip(),
                "page_no": int(page_no),
                "quote": citation["quote"].strip(),
            }
        )
    key_terms = [term.strip() for term in answer["key_terms"] if term.strip()][:8]
    study_questions = [
        question.strip() for question in answer["study_questions"] if question.strip()
    ][:5]
    return {
        "schema": RECORD_SCHEMA,
        "build_id": build_id,
        "job_id": job_id,
        "chunk_id": str(chunk.get("chunk_id", "")),
        "doc_id": str(chunk.get("doc_id", "")),
        "page_no": int(chunk.get("page_no", 0)),
        "section": chunk.get("section"),
        "source_block_ids": [str(value) for value in chunk.get("source_block_ids") or []],
        "summary": answer["summary"].strip(),
        "key_terms": key_terms,
        "study_questions": study_questions,
        "citations": citations,
        "model": model,
        "prompt_version": prompt_version,
        "corpus_hash": corpus_hash,
        "created_at": now_iso(),
    }


def write_json(path: Path, payload: dict, *, fsync: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())
    temporary.replace(path)


def load_request(request_path: Path, userdir: Path) -> tuple[dict, Path]:
    """Read the manifest and make the request/input land in their canonical paths.

    The local driver uploads ``<build_id>-request.json`` and
    ``<build_id>-input.jsonl`` to the USERDIR root, because ``tcloud upload``
    cannot create a nested remote directory. This function moves them into the
    canonical ``kb/requests/<build_id>/`` layout the manifest names. If the
    upload did not land, the copies staged in the task directory are used.
    """

    request = json.loads(request_path.read_text(encoding="utf-8"))
    build_id = str(request.get("build_id", ""))
    input_path = Path(request["input_path"])
    canonical_request = input_path.parent / "request.json"
    if not canonical_request.exists():
        candidates = [userdir / f"{build_id}-request.json", request_path]
        for candidate in candidates:
            if candidate.is_file():
                canonical_request.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, canonical_request)
                break
    if not input_path.exists():
        candidates = [
            userdir / f"{build_id}-input.jsonl",
            request_path.with_name("input.jsonl"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                input_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, input_path)
                break
    if not input_path.exists():
        raise SystemExit(f"input JSONL not found at {input_path}")
    return request, input_path


def load_chunks(input_path: Path) -> list[dict]:
    chunks = []
    with input_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            for field in ("chunk_id", "doc_id", "page_no", "text"):
                if field not in chunk:
                    raise SystemExit(
                        f"input line {line_number} is missing {field!r}"
                    )
            chunks.append(chunk)
    return chunks


def write_progress(
    path: Path,
    *,
    build_id: str,
    job_id: str,
    status: str,
    done: int,
    total: int,
    error: str | None,
) -> None:
    write_json(
        path,
        {
            "schema": PROGRESS_SCHEMA,
            "build_id": build_id,
            "job_id": job_id,
            "status": status,
            "done_chunks": done,
            "total_chunks": total,
            "error": error,
            "updated_at": now_iso(),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--server-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="")
    parser.add_argument("--job-id", default=os.environ.get("SLURM_JOB_ID", "local"))
    parser.add_argument("--job-started-epoch", type=float, default=None)
    parser.add_argument("--vllm-ready-epoch", type=float, default=None)
    parser.add_argument("--launcher", default="direct")
    parser.add_argument(
        "--userdir",
        default=os.environ.get("TACC_USERDIR", os.environ.get("HOME", "")),
        help="USERDIR root where the driver uploaded the build-scoped files",
    )
    parser.add_argument("--deadline-epoch", type=float, default=None)
    parser.add_argument("--prompt", type=Path, default=PROMPT_PATH)
    parser.add_argument("--http-timeout", type=float, default=180.0)
    args = parser.parse_args()

    worker_started = time.time()
    job_started = args.job_started_epoch or worker_started
    ready = args.vllm_ready_epoch or worker_started
    deadline = args.deadline_epoch or float("inf")
    result: dict = {
        "schema": SUMMARY_SCHEMA,
        "build_id": "",
        "job_id": args.job_id,
        "host": socket.gethostname(),
        "model": args.model,
        "prompt_version": "",
        "launcher": args.launcher,
        "job_started_epoch": round(job_started, 3),
        "vllm_ready_epoch": round(ready, 3),
        "vllm_startup_seconds": max(0.0, round(ready - job_started, 3)),
        "records_written": 0,
        "record_errors": 0,
        "repair_attempts": 0,
        "deadline_hit": False,
        "exit_code": 1,
    }

    records_handle = None
    progress_path: Path | None = None
    summary_path: Path | None = None
    try:
        request, input_path = load_request(
            args.request, Path(args.userdir) if args.userdir else Path(".")
        )
        build_id = str(request["build_id"])
        model = args.model or str(request["model"])
        prompt_version = str(request["prompt_version"])
        corpus_hash = str(request["corpus_hash"])
        params = request.get("params") or {}
        chunks = load_chunks(input_path)
        total = len(chunks)
        records_path = Path(request["record_path"])
        progress_path = Path(request["progress_path"])
        summary_path = records_path.with_name("summary.json")
        result.update(
            {
                "build_id": build_id,
                "model": model,
                "prompt_version": prompt_version,
                "chunks_total": total,
            }
        )
        system_prompt, user_template = load_prompt(args.prompt)
        write_progress(
            progress_path,
            build_id=build_id,
            job_id=args.job_id,
            status="running",
            done=0,
            total=total,
            error=None,
        )
        records_path.parent.mkdir(parents=True, exist_ok=True)
        records_handle = records_path.open("w", encoding="utf-8")
        max_repair = int(params.get("max_repair_attempts", 1))
        last_error = ""
        for index, chunk in enumerate(chunks, start=1):
            if time.time() > deadline:
                result["deadline_hit"] = True
                last_error = "deadline exceeded before chunk completion"
                break
            body_base = {
                "model": model,
                "temperature": float(params.get("temperature", 0.0)),
                "max_tokens": int(params.get("max_output_tokens", 1024)),
                "chat_template_kwargs": {"enable_thinking": False},
            }
            user_prompt = render_user_prompt(user_template, chunk)
            try:
                answer_text = chat_with_retry(
                    args.server_url,
                    {**body_base, "messages": build_messages(system_prompt, user_prompt)},
                    timeout_s=args.http_timeout,
                )
                try:
                    answer = extract_json_object(answer_text)
                    check_answer_shape(answer)
                except ValueError:
                    if max_repair < 1:
                        raise
                    result["repair_attempts"] += 1
                    log(f"chunk {index}/{total}: repairing malformed answer")
                    answer_text = chat_with_retry(
                        args.server_url,
                        {
                            **body_base,
                            "messages": build_messages(
                                system_prompt, user_prompt, repair=True
                            ),
                        },
                        timeout_s=args.http_timeout,
                    )
                    answer = extract_json_object(answer_text)
                    check_answer_shape(answer)
                record = build_record(
                    chunk,
                    answer,
                    build_id=build_id,
                    job_id=args.job_id,
                    model=model,
                    prompt_version=prompt_version,
                    corpus_hash=corpus_hash,
                )
                records_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                records_handle.flush()
                os.fsync(records_handle.fileno())
                result["records_written"] += 1
                log(f"chunk {index}/{total}: wrote {chunk.get('chunk_id')}")
            except Exception as exc:  # noqa: BLE001 - one bad chunk must not hide the rest
                result["record_errors"] += 1
                last_error = str(exc)
                log(f"chunk {index}/{total}: failed: {exc}")
            write_progress(
                progress_path,
                build_id=build_id,
                job_id=args.job_id,
                status="running",
                done=result["records_written"],
                total=total,
                error=None,
            )

        finished = time.time()
        error = last_error if (result["record_errors"] or result["deadline_hit"]) else None
        status = "done"
        if (
            result["deadline_hit"]
            or result["records_written"] < total
            or result["record_errors"] > 0
        ):
            status = "failed"
        write_progress(
            progress_path,
            build_id=build_id,
            job_id=args.job_id,
            status=status,
            done=result["records_written"],
            total=total,
            error=error,
        )
        result.update(
            {
                "worker_started_epoch": round(worker_started, 3),
                "worker_finished_epoch": round(finished, 3),
                "build_seconds": round(finished - worker_started, 3),
                "total_seconds": round(finished - job_started, 3),
                "exit_code": 0 if result["records_written"] > 0 else 1,
            }
        )
        return int(result["exit_code"])
    finally:
        if records_handle is not None:
            records_handle.close()
        if summary_path is not None:
            write_json(summary_path, result)
        elif progress_path is not None:
            write_json(progress_path.with_name("summary.json"), result)


if __name__ == "__main__":
    sys.exit(main())
