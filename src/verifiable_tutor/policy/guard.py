"""Disclosure guard: refuse complete homework solutions before the deadline.

The guard runs the VT-01 intent classifier and, when the message is a homework
solution request, blocks it while any assignment deadline is still in the
future. After the deadline it lets the request through for full teaching.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .deadline import AssignmentDeadline, is_before_deadline
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

    A homework solution request is blocked before the deadline and allowed
    after it. Every other intent passes through.
    """

    decision = classify_intent(message)
    if decision.intent == "homework_solution_request" and is_before_deadline(
        now, deadlines
    ):
        return GuardDecision(blocked=True, reason="before-deadline")
    return GuardDecision(blocked=False, reason=None)
