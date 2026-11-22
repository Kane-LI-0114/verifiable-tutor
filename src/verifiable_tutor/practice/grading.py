"""Deterministic grading for self-test answers (VT-17, FR-E5).

Single choice, multiple choice, and true or false are graded by exact
comparison, no model call. Short answer and code grading live elsewhere:
short answer is rubric based, code is test-result based (TACC exec).
"""

from __future__ import annotations


def grade_single_choice(student: str, reference: str) -> bool:
    """Return True when the chosen answer equals the reference (case-insensitive)."""

    return student.strip().lower() == reference.strip().lower()


def grade_multiple_choice(student: list[str], reference: list[str]) -> bool:
    """Return True when the selected set equals the reference set (order-insensitive)."""

    return set(student) == set(reference)


def grade_true_false(student: bool, reference: bool) -> bool:
    """Return True when the boolean answer matches the reference."""

    return student == reference
