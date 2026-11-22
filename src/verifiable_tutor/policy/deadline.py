"""Deadline registry for the disclosure gate (VT-08).

The registry is a small list of assignment deadlines. The gate blocks a
homework-solution request while at least one assignment's deadline is still in
the future; after every deadline has passed the gate opens for full teaching.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


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
