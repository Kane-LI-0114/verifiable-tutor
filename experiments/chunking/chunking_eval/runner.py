"""Build one index per chunking cell, evaluate the question set, summarise."""

from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from verifiable_tutor.corpus.chunker import normalize_doc_id

from .index import EvalStore
from .metrics import evaluate_rankings, page_sequence
from .retrieval import DenseSearcher, make_hybrid, search
from .strategies import chunk_pages, chunk_stats, usable_blocks

DEFAULT_KS = (3, 5, 10)
DEFAULT_MODES = ("hybrid", "lexical", "dense")

CELLS: dict[str, dict[str, Any]] = {
    "page_only": {"strategy": "page_only", "max_tokens": None},
    "page_first_128": {"strategy": "page_first", "max_tokens": 128},
    "page_first_256": {"strategy": "page_first", "max_tokens": 256},
    "page_first_450": {"strategy": "page_first", "max_tokens": 450},
    "recursive_128": {"strategy": "recursive", "max_tokens": 128},
    "recursive_256": {"strategy": "recursive", "max_tokens": 256},
    "recursive_450": {"strategy": "recursive", "max_tokens": 450},
    "semantic_450": {"strategy": "semantic", "max_tokens": 450, "threshold": 0.6},
    "cross_page_450": {"strategy": "cross_page", "max_tokens": 450},
}

PILOT_CELLS = (
    "page_only",
    "page_first_128",
    "page_first_450",
    "recursive_256",
    "semantic_450",
)

FULL_CELLS = tuple(CELLS)


