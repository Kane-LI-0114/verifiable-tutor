"""List the questions one cell fails and the pages it returned instead."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir")
    parser.add_argument("--cell", required=True)
    parser.add_argument("--mode", default="hybrid")
    parser.add_argument("--split", default="T")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--questions", default=str(ROOT / "questions" / "retrieval_v1.jsonl")
    )
    args = parser.parse_args()

    questions = {}
    with Path(args.questions).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                item = json.loads(line)
                questions[item["qid"]] = item

    rows = []
    path = Path(args.raw_dir) / f"{args.cell}.jsonl"
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["mode"] == args.mode and row["split"] == args.split:
                rows.append(row)

    failures = [row for row in rows if float(row["ndcg@5"]) <= args.threshold]
    failures.sort(key=lambda row: (row["ndcg@5"], row["qid"]))
    print(f"{len(failures)} of {len(rows)} questions at or below nDCG@5 {args.threshold}")
    print("| qid | category | stratum | nDCG@5 | gold | top pages |")
    print("|---|---|---|---:|---|---|")
    for row in failures:
        question = questions.get(row["qid"], {})
        gold = ", ".join(
            f"{page['doc_id']} p{page['page_no']}"
            for page in question.get("gold_pages", [])
        )
        top = ", ".join(f"{doc} p{page}" for doc, page in row["top_pages"][:5])
        print(
            f"| {row['qid']} | {row['category']} | {row['stratum']} | "
            f"{row['ndcg@5']:.3f} | {gold} | {top} |"
        )

    print()
    for key in ("category", "stratum"):
        counts = {}
        for row in failures:
            counts[row[key]] = counts.get(row[key], 0) + 1
        print(key, counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
