"""Deadline registry for the disclosure gate (VT-08).

The registry is a small list of assignment deadlines. The gate blocks a
homework-solution request while at least one assignment's deadline is still in
the future; after every deadline has passed the gate opens for full teaching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..prompts import load_prompt

DEADLINE_STATUS_PROMPT = load_prompt("deadline_status")


@dataclass(frozen=True)
class AssignmentDeadline:
    """One assignment with its deadline."""

    name: str
    deadline: datetime


def load_deadlines(path: Path) -> list[AssignmentDeadline]:
    """Load assignment deadlines from a YAML file.

    The file lists ``assignments`` with a ``name`` and an ISO ``deadline``.
    A deadline without a timezone is treated as UTC.
    """

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    deadlines: list[AssignmentDeadline] = []
    for item in data.get("assignments", []):
        deadline = datetime.fromisoformat(str(item["deadline"]))
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        deadlines.append(AssignmentDeadline(name=str(item["name"]), deadline=deadline))
    return deadlines


def is_before_deadline(now: datetime, deadlines: list[AssignmentDeadline]) -> bool:
    """True while ``now`` is before at least one assignment's deadline."""

    return any(now < item.deadline for item in deadlines)


def identify_assignment_number(message: str) -> str | None:
    """Return the assignment number ("1", "2", "3") named in a message."""

    normalized = message.lower()
    match = re.search(r"assignment\s*#?\s*([123])", normalized)
    if match:
        return match.group(1)
    match = re.search(r"作业\s*([123一二三])", message)
    if match:
        token = match.group(1)
        return {"一": "1", "二": "2", "三": "3"}.get(token, token)
    return None


def find_deadline(
    number: str, deadlines: list[AssignmentDeadline]
) -> AssignmentDeadline | None:
    """Return the deadline entry for the numbered assignment, if present."""

    suffix = f"assignment {number}"
    for item in deadlines:
        if suffix in item.name.lower():
            return item
    return None


def deadline_status_note(
    deadlines: list[AssignmentDeadline], now: datetime
) -> str:
    """Describe each assignment deadline and the disclosure rule for the model."""

    if not deadlines:
        return ""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    rows = []
    for item in deadlines:
        state = "open" if item.deadline > now else "passed"
        rows.append(f"- {item.name}: deadline {item.deadline.isoformat()}, {state}")
    return DEADLINE_STATUS_PROMPT.replace(
        "%%NOW%%", now.isoformat(timespec="minutes")
    ).replace("%%ASSIGNMENTS%%", "\n".join(rows))
