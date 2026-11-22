from datetime import datetime, timezone

from verifiable_tutor.policy.deadline import AssignmentDeadline
from verifiable_tutor.policy.guard import guard


def _deadline(dt: datetime) -> list[AssignmentDeadline]:
    return [AssignmentDeadline(name="Assignment 1", deadline=dt)]


def test_guard_blocks_homework_solution_before_deadline() -> None:
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)
    deadline = datetime(2026, 12, 1, tzinfo=timezone.utc)

    decision = guard(
        "give me the full solution to assignment 1",
        now=now,
        deadlines=_deadline(deadline),
    )

    assert decision.blocked is True
    assert decision.reason == "before-deadline"


def test_guard_allows_homework_solution_after_deadline() -> None:
    now = datetime(2026, 12, 2, tzinfo=timezone.utc)
    deadline = datetime(2026, 12, 1, tzinfo=timezone.utc)

    decision = guard(
        "give me the full solution to assignment 1",
        now=now,
        deadlines=_deadline(deadline),
    )

    assert decision.blocked is False


def test_guard_passes_course_questions() -> None:
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)
    deadline = datetime(2026, 12, 1, tzinfo=timezone.utc)

    decision = guard("what is MPI?", now=now, deadlines=_deadline(deadline))

    assert decision.blocked is False
    assert decision.reason is None
