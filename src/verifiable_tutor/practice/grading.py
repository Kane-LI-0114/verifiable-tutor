"""Grading for self-test answers (VT-17, FR-E5).

Single choice, multiple choice, and true or false are graded by exact
comparison, no model call. Short answer and code answers are graded by an
online model (DeepSeek) against the reference answer and scoring points; no
TACC execution is required.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ..prompts import load_prompt


def grade_single_choice(student: str, reference: str) -> bool:
    """Return True when the chosen answer equals the reference (case-insensitive)."""

    return student.strip().lower() == reference.strip().lower()


def grade_multiple_choice(student: list[str], reference: list[str]) -> bool:
    """Return True when the selected set equals the reference set (order-insensitive)."""

    return set(student) == set(reference)


def grade_true_false(student: bool, reference: bool) -> bool:
    """Return True when the boolean answer matches the reference."""

    return student == reference


@dataclass(frozen=True)
class GradingResult:
    """One model-graded answer."""

    score: float
    max_score: float
    explanation: str


def _build_grading_message(
    question: str,
    student_answer: str,
    reference_answer: str,
    scoring_points: list[str],
    max_score: float,
) -> str:
    points = "\n".join(f"- {point}" for point in scoring_points)
    return (
        "Question:\n" + question + "\n\n"
        "Student answer:\n" + student_answer + "\n\n"
        "Reference answer:\n" + reference_answer + "\n\n"
        "Scoring points (maximum score "
        + str(max_score)
        + "):\n" + points + "\n\n"
        "Grade the answer and return the JSON object."
    )


def _parse_grade(text: str) -> GradingResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    return GradingResult(
        score=float(data["score"]),
        max_score=float(data["max_score"]),
        explanation=str(data.get("explanation", "")),
    )


def grade_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    scoring_points: list[str],
    max_score: float,
    adapter: Any,
    *,
    provider: str = "deepseek",
    tier: str = "flash",
) -> GradingResult:
    """Grade one answer with an online model against the scoring points.

    The adapter is a seam: production passes the project model adapter, tests
    pass a fake. The model returns one JSON object with ``score``,
    ``max_score``, and ``explanation``.
    """

    message = _build_grading_message(
        question, student_answer, reference_answer, scoring_points, max_score
    )
    result = adapter.chat(
        [
            {"role": "system", "content": load_prompt("grading")},
            {"role": "user", "content": message},
        ],
        provider=provider,
        tier=tier,
        temperature=0.0,
    )
    return _parse_grade(result.text)
