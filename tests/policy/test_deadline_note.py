from datetime import datetime, timezone

from verifiable_tutor.policy.deadline import AssignmentDeadline, deadline_status_note


def test_deadline_status_note_marks_passed_and_open_assignments() -> None:
    deadlines = [
        AssignmentDeadline(
            "Assignment 1", datetime(2026, 10, 25, 23, 59, tzinfo=timezone.utc)
        ),
        AssignmentDeadline(
            "Assignment 3", datetime(2026, 11, 29, 23, 59, tzinfo=timezone.utc)
        ),
    ]

    note = deadline_status_note(
        deadlines, datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)
    )

    lines = note.splitlines()
    assert any(
        line.startswith("- Assignment 1") and line.endswith("passed") for line in lines
    )
    assert any(
        line.startswith("- Assignment 3") and line.endswith("open") for line in lines
    )
    assert "complete solution" in note


def test_deadline_status_note_is_empty_without_assignments() -> None:
    assert deadline_status_note([], datetime(2026, 11, 23, tzinfo=timezone.utc)) == ""
