"""Summarise the question set and the gold-page token lengths."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    from chunking_eval.strategies import estimate_tokens, usable_blocks

    pages = {}
    for path in sorted((ROOT / "data" / "pages").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                page = json.loads(line)
                pages[(page["doc_id"], page["page_no"])] = page

    questions = []
    for line in (ROOT / "questions" / "retrieval_v1.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            questions.append(json.loads(line))

    print("questions", len(questions))
    print("split", Counter(item["split"] for item in questions))
    print("category", Counter(item["category"] for item in questions))
    print("stratum", Counter(item["stratum"] for item in questions))
    print(
        "gold pages per question",
        Counter(len(item["gold_pages"]) for item in questions),
    )

    tokens = []
    for item in questions:
        for gold in item["gold_pages"]:
            page = pages[(gold["doc_id"], gold["page_no"])]
            tokens.append(
                sum(
                    estimate_tokens(str(block.get("content") or ""))
                    for block in usable_blocks(page)
                )
            )
    tokens.sort()
    print(
        "gold page tokens: min={} median={} mean={} p90={} max={}".format(
            min(tokens),
            statistics.median(tokens),
            round(statistics.mean(tokens), 1),
            tokens[int(0.9 * len(tokens))],
            max(tokens),
        )
    )
    print("gold pages under 128 tokens", sum(1 for value in tokens if value < 128))
    print("gold pages 128-249", sum(1 for value in tokens if 128 <= value < 250))
    print("gold pages 250+", sum(1 for value in tokens if value >= 250))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
