"""Store one graded practice attempt and its knowledge-point progress."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ..storage import Storage

__all__ = ["UnknownQuestionError", "submit_attempt"]


class UnknownQuestionError(ValueError):
    """An answer or result names a question the session does not contain."""


def submit_attempt(
    *,
    storage: Storage,
    session_id: str,
    topic: str,
    questions: Sequence[Mapping[str, Any]],
    attempt_no: int,
    answers: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    user_id: str,
    submitted_at: datetime,
) -> None:
    """Store the scores and let attempt one write the topic progress.

    The browser grades objective questions and the model grades open and code
    answers, so the caller passes stored results. This function normalizes
    them, writes the attempt, and records mastery only from attempt one.
    """

    known = {question["id"] for question in questions}
    unknown = (set(answers) | set(results)) - known
    if unknown:
        raise UnknownQuestionError(
            f"unknown question ids: {', '.join(sorted(unknown))}"
        )

    normalized: dict[str, dict[str, Any]] = {}
    for question in questions:
        stored = results.get(question["id"])
        normalized[question["id"]] = {
            "score": float(stored["score"]) if stored is not None else 0.0,
            "max_score": float(question["max_score"]),
            "explanation": stored.get("explanation", "") if stored else "",
        }

    storage.submit_practice_attempt(
        conversation_id=session_id,
        attempt_no=attempt_no,
        answers=answers,
        results=normalized,
        submitted_at=submitted_at,
    )

    if attempt_no != 1:
        return
    by_topic: dict[str, dict[str, set[str]]] = {}
    for question in questions:
        question_topic = question.get("topic") or topic
        entry = by_topic.setdefault(
            question_topic, {"covered": set(), "mastered": set()}
        )
        entry["covered"].update(question.get("knowledge_points") or [])
        if normalized[question["id"]]["score"] >= float(question["max_score"]):
            entry["mastered"].update(question.get("knowledge_points") or [])
    for question_topic, entry in by_topic.items():
        storage.record_progress(
            user_id=user_id,
            topic=question_topic,
            covered_points=sorted(entry["covered"]),
            mastered_points=sorted(entry["mastered"]),
        )
