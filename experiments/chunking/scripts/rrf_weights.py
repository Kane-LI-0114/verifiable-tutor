"""Sweep the RRF lexical/dense weights on the three strongest cells.

The retriever passes the lexical ranking first and the dense ranking second, so
a weights tuple ``(lexical, dense)`` is used throughout. The labels in the
report are written as ``dense:lexical`` to match the question being asked:
2:1 means twice the dense weight, 1:2 means twice the lexical weight.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(ROOT))

from chunking_eval.index import EvalStore  # noqa: E402
from chunking_eval.runner import (  # noqa: E402
    bootstrap_ci,
    evaluate_cell,
    load_questions,
    mcnemar_p,
)

CELLS = ("recursive_450", "page_only", "page_first_450")

# label -> (lexical weight, dense weight)
WEIGHTS = {
    "dense1_lex1": (1.0, 1.0),
    "dense2_lex1": (1.0, 2.0),
    "dense1_lex2": (2.0, 1.0),
}


def mean(rows, key):
    return statistics.mean(float(row[key]) for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="rrf-weights-01")
    parser.add_argument("--ks", default="3,5,10")
    args = parser.parse_args()
    ks = tuple(int(part) for part in args.ks.split(",") if part.strip())

    from verifiable_tutor.evidence.embedding import LocalEmbedder

    embedder = LocalEmbedder(
        model_path=str(ROOT / "models" / "bge-m3"),
        device="cpu",
        max_length=512,
        batch_size=8,
        dimension=1024,
    )
    questions = load_questions(ROOT / "questions" / "retrieval_v1.jsonl")
    out_dir = ROOT / "results" / args.run_id
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_rows = {}
    for cell in CELLS:
        store = EvalStore(ROOT / "data" / "index" / f"{cell}.db")
        for label, weights in WEIGHTS.items():
            started = time.time()
            rows = evaluate_cell(
                store,
                embedder,
                [question for question in questions if question["split"] == "T"],
                cell=f"{cell}@{label}",
                modes=("hybrid",),
                ks=ks,
                weights=weights,
            )
            all_rows[f"{cell}@{label}"] = rows
            with (raw_dir / f"{cell}@{label}.jsonl").open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(
                f"[rrf] {cell} {label} nDCG@5={mean(rows, 'ndcg@5'):.4f} "
                f"tokens@5={mean(rows, 'context_tokens@5'):.0f} "
                f"({time.time() - started:.1f}s)",
                flush=True,
            )
        store.close()

    summary = {"ks": list(ks), "cells": list(CELLS), "weights": WEIGHTS, "results": {}, "comparisons": []}
    for cell in CELLS:
        for label, weights in WEIGHTS.items():
            key = f"{cell}@{label}"
            rows = all_rows[key]
            ndcg = [float(row["ndcg@5"]) for row in rows]
            summary["results"][key] = {
                "cell": cell,
                "label": label,
                "weights_lexical": weights[0],
                "weights_dense": weights[1],
                "ndcg@5": round(mean(rows, "ndcg@5"), 6),
                "ndcg@5_ci": [round(value, 6) for value in bootstrap_ci(ndcg)],
                "hit@3": round(mean(rows, "hit@3"), 6),
                "hit@5": round(mean(rows, "hit@5"), 6),
                "tokens@5": round(mean(rows, "context_tokens@5"), 1),
            }

    for cell in CELLS:
        base = {row["qid"]: row for row in all_rows[f"{cell}@dense1_lex1"]}
        for label in ("dense2_lex1", "dense1_lex2"):
            rows = {row["qid"]: row for row in all_rows[f"{cell}@{label}"]}
            common = sorted(set(base) & set(rows))
            deltas = [float(rows[qid]["ndcg@5"]) - float(base[qid]["ndcg@5"]) for qid in common]
            wins = sum(delta > 1e-12 for delta in deltas)
            losses = sum(delta < -1e-12 for delta in deltas)
            baseline_only = sum(
                1 for qid in common if base[qid]["hit@3"] and not rows[qid]["hit@3"]
            )
            cell_only = sum(
                1 for qid in common if rows[qid]["hit@3"] and not base[qid]["hit@3"]
            )
            summary["comparisons"].append(
                {
                    "cell": cell,
                    "label": label,
                    "questions": len(common),
                    "mean_delta_ndcg@5": round(statistics.mean(deltas), 6),
                    "ci": [round(value, 6) for value in bootstrap_ci(deltas)],
                    "wins": wins,
                    "ties": len(deltas) - wins - losses,
                    "losses": losses,
                    "mcnemar_hit3": {
                        "baseline_only": baseline_only,
                        "cell_only": cell_only,
                        "p": round(mcnemar_p(baseline_only, cell_only), 6),
                    },
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n| Cell | Weights dense:lex | nDCG@5 | hit@3 | tokens@5 | Δ nDCG@5 vs 1:1 | W/T/L |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for cell in CELLS:
        for label in WEIGHTS:
            item = summary["results"][f"{cell}@{label}"]
            delta = "-"
            wtl = "-"
            for comparison in summary["comparisons"]:
                if comparison["cell"] == cell and comparison["label"] == label:
                    delta = f"{comparison['mean_delta_ndcg@5']:+.4f} [{comparison['ci'][0]:+.4f}, {comparison['ci'][1]:+.4f}]"
                    wtl = f"{comparison['wins']}/{comparison['ties']}/{comparison['losses']}"
            weights = f"{item['weights_dense']:.0f}:{item['weights_lexical']:.0f}"
            print(
                f"| {cell} | {weights} | {item['ndcg@5']:.4f} | {item['hit@3']:.3f} | "
                f"{item['tokens@5']:.0f} | {delta} | {wtl} |"
            )
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
