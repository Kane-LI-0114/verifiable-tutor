"""Analyse the questions whose gold page is long enough to be split.

The long-page cells keep every page at or below the budget whole and only split
pages above it. The overall score can hide that effect, so this script reports
the subset of test questions whose gold page is actually affected.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

import sys

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(ROOT))

from chunking_eval.runner import (  # noqa: E402
    bootstrap_ci,
    load_pages,
    load_questions,
    mcnemar_p,
)
from chunking_eval.strategies import estimate_tokens, usable_blocks  # noqa: E402
from verifiable_tutor.corpus.chunker import normalize_doc_id  # noqa: E402

THRESHOLDS = {
    "keep200_split128": 200,
    "keep256_split128": 256,
    "keep450_split128": 450,
}

COMPARATORS = ("page_first_450", "recursive_128", "recursive_256")


def affected_pages(pages, threshold):
    result = set()
    for page in pages:
        doc_id = normalize_doc_id(str(page.get("doc_id") or ""))
        total = sum(
            estimate_tokens(str(block.get("content") or ""))
            for block in usable_blocks(page)
        )
        if total > threshold:
            result.add((doc_id, int(page["page_no"])))
    return result


def load_raw(raw_dir, cell):
    rows = []
    with (Path(raw_dir) / f"{cell}.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def paired(base, cell, qids, key):
    base_by = {row["qid"]: row for row in base}
    cell_by = {row["qid"]: row for row in cell}
    common = [qid for qid in qids if qid in base_by and qid in cell_by]
    deltas = [float(cell_by[qid][key]) - float(base_by[qid][key]) for qid in common]
    wins = sum(delta > 1e-12 for delta in deltas)
    losses = sum(delta < -1e-12 for delta in deltas)
    ties = len(deltas) - wins - losses
    return {
        "questions": len(common),
        "mean_delta": round(statistics.mean(deltas), 6) if deltas else 0.0,
        "ci": [round(value, 6) for value in bootstrap_ci(deltas)] if deltas else [0, 0],
        "wins": wins,
        "ties": ties,
        "losses": losses,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--split", default="T")
    parser.add_argument("--mode", default="hybrid")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    pages = load_pages(ROOT / "data" / "pages")
    questions = load_questions(ROOT / "questions" / "retrieval_v1.jsonl")
    raw_dir = run_dir / "raw"

    def rows_for(cell, qids=None):
        rows = load_raw(raw_dir, cell)
        selected = [
            row
            for row in rows
            if row["mode"] == args.mode and row["split"] == args.split
        ]
        if qids is not None:
            selected = [row for row in selected if row["qid"] in qids]
        return selected

    def metrics(rows):
        return {
            "ndcg@5": round(statistics.mean(row["ndcg@5"] for row in rows), 6),
            "hit@3": round(statistics.mean(row["hit@3"] for row in rows), 6),
            "tokens@5": round(
                statistics.mean(row["context_tokens@5"] for row in rows), 1
            ),
        }

    output = {"split": args.split, "mode": args.mode, "cells": {}}
    for cell, threshold in THRESHOLDS.items():
        affected = affected_pages(pages, threshold)
        qids = [
            question["qid"]
            for question in questions
            if question["split"] == args.split
            and any(
                (doc_id, page_no) in affected
                for doc_id, page_no in question["gold_pages"]
            )
        ]
        subset = rows_for(cell, qids)
        overall = rows_for(cell)
        base_subset = rows_for("page_first_450", qids)
        base_overall = rows_for("page_first_450")

        comparators = {}
        for name in COMPARATORS:
            rows = rows_for(name, qids)
            comparators[name] = metrics(rows)

        hit_base = {row["qid"]: row["hit@3"] for row in base_subset}
        hit_cell = {row["qid"]: row["hit@3"] for row in subset}
        baseline_only = sum(
            1 for qid in qids if hit_base.get(qid) and not hit_cell.get(qid)
        )
        cell_only = sum(
            1 for qid in qids if hit_cell.get(qid) and not hit_base.get(qid)
        )

        output["cells"][cell] = {
            "threshold": threshold,
            "affected_pages": len(affected),
            "subset_questions": qids,
            "subset": metrics(subset),
            "overall": metrics(overall),
            "comparators_subset": comparators,
            "vs_page_first_450_subset": paired(base_subset, subset, qids, "ndcg@5"),
            "vs_page_first_450_overall": paired(
                base_overall, overall, [row["qid"] for row in overall], "ndcg@5"
            ),
            "mcnemar_hit3_subset": {
                "baseline_only": baseline_only,
                "cell_only": cell_only,
                "p": round(mcnemar_p(baseline_only, cell_only), 6),
            },
        }

    out = run_dir / "long_page_subset.json"
    out.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
