"""Minimal dual-granularity experiment.

Lexical retrieval reads page-level 450-token chunks. Dense retrieval reads
128-token subchunks. Both rankings are converted to pages and fused with RRF at
the page level. The model receives the full text of each selected page, so the
token cost is counted per page, not per retrieved chunk.
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

from chunking_eval.dual import (  # noqa: E402
    fuse_page_rankings,
    page_chunks,
    page_ranking_from_chunks,
)
from chunking_eval.index import EvalStore  # noqa: E402
from chunking_eval.metrics import evaluate_rankings  # noqa: E402
from chunking_eval.retrieval import DenseSearcher  # noqa: E402
from chunking_eval.runner import (  # noqa: E402
    bootstrap_ci,
    load_questions,
    mcnemar_p,
)


def mean(rows, key):
    return statistics.mean(float(row[key]) for row in rows)


def paired(base_rows, cell_rows, qids, key):
    base = {row["qid"]: row for row in base_rows}
    cell = {row["qid"]: row for row in cell_rows}
    common = [qid for qid in qids if qid in base and qid in cell]
    deltas = [float(cell[qid][key]) - float(base[qid][key]) for qid in common]
    wins = sum(delta > 1e-12 for delta in deltas)
    losses = sum(delta < -1e-12 for delta in deltas)
    return {
        "questions": len(common),
        "mean_delta": round(statistics.mean(deltas), 6),
        "ci": [round(value, 6) for value in bootstrap_ci(deltas)],
        "wins": wins,
        "ties": len(deltas) - wins - losses,
        "losses": losses,
    }


def page_tokens_for(top_pages, page_tokens):
    return sum(int(page_tokens.get((doc, page), 0)) for doc, page in top_pages)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="dual-granularity-01")
    parser.add_argument("--ks", default="3,5,10")
    parser.add_argument(
        "--weights",
        default="1:1",
        help="dense:lexical page-level RRF weights, for example 2:1",
    )
    args = parser.parse_args()
    ks = tuple(int(part) for part in args.ks.split(",") if part.strip())
    max_k = max(ks)
    dense_weight, lexical_weight = (float(part) for part in args.weights.split(":"))
    weights = (lexical_weight, dense_weight)
    label = f"dual_page450_sub128_dense{dense_weight:g}_lex{lexical_weight:g}"

    from verifiable_tutor.evidence.embedding import LocalEmbedder

    embedder = LocalEmbedder(
        model_path=str(ROOT / "models" / "bge-m3"),
        device="cpu",
        max_length=512,
        batch_size=8,
        dimension=1024,
    )
    questions = {
        question["qid"]: question
        for question in load_questions(ROOT / "questions" / "retrieval_v1.jsonl")
        if question["split"] == "T"
    }

    page_store = EvalStore(ROOT / "data" / "index" / "page_first_450.db")
    sub_store = EvalStore(ROOT / "data" / "index" / "page_first_128.db")
    dense = DenseSearcher(sub_store, embedder)

    page_map = page_store.page_map()
    all_page_chunks = page_store.get_chunks(list(page_map))
    page_tokens: dict[tuple[str, int], int] = {}
    for chunk in all_page_chunks:
        for doc_id, page_no in page_map.get(chunk["chunk_id"], []):
            page_tokens[(doc_id, page_no)] = (
                page_tokens.get((doc_id, page_no), 0)
                + int(chunk.get("token_estimate") or 0)
            )

    out_dir = ROOT / "results" / args.run_id
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for qid, question in questions.items():
        started = time.time()
        lexical_chunks = page_store.search_chunks(question["question"], limit=30)
        dense_chunks = dense.search(question["question"], k=30)
        lexical_pages = page_ranking_from_chunks(lexical_chunks)
        dense_pages = page_ranking_from_chunks(dense_chunks)
        fused_pages = fuse_page_rankings(
            lexical_pages, dense_pages, k=60, weights=weights
        )[:max_k]
        virtual_chunks, virtual_map = page_chunks(fused_pages, page_tokens)
        metrics = evaluate_rankings(
            virtual_chunks, virtual_map, question["gold_pages"], ks=ks
        )
        rows.append(
            {
                "qid": qid,
                "split": "T",
                "category": question["category"],
                "stratum": question["stratum"],
                "mode": "dual",
                "cell": label,
                **metrics,
                "top_pages": [[doc, page] for doc, page in fused_pages],
            }
        )
        if len(rows) % 10 == 0:
            print(f"[dual] {len(rows)}/{len(questions)}", flush=True)

    with (raw_dir / "dual.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    baseline = [
        json.loads(line)
        for line in (ROOT / "results" / "full-01" / "raw" / "page_first_450.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    baseline = [row for row in baseline if row["mode"] == "hybrid" and row["split"] == "T"]
    dense_baseline = [
        json.loads(line)
        for line in (ROOT / "results" / "full-01" / "raw" / "page_first_128.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    dense_baseline = [
        row for row in dense_baseline if row["mode"] == "dense" and row["split"] == "T"
    ]
    one_to_one = []
    one_to_one_path = (
        ROOT / "results" / "dual-granularity-01" / "raw" / "dual.jsonl"
    )
    if one_to_one_path.is_file() and args.run_id != "dual-granularity-01":
        one_to_one = [
            json.loads(line)
            for line in one_to_one_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    qids = list(questions)
    summary = {
        "run_id": args.run_id,
        "system": label,
        "configuration": {
            "lexical": "page_first_450, top 30",
            "dense": "page_first_128 subchunks, top 30",
            "fusion": (
                f"page-level RRF, k=60, weights dense:lexical "
                f"{dense_weight:g}:{lexical_weight:g}"
            ),
            "injection": "full page text for the top pages",
        },
        "dual": {
            "ndcg@5": round(mean(rows, "ndcg@5"), 6),
            "ndcg@5_ci": [round(value, 6) for value in bootstrap_ci([row["ndcg@5"] for row in rows])],
            "hit@3": round(mean(rows, "hit@3"), 6),
            "hit@5": round(mean(rows, "hit@5"), 6),
            "page_tokens@5": round(mean(rows, "context_tokens@5"), 1),
        },
        "baseline_page_first_450": {
            "ndcg@5": round(mean(baseline, "ndcg@5"), 6),
            "hit@3": round(mean(baseline, "hit@3"), 6),
            "hit@5": round(mean(baseline, "hit@5"), 6),
            "page_tokens@5": round(
                statistics.mean(
                    page_tokens_for(
                        [(doc, page) for doc, page in row["top_pages"][:5]], page_tokens
                    )
                    for row in baseline
                ),
                1,
            ),
        },
        "dense_page_first_128": {
            "ndcg@5": round(mean(dense_baseline, "ndcg@5"), 6),
            "hit@3": round(mean(dense_baseline, "hit@3"), 6),
            "page_tokens@5": round(
                statistics.mean(
                    page_tokens_for(
                        [(doc, page) for doc, page in row["top_pages"][:5]], page_tokens
                    )
                    for row in dense_baseline
                ),
                1,
            ),
        },
        "vs_page_first_450": {
            "ndcg@5": paired(baseline, rows, qids, "ndcg@5"),
            "hit@3": {
                "baseline_only": sum(
                    1
                    for qid in qids
                    if next(r for r in baseline if r["qid"] == qid)["hit@3"]
                    and not next(r for r in rows if r["qid"] == qid)["hit@3"]
                ),
                "dual_only": sum(
                    1
                    for qid in qids
                    if next(r for r in rows if r["qid"] == qid)["hit@3"]
                    and not next(r for r in baseline if r["qid"] == qid)["hit@3"]
                ),
            },
        },
    }
    summary["vs_page_first_450"]["hit@3"]["mcnemar_p"] = round(
        mcnemar_p(
            summary["vs_page_first_450"]["hit@3"]["baseline_only"],
            summary["vs_page_first_450"]["hit@3"]["dual_only"],
        ),
        6,
    )
    if one_to_one:
        one_to_one_by_qid = {row["qid"]: row for row in one_to_one}
        rows_by_qid = {row["qid"]: row for row in rows}
        baseline_only = sum(
            1
            for qid in qids
            if one_to_one_by_qid[qid]["hit@3"] and not rows_by_qid[qid]["hit@3"]
        )
        cell_only = sum(
            1
            for qid in qids
            if rows_by_qid[qid]["hit@3"] and not one_to_one_by_qid[qid]["hit@3"]
        )
        summary["vs_dual_1to1"] = {
            "ndcg@5": paired(one_to_one, rows, qids, "ndcg@5"),
            "hit@3": {
                "baseline_only": baseline_only,
                "cell_only": cell_only,
                "mcnemar_p": round(mcnemar_p(baseline_only, cell_only), 6),
            },
        }

    out = out_dir / "summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {out}")
    page_store.close()
    sub_store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
