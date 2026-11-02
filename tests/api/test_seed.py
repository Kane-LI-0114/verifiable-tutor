"""Instructor seeding command logic (FR-A9)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from verifiable_tutor.auth.service import bootstrap_instructor
from verifiable_tutor.storage import Storage

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def _clock():
    return NOW


def test_bootstrap_instructor_is_idempotent(tmp_path: Path):
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()

    first = bootstrap_instructor(
        storage=storage,
        email="teacher@ust.hk",
        password="instructor-password",
        clock=_clock,
    )
    second = bootstrap_instructor(
        storage=storage,
        email="teacher@ust.hk",
        password="instructor-password",
        clock=_clock,
    )

    assert first == {"email": "teacher@ust.hk", "role": "instructor", "created": True}
    assert second == {"email": "teacher@ust.hk", "role": "instructor", "created": False}
    user = storage.find_user_by_email("teacher@ust.hk")
    assert user is not None
    assert user["role"] == "instructor"
    assert user["status"] == "active"
    assert storage.scalar("SELECT COUNT(*) FROM users") == 1
