"""Render Markdown tables from a summary.json and its raw per-question rows."""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def fmt(value, digits=4):
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def cell_table(summary):
    lines = [
        "| Cell | Chunks | Mean tokens | Median | Max | Oversize | Multi-page | Budget |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cell, stats in summary.get("cells", {}).items():
        config = stats.get("config", {})
        lines.append(
            "| {cell} | {chunks} | {mean} | {median} | {max} | {oversize} | {multi} | {budget} |".format(
                cell=cell,
                chunks=stats.get("chunks", "-"),
                mean=fmt(stats.get("mean_tokens"), 1),
                median=stats.get("median_tokens", "-"),
                max=stats.get("max_tokens", "-"),
                oversize=stats.get("oversize", "-"),
                multi=stats.get("multi_page", "-"),
                budget=config.get("max_tokens") or "-",
            )
        )
    return "\n".join(lines)


def metrics_table(summary, split, mode):
    lines = [
        "| Cell | nDCG@5 (95% CI) | hit@3 | hit@5 | MRR | tokens@5 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cell in summary.get("cells", {}):
        group = summary.get("groups", {}).get(f"{split}/{mode}/{cell}")
        if not group:
            continue
        metrics = group.get("metrics", {})
        ndcg = metrics.get("ndcg@5", {})
        ci = ndcg.get("ci") or [None, None]
        lines.append(
            "| {cell} | {mean} [{low}, {high}] | {hit3} | {hit5} | {mrr} | {tokens} |".format(
                cell=cell,
                mean=fmt(ndcg.get("mean")),
                low=fmt(ci[0] if len(ci) > 0 else None),
                high=fmt(ci[1] if len(ci) > 1 else None),
                hit3=fmt(metrics.get("hit@3", {}).get("mean"), 3),
                hit5=fmt(metrics.get("hit@5", {}).get("mean"), 3),
                mrr=fmt(metrics.get("mrr", {}).get("mean"), 3),
                tokens=fmt(metrics.get("context_tokens@5", {}).get("mean"), 0),
            )
        )
    return "\n".join(lines)


def comparison_table(summary, split, mode):
    lines = [
        "| Cell | ΔnDCG@5 (95% CI) | W/T/L | McNemar p (hit@5) | Δtokens@5 |",
        "|---|---:|---:|---:|---:|",
    ]
    for comparison in summary.get("comparisons", []):
        if comparison["split"] != split or comparison["mode"] != mode:
            continue
        metrics = comparison["metrics"]
        ndcg = metrics.get("ndcg@5", {})
        ci = ndcg.get("ci") or [None, None]
        hit = metrics.get("hit@5", {})
        tokens = metrics.get("context_tokens@5", {})
        lines.append(
            "| {cell} | {delta} [{low}, {high}] | {wins}/{ties}/{losses} | {p} | {tokens} |".format(
                cell=comparison["cell"],
                delta=fmt(ndcg.get("mean_delta")),
                low=fmt(ci[0] if len(ci) > 0 else None),
                high=fmt(ci[1] if len(ci) > 1 else None),
                wins=ndcg.get("wins", 0),
                ties=ndcg.get("ties", 0),
                losses=ndcg.get("losses", 0),
                p=fmt(hit.get("mcnemar_p"), 4),
                tokens=fmt(tokens.get("mean_delta"), 1),
            )
        )
    return "\n".join(lines)


def raw_table(raw_dir, split, mode, field="category"):
    files = sorted(Path(raw_dir).glob("*.jsonl"))
    rows = []
    for path in files:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    grouped = defaultdict(list)
    for row in rows:
        if row["split"] != split or row["mode"] != mode:
            continue
        grouped[(row[field], row["cell"])].append(float(row["ndcg@5"]))
    cells = sorted({cell for _, cell in grouped})
    groups = sorted({group for group, _ in grouped})
    lines = [
        f"| {field.title()} | " + " | ".join(cells) + " |",
        "|---|" + "---:|" * len(cells),
    ]
    for group in groups:
        values = [
            fmt(statistics.mean(grouped[(group, cell)]), 3)
            if grouped.get((group, cell))
            else "-"
            for cell in cells
        ]
        lines.append("| " + group + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def main(argv):
    if not argv:
        print("usage: report.py <summary.json> [raw_dir]")
        return 2
    summary_path = Path(argv[0])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    raw_dir = Path(argv[1]) if len(argv) > 1 else summary_path.parent / "raw"

    print("## Cell configuration and chunk statistics\n")
    print(cell_table(summary))
    for mode in summary.get("modes", []):
        print(f"\n## Test metrics, {mode} retrieval\n")
        print(metrics_table(summary, "T", mode))
        print(f"\n## Paired comparison against page_only, {mode} retrieval\n")
        print(comparison_table(summary, "T", mode))
    if raw_dir.exists():
        print("\n## Test nDCG@5 by question category, hybrid retrieval\n")
        print(raw_table(raw_dir, "T", "hybrid", "category"))
        print("\n## Test nDCG@5 by page-length stratum, hybrid retrieval\n")
        print(raw_table(raw_dir, "T", "hybrid", "stratum"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
