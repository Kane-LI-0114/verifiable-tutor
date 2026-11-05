"""The document-summary request and record seam.

Seam: ``build_summary_request``, ``summary_input_from_pages``,
``validate_document_summary`` and the ``kb_worker.py`` dispatch on request
schema. They catch a summary job that misses a document, an outline built from
the wrong pages, a record that names a different document, and a worker that
answers the old card schema. They do not catch a summary that is merely a poor
description of the document.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKER = REPO_ROOT / "tacc" / "serve" / "kb_worker.py"
SUMMARY_PROMPT = REPO_ROOT / "src" / "verifiable_tutor" / "prompts" / "kb_doc_summary_v1.md"
CARD_PROMPT = REPO_ROOT / "src" / "verifiable_tutor" / "prompts" / "kb_v1.md"

PAGES = {
    "ACS_Lecture_0_2026F": [
        {
            "schema": "vt-page-record/1",
            "doc_id": "ACS_Lecture_0_2026F",
            "pdf": "ACS_Lecture_0_2026F.pdf",
            "pdf_sha256": "aa" * 32,
            "page_no": 1,
            "text": "Prelude text on page one.",
            "blocks": [
                {"block_id": 0, "label": "paragraph_title", "content": "Introduction"},
                {"block_id": 1, "label": "text", "content": "Prelude text on page one."},
            ],
        },
        {
            "schema": "vt-page-record/1",
            "doc_id": "ACS_Lecture_0_2026F",
            "pdf": "ACS_Lecture_0_2026F.pdf",
            "pdf_sha256": "aa" * 32,
            "page_no": 2,
            "text": "Second page text.",
            "blocks": [
                {"block_id": 0, "label": "paragraph_title", "content": "Vector Search"},
                {"block_id": 1, "label": "text", "content": "Second page text."},
            ],
        },
        {
            "schema": "vt-page-record/1",
            "doc_id": "ACS_Lecture_0_2026F",
            "pdf": "ACS_Lecture_0_2026F.pdf",
            "pdf_sha256": "aa" * 32,
            "page_no": 3,
            "text": "Third page text.",
            "blocks": [
                {"block_id": 0, "label": "paragraph_title", "content": "Retrieval"},
                {"block_id": 1, "label": "text", "content": "Third page text."},
            ],
        },
    ]
}

SUMMARY_INPUTS = [
    {
        "doc_id": "ACS_Lecture_0_2026F",
        "pdf_sha256": "aa" * 32,
        "page_count": 3,
        "outline": "p1: Introduction\np2: Vector Search\np3: Retrieval",
        "excerpt": "Prelude text on page one.\nSecond page text.",
    },
    {
        "doc_id": "Tutorial_1",
        "pdf_sha256": "bb" * 32,
        "page_count": 16,
        "outline": "p1: Setup",
        "excerpt": "Tutorial text.",
    },
]


def summary_record(doc_id: str) -> dict:
    return {
        "schema": "vt-doc-summary/1",
        "build_id": "sum-test",
        "job_id": "28099",
        "doc_id": doc_id,
        "summary": "This document introduces the course project and its pipeline.",
        "topics": ["course project", "pipeline", "OCR"],
        "page_count": 3,
        "model": "qwen3.8-27b",
        "prompt_version": "doc-summary-v1",
        "corpus_hash": "abc123",
        "created_at": "2026-11-05T02:00:00+00:00",
    }


def test_the_summary_request_lists_every_document_once() -> None:
    from verifiable_tutor.knowledge import build_summary_request

    request = build_summary_request(
        build_id="sum-20261105-01",
        documents=SUMMARY_INPUTS,
        userdir="/mnt/home/lijinchuan/USERDIR",
        prompt_version="doc-summary-v1",
        model="qwen3.8-27b",
        params={"temperature": 0.0, "max_output_tokens": 1024},
    )

    assert request["schema"] == "vt-summary-request/1"
    assert request["build_id"] == "sum-20261105-01"
    assert request["input_path"].endswith(
        "/USERDIR/kb/requests/sum-20261105-01/summary-input.jsonl"
    )
    assert request["record_path"].endswith(
        "/USERDIR/kb/results/sum-20261105-01/summaries.jsonl"
    )
    assert request["progress_path"].endswith(
        "/USERDIR/kb/results/sum-20261105-01/progress.json"
    )
    assert request["prompt_version"] == "doc-summary-v1"
    assert len({document["doc_id"] for document in SUMMARY_INPUTS}) == 2


def test_the_summary_input_carries_the_outline_and_the_first_two_pages() -> None:
    from verifiable_tutor.knowledge import summary_input_from_pages

    document = summary_input_from_pages(PAGES["ACS_Lecture_0_2026F"])

    assert document["doc_id"] == "ACS_Lecture_0_2026F"
    assert document["page_count"] == 3
    assert document["outline"].splitlines() == [
        "p1: Introduction",
        "p2: Vector Search",
        "p3: Retrieval",
    ]
    assert "Prelude text on page one." in document["excerpt"]
    assert "Second page text." in document["excerpt"]
    assert "Third page text." not in document["excerpt"]
    assert document["pdf_sha256"] == "aa" * 32


def test_a_summary_that_names_another_document_is_rejected() -> None:
    from verifiable_tutor.knowledge import validate_document_summary

    record = summary_record("ACS_Lecture_0_2026F")
    record["summary"] = "Tutorial_1 explains how to set up the environment."
    issues = validate_document_summary(
        record, doc_ids=["ACS_Lecture_0_2026F", "Tutorial_1"]
    )
    assert any("Tutorial_1" in issue for issue in issues)

    record["summary"] = "This document introduces the course project."
    assert validate_document_summary(
        record, doc_ids=["ACS_Lecture_0_2026F", "Tutorial_1"]
    ) == []


def test_a_summary_with_too_few_topics_is_rejected() -> None:
    from verifiable_tutor.knowledge import validate_document_summary

    record = summary_record("Tutorial_1")
    record["topics"] = ["one topic"]

    issues = validate_document_summary(record, doc_ids=["Tutorial_1"])

    assert any("topics" in issue for issue in issues)


class ChatHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        self.server.requests.append(body)
        content = json.dumps(
            {
                "summary": "A grounded document summary.",
                "topics": ["course project", "pipeline", "OCR"],
            }
        )
        payload = {
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": content}}
            ]
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:
        pass


def start_stub() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), ChatHandler)
    server.requests = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def write_summary_request(tmp_path: Path, documents: list[dict]) -> Path:
    input_path = tmp_path / "summary-input.jsonl"
    input_path.write_text(
        "".join(json.dumps(document) + "\n" for document in documents),
        encoding="utf-8",
    )
    results = tmp_path / "results"
    request = {
        "schema": "vt-summary-request/1",
        "build_id": "sum-test",
        "input_path": str(input_path),
        "record_path": str(results / "summaries.jsonl"),
        "progress_path": str(results / "progress.json"),
        "prompt_version": "doc-summary-v1",
        "model": "qwen3.8-27b",
        "params": {"temperature": 0.0, "max_output_tokens": 512},
        "corpus_hash": "abc123",
        "created_at": "2026-11-05T02:00:00+00:00",
    }
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    return request_path


def test_the_worker_dispatches_a_summary_request(tmp_path: Path) -> None:
    server = start_stub()
    try:
        request_path = write_summary_request(tmp_path, SUMMARY_INPUTS)
        staged_worker = tmp_path / "kb_worker.py"
        shutil.copyfile(WORKER, staged_worker)
        shutil.copyfile(SUMMARY_PROMPT, tmp_path / "kb_doc_summary_v1.md")
        shutil.copyfile(CARD_PROMPT, tmp_path / "kb_v1.md")
        result = subprocess.run(
            [
                sys.executable,
                str(staged_worker),
                "--request",
                str(request_path),
                "--server-url",
                f"http://127.0.0.1:{server.server_port}/v1",
                "--model",
                "qwen3.8-27b",
                "--job-id",
                "28099",
                "--job-started-epoch",
                "1000",
                "--vllm-ready-epoch",
                "1100",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "SLURM_JOB_ID": "28099"},
        )
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    summaries = [
        json.loads(line)
        for line in (tmp_path / "results" / "summaries.jsonl").read_text().splitlines()
        if line
    ]
    assert [record["schema"] for record in summaries] == ["vt-doc-summary/1"] * 2
    assert [record["doc_id"] for record in summaries] == [
        "ACS_Lecture_0_2026F",
        "Tutorial_1",
    ]
    assert all(record["job_id"] == "28099" for record in summaries)
    progress = json.loads((tmp_path / "results" / "progress.json").read_text())
    assert progress["status"] == "done"
    assert progress["done_chunks"] == 2
    assert progress["total_chunks"] == 2
    user_prompt = server.requests[0]["messages"][1]["content"]
    assert "p1: Introduction" in user_prompt
    assert "ACS_Lecture_0_2026F" in user_prompt
