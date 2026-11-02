"""JSONL session trace: the canonical record for replay and evaluation.

The trace belongs to one user and one conversation. It contains a ``meta``
line, one ``frame`` line per AI SDK UI message stream part, and ``event``
lines for failures. Only internal user ids appear here, never email addresses
(FR-A7). Replay reads the ``frame`` lines and re-emits them at a speed factor.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""

    return datetime.now(timezone.utc)


class SessionTrace:
    """Read and write one JSONL trace per conversation."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def path_for(self, user_id: str, session_id: str) -> Path:
        return self.directory / user_id / f"{session_id}.jsonl"

    def exists(self, user_id: str, session_id: str) -> bool:
        return self.path_for(user_id, session_id).is_file()

    def _append(
        self, user_id: str, session_id: str, record: dict[str, Any], *, now: datetime
    ) -> None:
        path = self.path_for(user_id, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"ts": now.timestamp(), **record}, ensure_ascii=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def append_meta(
        self, user_id: str, session_id: str, meta: dict[str, Any], *, now: datetime
    ) -> None:
        self._append(user_id, session_id, {"kind": "meta", **meta}, now=now)

    def append_frame(
        self, user_id: str, session_id: str, frame: dict[str, Any], *, now: datetime
    ) -> None:
        self._append(user_id, session_id, {"kind": "frame", "frame": frame}, now=now)

    def append_event(
        self,
        user_id: str,
        session_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
        *,
        now: datetime,
    ) -> None:
        self._append(
            user_id,
            session_id,
            {"kind": "event", "event": event, "payload": payload or {}},
            now=now,
        )

    def frames(self, user_id: str, session_id: str) -> list[tuple[float, dict[str, Any]]]:
        """Return ``(timestamp, frame)`` pairs, skipping malformed lines."""

        path = self.path_for(user_id, session_id)
        if not path.is_file():
            return []
        pairs: list[tuple[float, dict[str, Any]]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict) or record.get("kind") != "frame":
                continue
            frame = record.get("frame")
            timestamp = record.get("ts")
            if isinstance(frame, dict) and isinstance(timestamp, (int, float)):
                pairs.append((float(timestamp), frame))
        return pairs
