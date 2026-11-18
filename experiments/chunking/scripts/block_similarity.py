"""Describe adjacent-block cosine similarity to choose a semantic threshold."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = "BAAI/bge-m3"


def key(text: str) -> str:
    digest = hashlib.sha256()
    digest.update(MODEL.encode())
    digest.update(b"\x00")
    digest.update(text.encode())
    return digest.hexdigest()


def main() -> int:
    from chunking_eval.strategies import usable_blocks

    connection = sqlite3.connect(ROOT / "data" / "cache" / "vectors.db")
    vectors = {}
    for row_key, blob in connection.execute("SELECT key, vector FROM vectors"):
        vectors[row_key] = np.frombuffer(blob, dtype=np.float32)
    connection.close()

    similarities = []
    for path in sorted((ROOT / "data" / "pages").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            page = json.loads(line)
            blocks = usable_blocks(page)
            for left, right in zip(blocks, blocks[1:]):
                left_text = str(left.get("content") or "").strip()
                right_text = str(right.get("content") or "").strip()
                left_vector = vectors.get(key(left_text))
                right_vector = vectors.get(key(right_text))
                if left_vector is None or right_vector is None:
                    continue
                if len(left_vector) != len(right_vector):
                    continue
                similarities.append(float(np.dot(left_vector, right_vector)))

    similarities.sort()
    print("pairs", len(similarities))
    for quantile in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95):
        print(f"p{int(quantile * 100):02d}", round(similarities[int(quantile * len(similarities))], 4))
    for threshold in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70):
        share = sum(1 for value in similarities if value < threshold) / len(similarities)
        print(f"below {threshold:.2f}: {share:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
