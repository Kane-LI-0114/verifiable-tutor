"""Replay recorded session traces through the normal stream path.

Replay re-emits the recorded AI SDK frames with their original spacing scaled
by a speed factor and capped per gap, so the offline demo exercises the same
frontend path without any model call (ADR-0003, FR-B10).
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, Sequence

from . import streaming
from ..storage import Storage
from ..trace import SessionTrace

MAX_REPLAY_GAP_SECONDS = 2.0


class ReplayError(Exception):
    """A client-visible replay failure."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def replay_delays(
    timestamps: Sequence[float],
    *,
    speed: float,
    max_gap: float = MAX_REPLAY_GAP_SECONDS,
) -> list[float]:
    """Return the sleep before each frame, scaled by speed and capped."""

    if speed <= 0:
        raise ValueError("speed must be positive")
    delays: list[float] = []
    previous: float | None = None
    for timestamp in timestamps:
        if previous is None:
            delays.append(0.0)
        else:
            gap = max(0.0, (timestamp - previous) / speed)
            delays.append(min(max_gap, gap))
        previous = timestamp
    return delays


class ReplayService:
    """Load a recorded trace and re-emit it as the production stream."""

    def __init__(
        self,
        *,
        storage: Storage,
        trace: SessionTrace,
        sleep: Callable[[float], None],
        default_speed: float,
    ) -> None:
        self._storage = storage
        self._trace = trace
        self._sleep = sleep
        self._default_speed = default_speed

    def frames_for(
        self, user: dict[str, Any], session_id: str
    ) -> list[tuple[float, dict[str, Any]]]:
        """Return the recorded frames after the ownership check."""

        conversation = self._storage.find_conversation(session_id)
        if conversation is None or conversation["user_id"] != user["id"]:
            raise ReplayError(404, "conversation not found")
        frames = self._trace.frames(user["id"], session_id)
        if not frames:
            raise ReplayError(404, "no replay trace")
        return frames

    def event_stream(
        self,
        frames: Sequence[tuple[float, dict[str, Any]]],
        *,
        speed: float | None = None,
    ) -> Iterator[str]:
        """Yield the recorded frames as SSE, sleeping for scaled gaps."""

        resolved_speed = speed if speed is not None else self._default_speed
        delays = replay_delays([timestamp for timestamp, _ in frames], speed=resolved_speed)
        for delay, (_, frame) in zip(delays, frames):
            if delay > 0:
                self._sleep(delay)
            yield streaming.sse(frame)
        yield streaming.DONE_FRAME
