"""Small helpers shared by the HTTP API tests."""

from __future__ import annotations

import json


def parse_sse(text: str) -> list[object]:
    """Decode an SSE body into protocol parts plus the [DONE] marker."""

    parts: list[object] = []
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: ") :]
        parts.append(payload if payload == "[DONE]" else json.loads(payload))
    return parts
