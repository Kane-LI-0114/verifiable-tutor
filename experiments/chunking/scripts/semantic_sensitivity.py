"""Evaluate the semantic thresholds on the test split for sensitivity."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(ROOT))

from chunking_eval.index import EvalStore  # noqa: E402
from chunking_eval.runner import evaluate_cell, load_questions  # noqa: E402
from chunking_eval.retrieval import DenseSearcher  # noqa: E402


def main() -> int:
    from verifiable_tutor.evidence.embedding import LocalEmbedder

    embedder = LocalEmbedder(
        model_path=str(ROOT / "models" / "bge-m3"),
        device="cpu",
        max_length=512,
        batch_size=8,
        dimension=1024,
    )
    questions = load_questions(ROOT / "questions" / "retrieval_v1.jsonl")
    results = []
    for threshold, name in ((0.25, "semantic_cal_025"), (0.30, "semantic_cal_030"), (0.35, "semantic_cal_035")):
        path = ROOT / "data" / "index" / f"{name}.db"
        store = EvalStore(path)
        rows = evaluate_cell(
            store,
            embedder,
            questions,
            cell=name,
            modes=("hybrid",),
            ks=(3, 5, 10),
        )
        test = [row for row in rows if row["split"] == "T"]
        results.append(
            {
                "threshold": threshold,
                "chunks": store.count(),
                "ndcg@5": round(statistics.mean(float(row["ndcg@5"]) for row in test), 4),
                "hit@5": round(statistics.mean(float(row["hit@5"]) for row in test), 4),
                "tokens@5": round(
                    statistics.mean(float(row["context_tokens@5"]) for row in test), 0
                ),
            }
        )
        store.close()
    print(json.dumps(results, indent=2))
    out = ROOT / "results" / "full-01" / "semantic_sensitivity.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
