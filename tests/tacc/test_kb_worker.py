import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKER = REPO_ROOT / "tacc" / "serve" / "kb_worker.py"

CHUNKS = [
    {
        "chunk_id": "course_project:p001:c00",
        "doc_id": "course_project",
        "page_no": 1,
        "section": "Course Project",
        "source_block_ids": ["0", "1"],
        "text": "Course Project\nBuilding an End-to-End Agent System",
    },
    {
        "chunk_id": "course_project:p003:c00",
        "doc_id": "course_project",
        "page_no": 3,
        "section": None,
        "source_block_ids": ["0"],
        "text": "Lecture notes about MPI",
    },
]


def record_json(chunk: dict) -> str:
    return json.dumps(
        {
            "summary": "A grounded summary of the chunk.",
            "key_terms": ["agent system", "MPI"],
            "study_questions": ["What is the topic?", "Which course is it for?"],
            "citations": [
                {
                    "doc_id": chunk["doc_id"],
                    "page_no": chunk["page_no"],
                    "quote": chunk["text"],
                }
            ],
        }
    )


class ChatHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        self.server.requests.append(body)
        content = self.server.reply(body, len(self.server.requests))
        payload = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": "qwen3.8-27b",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:
        pass


def start_stub(reply) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), ChatHandler)
    server.requests = []
    server.reply = reply
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def write_request(tmp_path: Path, *, chunks=None, deadline=None) -> Path:
    chunks = chunks if chunks is not None else CHUNKS
    input_path = tmp_path / "input.jsonl"
    input_path.write_text(
        "\n".join(json.dumps(chunk) for chunk in chunks) + "\n", encoding="utf-8"
    )
    request = {
        "schema": "vt-kb-request/1",
        "build_id": "kb-20261102-01",
        "shard_id": "course_project-p001-p003",
        "doc_ids": ["course_project"],
        "input_path": str(input_path),
        "record_path": str(tmp_path / "records.jsonl"),
        "progress_path": str(tmp_path / "progress.json"),
        "prompt_version": "kb-v1",
        "model": "qwen3.8-27b",
        "params": {
            "temperature": 0.0,
            "max_output_tokens": 1024,
            "chunk_count": len(chunks),
            "max_repair_attempts": 1,
        },
        "corpus_hash": "abc123",
        "created_at": "2026-11-02T02:00:00+00:00",
    }
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    if deadline is not None:
        request["deadline_epoch"] = deadline
        request_path.write_text(json.dumps(request), encoding="utf-8")
    return request_path


def run_worker(tmp_path: Path, server: ThreadingHTTPServer, *, deadline=None):
    request_path = write_request(tmp_path, deadline=deadline)
    command = [
        sys.executable,
        str(WORKER),
        "--request",
        str(request_path),
        "--server-url",
        f"http://127.0.0.1:{server.server_port}/v1",
        "--model",
        "qwen3.8-27b",
        "--job-id",
        "28001",
        "--job-started-epoch",
        "1000",
        "--vllm-ready-epoch",
        "1100",
        "--launcher",
        "serve.sh",
    ]
    if deadline is not None:
        command.extend(["--deadline-epoch", str(deadline)])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "SLURM_JOB_ID": "28001"},
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_worker_writes_records_and_progress(tmp_path: Path) -> None:
    server = start_stub(lambda body, call: record_json(CHUNKS[0]))
    try:
        result = run_worker(tmp_path, server)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    records = read_jsonl(tmp_path / "records.jsonl")
    assert len(records) == 2
    assert {record["chunk_id"] for record in records} == {
        chunk["chunk_id"] for chunk in CHUNKS
    }
    assert all(record["schema"] == "vt-kb-record/1" for record in records)
    assert all(record["job_id"] == "28001" for record in records)

    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "done"
    assert progress["done_chunks"] == 2
    assert progress["total_chunks"] == 2

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["chunks_total"] == 2
    assert summary["records_written"] == 2
    assert summary["record_errors"] == 0
    assert summary["vllm_startup_seconds"] == 100


def test_worker_sends_greedy_generation_without_thinking(tmp_path: Path) -> None:
    server = start_stub(lambda body, call: record_json(CHUNKS[0]))
    try:
        result = run_worker(tmp_path, server)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    body = server.requests[0]
    assert body["model"] == "qwen3.8-27b"
    assert body["temperature"] == 0.0
    assert body["chat_template_kwargs"]["enable_thinking"] is False


def test_worker_repairs_one_malformed_answer(tmp_path: Path) -> None:
    def reply(body, call):
        if call % 2 == 1:
            return "Sure, here is the JSON: not valid json"
        return record_json(CHUNKS[0])

    server = start_stub(reply)
    try:
        result = run_worker(tmp_path, server)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    records = read_jsonl(tmp_path / "records.jsonl")
    assert len(records) == 2
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["repair_attempts"] == 2
    assert summary["record_errors"] == 0


def test_worker_fails_when_every_answer_is_malformed(tmp_path: Path) -> None:
    server = start_stub(lambda body, call: "I cannot produce JSON today.")
    try:
        result = run_worker(tmp_path, server)
    finally:
        server.shutdown()

    assert result.returncode != 0
    records_path = tmp_path / "records.jsonl"
    assert not records_path.exists() or records_path.read_text(encoding="utf-8") == ""
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "failed"
    assert progress["done_chunks"] == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["record_errors"] == 2
    assert summary["records_written"] == 0


def test_worker_stops_at_the_deadline(tmp_path: Path) -> None:
    server = start_stub(lambda body, call: record_json(CHUNKS[0]))
    try:
        result = run_worker(tmp_path, server, deadline=1)
    finally:
        server.shutdown()

    assert result.returncode != 0
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["status"] == "failed"
    assert "deadline" in (progress["error"] or "").lower()
    assert server.requests == []
