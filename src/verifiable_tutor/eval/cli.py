"""Command-line entry point for RQ2 self-test metrics.

Usage:
    python -m verifiable_tutor.eval.cli rq2a <run-dir> --expected-points N
    python -m verifiable_tutor.eval.cli rq2b <run-dir> --grader a|b

Each command reads the JSONL files of one run directory, computes the metrics,
writes ``metrics.json`` beside them, and prints the result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import metrics
from .loader import build_max_scores, load_jsonl


def compute_rq2a(run_dir: str | Path, expected_points: int) -> dict[str, Any]:
    run = Path(run_dir)
    annotations = load_jsonl(run / "annotations.jsonl")
    questions = load_jsonl(run / "system-a.jsonl")
    return {
        "run_id": run.name,
        "knowledge_point_coverage": metrics.knowledge_point_coverage(
            annotations, expected_points
        ),
        "question_validity_rate": metrics.question_validity_rate(annotations),
        "reference_answer_verifiability": metrics.reference_answer_verifiability(
            questions
        ),
        "citation_validity": metrics.citation_validity(questions),
    }


def compute_rq2b(run_dir: str | Path, grader: str) -> dict[str, Any]:
    run = Path(run_dir)
    questions = load_jsonl(run / "questions.jsonl")
    ground_truth = load_jsonl(run / "ground_truth.jsonl")
    grades = load_jsonl(run / f"system-{grader}-grades.jsonl")
    max_scores = build_max_scores(questions)
    return {
        "run_id": run.name,
        "grader": grader,
        "exact_match_rate": metrics.exact_match_rate(grades, ground_truth),
        "within_one_point_agreement": metrics.within_one_point_agreement(
            grades, ground_truth
        ),
        "normalized_mae": metrics.normalized_mae(grades, ground_truth, max_scores),
        "false_pass_rate": metrics.false_pass_rate(grades, ground_truth, max_scores),
        "false_fail_rate": metrics.false_fail_rate(grades, ground_truth, max_scores),
    }


def _write(result: dict[str, Any], run_dir: str | Path) -> None:
    path = Path(run_dir) / "metrics.json"
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute RQ2 self-test metrics.")
    sub = parser.add_subparsers(dest="command", required=True)

    rq2a = sub.add_parser("rq2a", help="generation quality metrics")
    rq2a.add_argument("run_dir", help="generation/<run-id> directory")
    rq2a.add_argument("--expected-points", type=int, default=0)

    rq2b = sub.add_parser("rq2b", help="grading agreement metrics")
    rq2b.add_argument("run_dir", help="grading_shared/<run-id> directory")
    rq2b.add_argument("--grader", choices=["a", "b"], default="a")

    args = parser.parse_args(argv)
    if args.command == "rq2a":
        result = compute_rq2a(args.run_dir, args.expected_points)
    else:
        result = compute_rq2b(args.run_dir, args.grader)
    _write(result, args.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
