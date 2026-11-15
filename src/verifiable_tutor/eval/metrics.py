"""RQ2 metric computation for the self-test benchmark.

Every function here is a pure seam: it takes decoded JSONL records (lists of
dicts) and returns a number, or ``None`` when the metric has no applicable
items. The field shapes are owned by docs/benchmark-schema.md.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


# --- RQ2a: generation quality -------------------------------------------


def question_validity_rate(annotations: Iterable[Mapping]) -> float:
    """Share of annotated questions marked valid."""
    items = list(annotations)
    return _rate(sum(1 for a in items if a.get("valid")), len(items))


def knowledge_point_coverage(
    annotations: Iterable[Mapping], expected_points: int
) -> float:
    """Distinct covered knowledge points divided by the expected count."""
    if expected_points <= 0:
        return 0.0
    covered = {
        point
        for annotation in annotations
        for point in annotation.get("knowledge_points", [])
    }
    return len(covered) / expected_points


def reference_answer_verifiability(questions: Iterable[Mapping]) -> float:
    """Share of questions whose reference answer is verified, among applicable."""
    applicable = [
        q for q in questions if q.get("reference_verified") is not None
    ]
    return _rate(
        sum(1 for q in applicable if q["reference_verified"]), len(applicable)
    )


def citation_validity(questions: Iterable[Mapping]) -> float | None:
    """Share of cited questions whose citation passed the span verifier.

    Returns ``None`` when no question carries a verification result, because
    the share is then undefined rather than zero.
    """

    cited = [q for q in questions if q.get("citation_verified") is not None]
    if not cited:
        return None
    return _rate(sum(1 for q in cited if q["citation_verified"]), len(cited))


# --- RQ2b: grading agreement --------------------------------------------


def _join(
    grades: Iterable[Mapping], ground_truth: Iterable[Mapping]
) -> list[tuple[Mapping, Mapping]]:
    """Pair grades with ground truth by (question_id, variant)."""

    index = {
        (g["question_id"], g["variant"]): g for g in ground_truth
    }
    return [
        (grade, index[key])
        for grade in grades
        if (key := (grade["question_id"], grade["variant"])) in index
    ]


def exact_match_rate(
    grades: Iterable[Mapping], ground_truth: Iterable[Mapping]
) -> float:
    pairs = _join(grades, ground_truth)
    return _rate(
        sum(1 for grade, truth in pairs if grade["score"] == truth["score"]),
        len(pairs),
    )


def within_one_point_agreement(
    grades: Iterable[Mapping], ground_truth: Iterable[Mapping]
) -> float:
    pairs = _join(grades, ground_truth)
    return _rate(
        sum(1 for grade, truth in pairs if abs(grade["score"] - truth["score"]) <= 1.0),
        len(pairs),
    )


def normalized_mae(
    grades: Iterable[Mapping],
    ground_truth: Iterable[Mapping],
    max_scores: Mapping,
) -> float:
    """Mean absolute error, normalized per item by its maximum score."""

    pairs = _join(grades, ground_truth)
    errors = [
        abs(grade["score"] - truth["score"]) / max_scores[grade["question_id"]]
        for grade, truth in pairs
        if max_scores.get(grade["question_id"], 0) > 0
    ]
    return sum(errors) / len(errors) if errors else 0.0


def false_pass_rate(
    grades: Iterable[Mapping],
    ground_truth: Iterable[Mapping],
    max_scores: Mapping,
) -> float:
    """Share of fully-wrong answers (ground truth 0) scored as fully correct."""

    pairs = _join(grades, ground_truth)
    wrong = [
        (grade, truth)
        for grade, truth in pairs
        if truth["score"] == 0
    ]
    return _rate(
        sum(
            1
            for grade, _ in wrong
            if grade["score"] == max_scores.get(grade["question_id"], 0)
        ),
        len(wrong),
    )


def false_fail_rate(
    grades: Iterable[Mapping],
    ground_truth: Iterable[Mapping],
    max_scores: Mapping,
) -> float:
    """Share of fully-correct answers (ground truth max) scored as fully wrong."""

    pairs = _join(grades, ground_truth)
    correct = [
        (grade, truth)
        for grade, truth in pairs
        if truth["score"] == max_scores.get(grade["question_id"], 0)
    ]
    return _rate(
        sum(1 for grade, _ in correct if grade["score"] == 0), len(correct)
    )