def load_pages(directory: str | Path) -> list[dict]:
    pages: list[dict] = []
    for path in sorted(Path(directory).glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    pages.append(json.loads(line))
    return pages


def load_questions(path: str | Path) -> list[dict]:
    questions: list[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            question = json.loads(line)
            question["gold_pages"] = [
                (str(page["doc_id"]), int(page["page_no"]))
                for page in question.get("gold_pages") or []
            ]
            questions.append(question)
    return questions


def validate_questions(
    questions: Sequence[Mapping], pages: Sequence[Mapping]
) -> list[str]:
    errors: list[str] = []
    known: dict[str, set[int]] = {}
    for page in pages:
        known.setdefault(normalize_doc_id(str(page.get("doc_id") or "")), set()).add(
            int(page.get("page_no") or 0)
        )
    seen: set[str] = set()
    for question in questions:
        qid = str(question.get("qid") or "")
        if not qid:
            errors.append("question without qid")
            continue
        if qid in seen:
            errors.append(f"{qid}: duplicate qid")
        seen.add(qid)
        if question.get("split") not in {"D", "T"}:
            errors.append(f"{qid}: split must be D or T")
        if not str(question.get("question") or "").strip():
            errors.append(f"{qid}: empty question")
        gold = question.get("gold_pages") or []
        if not gold:
            errors.append(f"{qid}: no gold pages")
        for doc_id, page_no in gold:
            if doc_id not in known:
                errors.append(f"{qid}: unknown doc_id {doc_id!r}")
            elif page_no not in known[doc_id]:
                errors.append(f"{qid}: unknown page {doc_id} p{page_no}")
    return errors


class VectorCache:
    """Content-addressed float32 vector cache shared by every cell."""

    def __init__(self, path: str | Path, model: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.model = model
        self._connection = sqlite3.connect(self.path)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS vectors ("
            " key TEXT PRIMARY KEY, vector BLOB NOT NULL)"
        )
        self._connection.commit()

    def _key(self, text: str) -> str:
        digest = hashlib.sha256()
        digest.update(self.model.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(text.encode("utf-8"))
        return digest.hexdigest()

    def get_or_embed(
        self, texts: Iterable[str], embedder: Any, *, progress: bool = False
    ) -> dict[str, np.ndarray]:
        unique = list(dict.fromkeys(str(text) for text in texts))
        keys = {text: self._key(text) for text in unique}
        found: dict[str, np.ndarray] = {}
        placeholders = ",".join("?" for _ in unique)
        if unique:
            rows = self._connection.execute(
                f"SELECT key, vector FROM vectors WHERE key IN ({placeholders})",
                list(keys.values()),
            ).fetchall()
            by_key = {row[0]: row[1] for row in rows}
            for text in unique:
                blob = by_key.get(keys[text])
                if blob is not None:
                    found[text] = np.frombuffer(blob, dtype=np.float32)
        missing = [text for text in unique if text not in found]
        if missing:
            if progress:
                print(f"  embedding {len(missing)} new texts", flush=True)
            # Sort by character length so a batch is not padded to the longest
            # chunk in the whole set. This roughly halves the CPU time.
            missing.sort(key=len)
            batch_size = 16
            for start in range(0, len(missing), batch_size):
                batch = missing[start : start + batch_size]
                vectors = embedder.embed(batch)
                for text, vector in zip(batch, vectors):
                    array = np.asarray(vector, dtype=np.float32)
                    found[text] = array
                    self._connection.execute(
                        "INSERT OR REPLACE INTO vectors(key, vector) VALUES(?, ?)",
                        (keys[text], array.tobytes()),
                    )
                self._connection.commit()
                if progress and (start // batch_size) % 5 == 0:
                    done = min(start + batch_size, len(missing))
                    print(f"    {done}/{len(missing)}", flush=True)
        return found

    def close(self) -> None:
        self._connection.close()


def embed_chunks(
    chunks: Sequence[Mapping], embedder: Any, cache: VectorCache
) -> dict[str, np.ndarray]:
    texts = [str(chunk.get("embed_text") or chunk["text"]) for chunk in chunks]
    vectors = cache.get_or_embed(texts, embedder, progress=True)
    return {
        str(chunk["chunk_id"]): vectors[str(chunk.get("embed_text") or chunk["text"])]
        for chunk in chunks
    }


def build_block_lookup(
    pages: Sequence[Mapping], embedder: Any, cache: VectorCache
) -> dict[str, np.ndarray]:
    texts = [
        str(block.get("content") or "").strip()
        for page in pages
        for block in usable_blocks(page)
        if str(block.get("content") or "").strip()
    ]
    return cache.get_or_embed(texts, embedder, progress=True)


def build_cell(
    name: str,
    pages: Sequence[Mapping],
    embedder: Any,
    cache: VectorCache,
    index_dir: str | Path,
    *,
    threshold: float | None = None,
    config_override: Mapping[str, Any] | None = None,
) -> tuple[EvalStore, list[dict], dict, dict]:
    config = dict(config_override or CELLS[name])
    if threshold is not None:
        config["threshold"] = threshold
    strategy = config["strategy"]
    vector_lookup = None
    if strategy == "semantic":
        vector_lookup = build_block_lookup(pages, embedder, cache)
        chunks = chunk_pages(
            pages,
            strategy,
            max_tokens=config["max_tokens"],
            threshold=float(config.get("threshold", 0.6)),
            vector_lookup=vector_lookup,
        )
    else:
        chunks = chunk_pages(
            pages,
            strategy,
            max_tokens=config.get("max_tokens"),
        )

    db_path = Path(index_dir) / f"{name}.db"
    if db_path.exists():
        db_path.unlink()
    store = EvalStore(db_path)
    store.add_chunks(chunks)

    vectors = embed_chunks(chunks, embedder, cache)
    by_doc: dict[str, dict[str, bytes]] = {}
    for chunk in chunks:
        chunk_id = str(chunk["chunk_id"])
        by_doc.setdefault(str(chunk["doc_id"]), {})[chunk_id] = vectors[chunk_id].tobytes()
    built_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    for doc_id, doc_vectors in by_doc.items():
        store.set_embeddings(doc_id, doc_vectors, model=cache.model, built_at=built_at)

    stats = chunk_stats(chunks)
    stats["config"] = config
    stats["index_state"] = store.index_state()
    return store, chunks, store.page_map(), stats


def evaluate_cell(
    store: EvalStore,
    embedder: Any,
    questions: Sequence[Mapping],
    *,
    cell: str,
    modes: Sequence[str],
    ks: Sequence[int],
    weights: tuple[float, float] = (1.0, 1.0),
) -> list[dict]:
    page_map = store.page_map()
    max_k = max(ks)
    dense = DenseSearcher(store, embedder) if "dense" in modes else None
    hybrid = (
        make_hybrid(store, embedder, weights=weights) if "hybrid" in modes else None
    )
    rows: list[dict] = []
    for question in questions:
        gold = question["gold_pages"]
        for mode in modes:
            hits = search(
                store,
                embedder,
                str(question["question"]),
                mode=mode,
                k=max_k,
                dense=dense,
                hybrid=hybrid,
                weights=weights,
            )
            metadata = {
                item["chunk_id"]: item
                for item in store.get_chunks([hit["chunk_id"] for hit in hits])
            }
            for hit in hits:
                source = metadata.get(hit["chunk_id"], {})
                hit["token_estimate"] = source.get("token_estimate", 0)
            metrics = evaluate_rankings(hits, page_map, gold, ks=ks)
            rows.append(
                {
                    "cell": cell,
                    "qid": question["qid"],
                    "split": question["split"],
                    "category": question["category"],
                    "stratum": question["stratum"],
                    "mode": mode,
                    **metrics,
                    "top_pages": [
                        [doc_id, page_no]
                        for doc_id, page_no in page_sequence(hits, page_map)[:max_k]
                    ],
                }
            )
    return rows


def bootstrap_ci(
    values: Sequence[float], *, samples: int = 2000, seed: int = 42
) -> list[float]:
    if not values:
        return [0.0, 0.0]
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        means.append(
            sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        )
    means.sort()
    return [means[int(0.025 * len(means))], means[int(0.975 * len(means)) - 1]]


def mcnemar_p(baseline_only: int, cell_only: int) -> float:
    total = baseline_only + cell_only
    if total == 0:
        return 1.0
    tail = sum(math.comb(total, index) for index in range(min(baseline_only, cell_only) + 1))
    return min(1.0, 2.0 * tail / (2.0**total))


def _metric_keys(ks: Sequence[int]) -> list[str]:
    keys = ["mrr"]
    for k in ks:
        keys.extend([f"hit@{k}", f"ndcg@{k}", f"context_tokens@{k}"])
    return keys


def summarise(
    rows: Sequence[Mapping],
    cell_stats: Mapping[str, Mapping],
    *,
    ks: Sequence[int],
    modes: Sequence[str],
    baseline: str = "page_only",
) -> dict:
    keys = _metric_keys(ks)
    by_group: dict[tuple[str, str, str], list[Mapping]] = {}
    for row in rows:
        by_group.setdefault((row["split"], row["mode"], row.get("cell", "")), []).append(row)

    summary: dict[str, Any] = {
        "baseline": baseline,
        "ks": list(ks),
        "modes": list(modes),
        "cells": {name: dict(stats) for name, stats in cell_stats.items()},
        "groups": {},
        "comparisons": [],
    }

    for (split, mode, cell), group in by_group.items():
        if not cell:
            continue
        entry: dict[str, Any] = {
            "questions": len(group),
            "metrics": {},
        }
        for key in keys:
            values = [float(row[key]) for row in group if key in row]
            if not values:
                continue
            entry["metrics"][key] = {
                "mean": round(statistics.mean(values), 6),
                "median": round(statistics.median(values), 6),
                "ci": [round(value, 6) for value in bootstrap_ci(values)],
            }
        summary["groups"][f"{split}/{mode}/{cell}"] = entry

    for split in ("D", "T"):
        for mode in modes:
            baseline_rows = {
                row["qid"]: row
                for row in rows
                if row.get("cell") == baseline and row["split"] == split and row["mode"] == mode
            }
            if not baseline_rows:
                continue
            for cell in cell_stats:
                if cell == baseline:
                    continue
                cell_rows = {
                    row["qid"]: row
                    for row in rows
                    if row.get("cell") == cell and row["split"] == split and row["mode"] == mode
                }
                common = sorted(set(baseline_rows) & set(cell_rows))
                if not common:
                    continue
                comparison: dict[str, Any] = {
                    "split": split,
                    "mode": mode,
                    "cell": cell,
                    "baseline": baseline,
                    "questions": len(common),
                    "metrics": {},
                }
                for k in ks:
                    key = f"ndcg@{k}"
                    deltas = [
                        float(cell_rows[qid][key]) - float(baseline_rows[qid][key])
                        for qid in common
                    ]
                    wins = sum(delta > 1e-12 for delta in deltas)
                    losses = sum(delta < -1e-12 for delta in deltas)
                    ties = len(deltas) - wins - losses
                    comparison["metrics"][key] = {
                        "mean_delta": round(statistics.mean(deltas), 6),
                        "ci": [round(value, 6) for value in bootstrap_ci(deltas)],
                        "wins": wins,
                        "ties": ties,
                        "losses": losses,
                    }
                    hit_key = f"hit@{k}"
                    baseline_only = sum(
                        1
                        for qid in common
                        if baseline_rows[qid][hit_key] and not cell_rows[qid][hit_key]
                    )
                    cell_only = sum(
                        1
                        for qid in common
                        if cell_rows[qid][hit_key] and not baseline_rows[qid][hit_key]
                    )
                    comparison["metrics"][hit_key] = {
                        "baseline_only": baseline_only,
                        "cell_only": cell_only,
                        "mcnemar_p": round(mcnemar_p(baseline_only, cell_only), 6),
                    }
                    token_key = f"context_tokens@{k}"
                    token_deltas = [
                        float(cell_rows[qid][token_key])
                        - float(baseline_rows[qid][token_key])
                        for qid in common
                    ]
                    comparison["metrics"][token_key] = {
                        "mean_delta": round(statistics.mean(token_deltas), 1),
                    }
                summary["comparisons"].append(comparison)
    return summary


def format_table(summary: Mapping) -> str:
    lines = []
    for split in ("T", "D"):
        lines.append(f"split={split}")
        for mode in summary.get("modes") or []:
            lines.append(f"  mode={mode}")
            for cell in summary.get("cells") or {}:
                group = summary["groups"].get(f"{split}/{mode}/{cell}")
                if not group:
                    continue
                metrics = group["metrics"]
                ndcg = metrics.get("ndcg@5", {}).get("mean", float("nan"))
                hit = metrics.get("hit@3", {}).get("mean", float("nan"))
                tokens = metrics.get("context_tokens@5", {}).get("mean", float("nan"))
                lines.append(
                    f"    {cell:20s} ndcg@5={ndcg:.4f} hit@3={hit:.3f} tokens@5={tokens:.0f}"
                )
    return "\n".join(lines)
