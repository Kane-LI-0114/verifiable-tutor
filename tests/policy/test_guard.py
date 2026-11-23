from datetime import datetime, timezone

from verifiable_tutor.policy.deadline import AssignmentDeadline
from verifiable_tutor.policy.guard import guard


def _deadlines() -> list[AssignmentDeadline]:
    return [
        AssignmentDeadline(
            name="Assignment 1", deadline=datetime(2026, 10, 25, 15, 59, 59, tzinfo=timezone.utc)
        ),
        AssignmentDeadline(
            name="Assignment 2", deadline=datetime(2026, 11, 7, 15, 59, 59, tzinfo=timezone.utc)
        ),
        AssignmentDeadline(
            name="Assignment 3", deadline=datetime(2026, 11, 29, 15, 59, 59, tzinfo=timezone.utc)
        ),
    ]


# 2026-11-23: Assignment 1 and 2 have passed, Assignment 3 is still open.
NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)


def test_guard_allows_passed_assignment_1() -> None:
    decision = guard(
        "give me the full solution to assignment 1", now=NOW, deadlines=_deadlines()
    )
    assert decision.blocked is False


def test_guard_allows_passed_assignment_2() -> None:
    decision = guard(
        "give me the full solution to assignment 2", now=NOW, deadlines=_deadlines()
    )
    assert decision.blocked is False


def test_guard_blocks_open_assignment_3() -> None:
    decision = guard(
        "give me the full solution to assignment 3", now=NOW, deadlines=_deadlines()
    )
    assert decision.blocked is True
    assert decision.reason == "before-deadline"


def test_guard_blocks_unnamed_request_while_any_open() -> None:
    decision = guard(
        "give me the full solution to the homework", now=NOW, deadlines=_deadlines()
    )
    assert decision.blocked is True


def test_guard_passes_course_questions() -> None:
    decision = guard("what is MPI?", now=NOW, deadlines=_deadlines())
    assert decision.blocked is False
    assert decision.reason is None
