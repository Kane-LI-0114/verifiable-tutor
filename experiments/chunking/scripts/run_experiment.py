"""Run the isolated chunking experiment.

Examples (from the repository root, with the experiment virtualenv):

  experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py validate
  experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py run --cells pilot --run-id pilot-01
  experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py run --cells full --calibrate-semantic --run-id full-01
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(ROOT))

from chunking_eval.runner import (  # noqa: E402
    FULL_CELLS,
    LONG_PAGE_CELLS,
    PILOT_CELLS,
    VectorCache,
    build_cell,
    evaluate_cell,
    format_table,
    load_pages,
    load_questions,
    summarise,
    validate_questions,
)

DEFAULT_PAGES = ROOT / "data" / "pages"
DEFAULT_QUESTIONS = ROOT / "questions" / "retrieval_v1.jsonl"
DEFAULT_MODEL = ROOT / "models" / "bge-m3"
DEFAULT_CACHE = ROOT / "data" / "cache" / "vectors.db"
DEFAULT_INDEX = ROOT / "data" / "index"


def build_embedder(model_path: Path):
    import torch

    from verifiable_tutor.evidence.embedding import LocalEmbedder

    if not model_path.is_dir():
        raise SystemExit(
            f"BGE-M3 weights not found at {model_path}. "
            "Run: experiments/chunking/.venv/Scripts/hf download "
            "BAAI/bge-m3 --local-dir experiments/chunking/models/bge-m3"
        )
    torch.set_num_threads(min(12, torch.get_num_threads()))
    return LocalEmbedder(
        model_path=str(model_path),
        device="cpu",
        max_length=512,
        batch_size=16,
        dimension=1024,
    )


def resolve_cells(value: str) -> tuple[str, ...]:
    if value == "pilot":
        return PILOT_CELLS
    if value == "full":
        return FULL_CELLS
    if value == "long":
        return LONG_PAGE_CELLS
    return tuple(part.strip() for part in value.split(",") if part.strip())


def calibrate_semantic(
    pages,
    questions,
    embedder,
    cache: VectorCache,
    *,
    thresholds=(0.25, 0.30, 0.35),
    index_dir: Path = DEFAULT_INDEX,
) -> tuple[float, list[dict]]:
    dev = [question for question in questions if question["split"] == "D"]
    results = []
    for threshold in thresholds:
        name = f"semantic_cal_{int(round(threshold * 100)):03d}"
        print(f"[calibrate] semantic threshold={threshold} -> {name}", flush=True)
        store, chunks, _page_map, stats = build_cell(
            name,
            pages,
            embedder,
            cache,
            index_dir,
            config_override={
                "strategy": "semantic",
                "max_tokens": 450,
                "threshold": threshold,
            },
        )
        rows = evaluate_cell(
            store,
            embedder,
            dev,
            cell=name,
            modes=("hybrid",),
            ks=(5,),
        )
        score = statistics.mean(float(row["ndcg@5"]) for row in rows)
        results.append(
            {
                "threshold": threshold,
                "dev_ndcg@5": round(score, 6),
                "chunks": stats["chunks"],
                "mean_tokens": stats["mean_tokens"],
            }
        )
        print(
            f"[calibrate] threshold={threshold} dev_ndcg@5={score:.4f} "
            f"chunks={stats['chunks']} mean_tokens={stats['mean_tokens']}",
            flush=True,
        )
        store.close()
    best = max(results, key=lambda item: (item["dev_ndcg@5"], -item["threshold"]))
    return float(best["threshold"]), results


def command_validate(args) -> int:
    pages = load_pages(args.pages)
    questions = load_questions(args.questions)
    errors = validate_questions(questions, pages)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    counts = Counter((question["split"], question["stratum"]) for question in questions)
    print(f"ok: {len(questions)} questions, {len(pages)} pages")
    for key, value in sorted(counts.items()):
        print(f"  {key[0]}/{key[1]}: {value}")
    return 0


def command_run(args) -> int:
    pages = load_pages(args.pages)
    questions = load_questions(args.questions)
    errors = validate_questions(questions, pages)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    cells = resolve_cells(args.cells)
    unknown = [cell for cell in cells if cell not in FULL_CELLS]
    if unknown:
        raise SystemExit(f"unknown cells: {unknown}")

    run_id = args.run_id or time.strftime("run-%Y%m%d-%H%M%S")
    out_dir = Path(args.out) / run_id
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    index_dir = Path(args.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    embedder = build_embedder(Path(args.model_path))
    cache = VectorCache(args.cache, model="BAAI/bge-m3")

    semantic_threshold = float(args.semantic_threshold)
    calibration = None
    if args.calibrate_semantic:
        semantic_threshold, calibration = calibrate_semantic(
            pages, questions, embedder, cache, index_dir=index_dir
        )
        print(f"[calibrate] selected threshold={semantic_threshold}", flush=True)

    all_rows: list[dict] = []
    cell_stats: dict[str, dict] = {}
    for cell in cells:
        started = time.time()
        print(f"[run] {cell}", flush=True)
        store, chunks, _page_map, stats = build_cell(
            cell,
            pages,
            embedder,
            cache,
            index_dir,
            threshold=semantic_threshold if cell == "semantic_450" else None,
        )
        rows = evaluate_cell(
            store,
            embedder,
            questions,
            cell=cell,
            modes=args.modes,
            ks=args.ks,
        )
        with (raw_dir / f"{cell}.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        all_rows.extend(rows)
        cell_stats[cell] = stats
        store.close()
        print(
            f"[run] {cell} done: {stats['chunks']} chunks, "
            f"{time.time() - started:.1f}s",
            flush=True,
        )

    summary = summarise(all_rows, cell_stats, ks=args.ks, modes=args.modes)
    summary["run"] = {
        "run_id": run_id,
        "questions": str(Path(args.questions)),
        "pages": str(Path(args.pages)),
        "cells": list(cells),
        "modes": list(args.modes),
        "ks": list(args.ks),
        "semantic_threshold": semantic_threshold,
        "semantic_calibration": calibration,
        "question_counts": {
            "total": len(questions),
            "dev": sum(1 for question in questions if question["split"] == "D"),
            "test": sum(1 for question in questions if question["split"] == "T"),
            "by_category": dict(Counter(question["category"] for question in questions)),
            "by_stratum": dict(Counter(question["stratum"] for question in questions)),
        },
        "model": "BAAI/bge-m3",
        "max_length": 512,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(format_table(summary))
    print(f"[run] summary written to {out_dir / 'summary.json'}")
    cache.close()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", default=str(DEFAULT_PAGES))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.set_defaults(func=command_validate)

    run = subparsers.add_parser("run")
    run.add_argument("--cells", default="pilot")
    run.add_argument("--modes", default="hybrid,lexical,dense")
    run.add_argument("--ks", default="3,5,10")
    run.add_argument("--run-id", default="")
    run.add_argument("--out", default=str(ROOT / "results"))
    run.add_argument("--index-dir", default=str(DEFAULT_INDEX))
    run.add_argument("--model-path", default=str(DEFAULT_MODEL))
    run.add_argument("--cache", default=str(DEFAULT_CACHE))
    run.add_argument("--calibrate-semantic", action="store_true")
    run.add_argument("--semantic-threshold", default="0.6")
    run.set_defaults(func=command_run)

    args = parser.parse_args(argv)
    if hasattr(args, "modes"):
        args.modes = tuple(part.strip() for part in args.modes.split(",") if part.strip())
    if hasattr(args, "ks"):
        args.ks = tuple(int(part) for part in args.ks.split(",") if part.strip())
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
