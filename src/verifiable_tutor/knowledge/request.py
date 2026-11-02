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
