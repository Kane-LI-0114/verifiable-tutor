#!/usr/bin/env python3
"""Embed the chunks of one ``vt-index-request/1`` batch with BGE-M3 on TACC.

This script runs inside the submitted ``tacc/index`` GPU job. It reads the
manifest, loads the BGE-M3 weights from the path the request names (downloading
them through the Hugging Face mirror when they are missing), encodes every
input line with the model's CLS embedding and L2 normalisation, and writes::

    vectors.npy     float32 matrix, one row per input line, 1024 columns
    row_map.jsonl   one row per input line: row, chunk_id, doc_id, page_no
    summary.json    job id, model, counts, timings and status

The local driver is the validator: it checks that every chunk got exactly one
vector before storing the vectors in the knowledge store.

Usage inside the job:
  qwen-python index_worker.py --request request.json --job-id "$SLURM_JOB_ID" \
      --job-started-epoch "$JOB_STARTED_EPOCH" --deadline-epoch "$DEADLINE"
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SUMMARY_SCHEMA = "vt-index-summary/1"
REQUEST_SCHEMA = "vt-index-request/1"
#: Files needed to load BGE-M3; the ONNX and image weights are not downloaded.
MODEL_FILES = [
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "pytorch_model.bin",
    "model.safetensors",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[index-worker] {message}", flush=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def load_request(request_path: Path, userdir: Path) -> tuple[dict, list[dict], Path]:
    """Read the manifest, move the uploaded input into its canonical path."""

    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request.get("schema") != REQUEST_SCHEMA:
        raise SystemExit(f"request schema must be {REQUEST_SCHEMA}")
    input_path = Path(request["input_path"])
    if not input_path.is_file():
        for candidate in input_candidates(request, userdir, request_path):
            if candidate.is_file() and candidate != input_path:
                input_path.parent.mkdir(parents=True, exist_ok=True)
                input_path.write_bytes(candidate.read_bytes())
                break
    if not input_path.is_file():
        raise SystemExit(f"index input not found at {input_path}")
    rows = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit(f"index input is empty: {input_path}")
    return request, rows, input_path


def input_candidates(request: dict, userdir: Path, request_path: Path) -> list[Path]:
    """Return where the input may be, in the order the worker tries them.

    The local driver uploads ``<batch_id>-index-input.jsonl`` to the USERDIR
    root because ``tcloud upload`` cannot create the nested request directory;
    the staged task-directory copy is the last fallback.
    """

    return [
        Path(request["input_path"]),
        Path(userdir) / f"{request.get('batch_id', '')}-index-input.jsonl",
        Path(request_path).with_name("input.jsonl"),
    ]


def ensure_model(model_path: Path, repo_id: str, deadline: float) -> dict:
    """Return download timing; fetch the weights through the HF mirror if needed."""

    config_file = model_path / "config.json"
    if config_file.is_file():
        log(f"weights present at {model_path}")
        return {"downloaded": False, "download_seconds": 0.0}

    started = time.time()
    model_path.mkdir(parents=True, exist_ok=True)
    log(f"downloading {repo_id} into {model_path} (HF_ENDPOINT={os.environ.get('HF_ENDPOINT')})")
    try:
        from huggingface_hub import snapshot_download  # noqa: PLC0415

        snapshot_download(
            repo_id=repo_id,
            local_dir=str(model_path),
            allow_patterns=MODEL_FILES,
        )
    except Exception as exc:  # noqa: BLE001 - the job reports the failure
        raise SystemExit(
            f"could not download {repo_id} into {model_path}: {type(exc).__name__}: {exc}"
        ) from exc
    seconds = round(time.time() - started, 3)
    if not (model_path / "config.json").is_file():
        raise SystemExit(f"download finished but {model_path / 'config.json'} is missing")
    log(f"weights downloaded in {seconds}s")
    return {"downloaded": True, "download_seconds": seconds}


def load_model(model_path: Path, device: str):
    """Load the BGE-M3 tokenizer and encoder in float32."""

    import torch  # noqa: PLC0415
    from transformers import AutoModel, AutoTokenizer  # noqa: PLC0415

    started = time.time()
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModel.from_pretrained(str(model_path), torch_dtype=torch.float32)
    model.to(device)
    model.eval()
    return tokenizer, model, round(time.time() - started, 3)


def encode_rows(
    rows: list[dict],
    tokenizer,
    model,
    *,
    device: str,
    batch_size: int,
    max_length: int,
    deadline: float,
):
    """Encode rows into a normalised float32 matrix, in input order."""

    import numpy as np  # noqa: PLC0415
    import torch  # noqa: PLC0415
    from torch.nn import functional as functional  # noqa: PLC0415

    vectors = []
    started = time.time()
    for start in range(0, len(rows), batch_size):
        if deadline and time.time() > deadline:
            raise SystemExit(
                f"index deadline reached after {len(vectors)} of {len(rows)} chunks"
            )
        batch = rows[start : start + batch_size]
        encoded = tokenizer(
            [str(row.get("text") or "") for row in batch],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            hidden = model(**encoded).last_hidden_state[:, 0]
            hidden = functional.normalize(hidden, p=2, dim=1)
        vectors.append(hidden.to("cpu", dtype=torch.float32).numpy())
        log(f"embedded {min(start + batch_size, len(rows))}/{len(rows)}")
    matrix = np.concatenate(vectors, axis=0) if vectors else np.zeros((0, 1024), dtype=np.float32)
    return matrix, round(time.time() - started, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--job-id", default=os.environ.get("SLURM_JOB_ID", "local"))
    parser.add_argument("--job-started-epoch", type=float, default=None)
    parser.add_argument("--deadline-epoch", type=float, default=None)
    parser.add_argument(
        "--userdir",
        default=os.environ.get("TACC_USERDIR", os.environ.get("HOME", "")),
    )
    args = parser.parse_args()

    worker_started = time.time()
    job_started = args.job_started_epoch or worker_started
    deadline = args.deadline_epoch or (job_started + 3300)
    result: dict = {
        "schema": SUMMARY_SCHEMA,
        "batch_id": "",
        "job_id": args.job_id,
        "host": socket.gethostname(),
        "model": "",
        "model_path": "",
        "dimension": 0,
        "rows": 0,
        "downloaded": False,
        "download_seconds": 0.0,
        "load_seconds": 0.0,
        "embed_seconds": 0.0,
        "elapsed_seconds": 0.0,
        "device": "",
        "status": "failed",
        "error": None,
        "generated_at": now_iso(),
    }
    request: dict = {}
    try:
        # Read the manifest first so a failure still writes summary.json to the
        # canonical result directory instead of a fallback path.
        request = json.loads(args.request.read_text(encoding="utf-8"))
        request, rows, input_path = load_request(
            args.request, Path(args.userdir) if args.userdir else Path(".")
        )
        result.update(
            {
                "batch_id": request.get("batch_id", ""),
                "model": request.get("model", ""),
                "model_path": request.get("model_path", ""),
                "dimension": int(request.get("dimension", 1024)),
                "rows": len(rows),
                "device": request.get("device", "cuda"),
                "input_path": str(input_path),
                "corpus_hash": request.get("corpus_hash", ""),
                "job_started_epoch": round(job_started, 3),
            }
        )
        model_path = Path(str(request.get("model_path") or "~/models/bge-m3")).expanduser()
        download = ensure_model(model_path, str(request.get("model", "BAAI/bge-m3")), deadline)
        tokenizer, model, load_seconds = load_model(model_path, result["device"])
        matrix, embed_seconds = encode_rows(
            rows,
            tokenizer,
            model,
            device=result["device"],
            batch_size=int(request.get("batch_size", 16)),
            max_length=int(request.get("max_length", 512)),
            deadline=deadline - 120,
        )
        out_dir = Path(request["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        import numpy as np  # noqa: PLC0415

        np.save(out_dir / "vectors.npy", matrix)
        with (out_dir / "row_map.jsonl").open("w", encoding="utf-8") as handle:
            for index, row in enumerate(rows):
                handle.write(
                    json.dumps(
                        {
                            "row": index,
                            "chunk_id": str(row["chunk_id"]),
                            "doc_id": str(row["doc_id"]),
                            "page_no": int(row.get("page_no") or 0),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        result.update(
            {
                "downloaded": download["downloaded"],
                "download_seconds": download["download_seconds"],
                "load_seconds": load_seconds,
                "embed_seconds": embed_seconds,
                "dimension": int(matrix.shape[1]),
                "elapsed_seconds": round(time.time() - job_started, 3),
                "status": "done",
            }
        )
        log(
            f"wrote {matrix.shape[0]}x{matrix.shape[1]} vectors in {embed_seconds}s "
            f"(load {load_seconds}s, total {result['elapsed_seconds']}s)"
        )
        return 0
    except SystemExit as exc:
        result["error"] = str(exc)
        raise
    finally:
        if request:
            summary_path = Path(request["out_dir"]) / "summary.json"
        elif args.userdir:
            summary_path = Path(args.userdir) / "index" / "summary.json"
        else:
            summary_path = Path("summary.json")
        try:
            result["elapsed_seconds"] = round(time.time() - job_started, 3)
            write_json(summary_path, result)
        except Exception as exc:  # noqa: BLE001 - never mask the real failure
            log(f"could not write summary: {exc}")


if __name__ == "__main__":
    sys.exit(main())
