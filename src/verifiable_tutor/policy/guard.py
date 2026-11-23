"""Disclosure guard: refuse complete homework solutions before the deadline.

The guard runs the VT-01 intent classifier and, when the message is a homework
solution request, blocks it only for the assignment whose deadline is still in
the future. An assignment whose deadline has passed is taught in full.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .deadline import (
    AssignmentDeadline,
    find_deadline,
    identify_assignment_number,
    is_before_deadline,
)
from .intent import classify_intent


@dataclass(frozen=True)
class GuardDecision:
    """One disclosure decision for a user message."""

    blocked: bool
    reason: str | None


def guard(
    message: str,
    *,
    now: datetime,
    deadlines: list[AssignmentDeadline],
) -> GuardDecision:
    """Decide whether to block a user message.

    A homework solution request is blocked only for the assignment named in
    the message whose deadline is still ahead. When no assignment is named,
    the request is refused while any deadline is still ahead.
    """

    decision = classify_intent(message)
    if decision.intent != "homework_solution_request":
        return GuardDecision(blocked=False, reason=None)

    number = identify_assignment_number(message)
    if number is not None:
        deadline = find_deadline(number, deadlines)
        if deadline is not None and now < deadline.deadline:
            return GuardDecision(blocked=True, reason="before-deadline")
        return GuardDecision(blocked=False, reason=None)

    # No specific assignment named: refuse while any deadline is still ahead.
    if is_before_deadline(now, deadlines):
        return GuardDecision(blocked=True, reason="before-deadline")
    return GuardDecision(blocked=False, reason=None)
