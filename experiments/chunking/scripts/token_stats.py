"""Measure the real BGE-M3 token length of every chunk in a run.

The chunker estimates tokens as CJK characters plus one token per four other
characters. BGE-M3 uses its own tokenizer and truncates at 512 tokens, so this
script reports the real length distribution and the truncation rate per cell.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", help="results/<run>/summary.json")
    parser.add_argument("--model", default=str(ROOT / "models" / "bge-m3"))
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    from transformers import AutoTokenizer

    summary_path = Path(args.summary)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    index_dir = ROOT / "data" / "index"
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    import sqlite3

    stats = {}
    for cell in summary.get("cells", {}):
        path = index_dir / f"{cell}.db"
        if not path.is_file():
            continue
        connection = sqlite3.connect(path)
        texts = [row[0] for row in connection.execute("SELECT text FROM eval_chunks")]
        connection.close()
        lengths = [
            len(tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"])
            for text in texts
        ]
        lengths.sort()
        stats[cell] = {
            "chunks": len(lengths),
            "mean": round(statistics.mean(lengths), 1) if lengths else 0,
            "median": lengths[len(lengths) // 2] if lengths else 0,
            "p90": lengths[int(0.9 * len(lengths))] if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "over_512": sum(1 for value in lengths if value > 512),
            "over_512_pct": round(
                100.0 * sum(1 for value in lengths if value > 512) / len(lengths), 2
            )
            if lengths
            else 0.0,
        }
        print(
            f"{cell:20s} chunks={stats[cell]['chunks']:4d} "
            f"mean={stats[cell]['mean']:6.1f} p90={stats[cell]['p90']:4d} "
            f"max={stats[cell]['max']:4d} over512={stats[cell]['over_512_pct']:5.2f}%"
        )

    out = Path(args.out) if args.out else summary_path.parent / "bge_token_stats.json"
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
