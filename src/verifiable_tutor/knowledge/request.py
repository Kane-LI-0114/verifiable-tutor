"""Build the ``vt-kb-request/1`` manifest for one knowledge-base build.

The contract is owned by ``docs/knowledge-schema.md``: the local backend writes
the request and the input JSONL into ``USERDIR``, and the TACC job writes its
records and progress next to the request under ``USERDIR/kb/results/``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Mapping, Sequence

from verifiable_tutor.knowledge.chunks import normalize_doc_id

REQUEST_SCHEMA = "vt-kb-request/1"
REQUEST_DIR = "kb/requests"
RESULT_DIR = "kb/results"


def canonical_line(chunk: Mapping) -> str:
    """Return one canonical JSON line for the input JSONL."""

    return json.dumps(chunk, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def corpus_hash(chunks: Sequence[Mapping]) -> str:
    """Hash the canonical input lines, so equal chunks always hash equally."""

    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(canonical_line(chunk).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _shard_id(chunks: Sequence[Mapping]) -> str:
    doc_ids = sorted({str(chunk["doc_id"]) for chunk in chunks})
    pages = [int(chunk["page_no"]) for chunk in chunks]
    return f"{doc_ids[0]}-p{min(pages):03d}-p{max(pages):03d}"


def build_request(
    *,
    build_id: str,
    chunks: Sequence[Mapping],
    userdir: str,
    prompt_version: str,
    model: str,
    params: Mapping,
    created_at: str | None = None,
) -> dict:
    """Return the manifest object the TACC job reads."""

    if not chunks:
        raise ValueError("a knowledge-base request needs at least one chunk")
    if not build_id:
        raise ValueError("build_id is required")
    userdir = userdir.rstrip("/")
    request_dir = f"{userdir}/{REQUEST_DIR}/{build_id}"
    result_dir = f"{userdir}/{RESULT_DIR}/{build_id}"
    return {
        "schema": REQUEST_SCHEMA,
        "build_id": build_id,
        "shard_id": _shard_id(chunks),
        "doc_ids": sorted({str(chunk["doc_id"]) for chunk in chunks}),
        "input_path": f"{request_dir}/input.jsonl",
        "record_path": f"{result_dir}/records.jsonl",
        "progress_path": f"{result_dir}/progress.json",
        "prompt_version": prompt_version,
        "model": model,
        "params": dict(params),
        "corpus_hash": corpus_hash(chunks),
        "created_at": created_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


SUMMARY_REQUEST_SCHEMA = "vt-summary-request/1"
SUMMARY_REQUEST_DIR = "kb/requests"
SUMMARY_RESULT_DIR = "kb/results"
#: How many leading pages of a document feed the summary excerpt.
SUMMARY_EXCERPT_PAGES = 2


def _title_blocks(page: Mapping) -> list[str]:
    blocks = [
        block
        for block in page.get("blocks") or []
        if isinstance(block, Mapping) and block.get("label") == "paragraph_title"
    ]
    blocks.sort(
        key=lambda block: (
            block.get("block_order") is None,
            block.get("block_order") or 0,
        )
    )
    return [
        str(block.get("content") or "").strip()
        for block in blocks
        if str(block.get("content") or "").strip()
    ]


def summary_input_from_pages(pages: Sequence[Mapping]) -> dict:
    """Build one summary input line from a document's page records.

    The input carries the outline (the ``paragraph_title`` blocks in page
    order) and the text of the first two pages, which is what lets Qwen summarise
    a long deck without reading all of it (docs/knowledge-schema.md section 6).
    """

    ordered = sorted(pages, key=lambda page: int(page.get("page_no") or 0))
    if not ordered:
        raise ValueError("a summary input needs at least one page record")
    doc_id = normalize_doc_id(str(ordered[0].get("doc_id") or ""))
    if not doc_id:
        raise ValueError("page record has no doc_id")
    outline: list[str] = []
    for page in ordered:
        page_no = int(page.get("page_no") or 0)
        for title in _title_blocks(page):
            outline.append(f"p{page_no}: {title}")
    excerpt = "\n".join(
        str(page.get("text") or "").strip()
        for page in ordered[:SUMMARY_EXCERPT_PAGES]
        if str(page.get("text") or "").strip()
    )
    return {
        "doc_id": doc_id,
        "pdf_sha256": str(ordered[0].get("pdf_sha256") or ""),
        "page_count": len(ordered),
        "outline": "\n".join(outline),
        "excerpt": excerpt,
    }


def summary_corpus_hash(documents: Sequence[Mapping]) -> str:
    """Hash the canonical summary input lines, so equal input always hashes equally."""

    digest = hashlib.sha256()
    for document in documents:
        digest.update(canonical_line(document).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_summary_request(
    *,
    build_id: str,
    documents: Sequence[Mapping],
    userdir: str,
    prompt_version: str,
    model: str,
    params: Mapping,
    created_at: str | None = None,
) -> dict:
    """Return the ``vt-summary-request/1`` manifest the TACC job reads."""

    if not documents:
        raise ValueError("a summary request needs at least one document")
    if not build_id:
        raise ValueError("build_id is required")
    doc_ids = [str(document.get("doc_id") or "") for document in documents]
    if any(not doc_id for doc_id in doc_ids):
        raise ValueError("every summary input needs a doc_id")
    if len(set(doc_ids)) != len(doc_ids):
        raise ValueError("a summary request lists each document once")
    userdir = userdir.rstrip("/")
    request_dir = f"{userdir}/{SUMMARY_REQUEST_DIR}/{build_id}"
    result_dir = f"{userdir}/{SUMMARY_RESULT_DIR}/{build_id}"
    return {
        "schema": SUMMARY_REQUEST_SCHEMA,
        "build_id": build_id,
        "input_path": f"{request_dir}/summary-input.jsonl",
        "record_path": f"{result_dir}/summaries.jsonl",
        "progress_path": f"{result_dir}/progress.json",
        "prompt_version": prompt_version,
        "model": model,
        "params": dict(params),
        "corpus_hash": summary_corpus_hash(documents),
        "created_at": created_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
