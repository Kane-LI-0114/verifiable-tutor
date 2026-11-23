"""JSONL loading helpers for the RQ2 benchmark data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read one JSON-object-per-line file into a list of dicts."""

    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build_max_scores(questions: list[dict[str, Any]]) -> dict[str, float]:
    """Map question id to its maximum score, from a shared question set."""

    return {q["question_id"]: q["max_score"] for q in questions}
