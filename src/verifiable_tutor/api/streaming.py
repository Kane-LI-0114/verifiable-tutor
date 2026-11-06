"""AI SDK UI message stream (version 1) encoder.

Wire contract checked on 2026-11-02 against the protocol page referenced by
ADR-0003 (https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol): one SSE
``data: <json>`` line per part, the ``x-vercel-ai-ui-message-stream: v1``
response header, and a terminating ``data: [DONE]`` marker. The project's
``data-step`` part is a custom data part carrying the work-chain step.
"""

from __future__ import annotations

import json
from typing import Any

STREAM_HEADER = "x-vercel-ai-ui-message-stream"
STREAM_VERSION = "v1"
STREAM_MEDIA_TYPE = "text/event-stream"
DONE_FRAME = "data: [DONE]\n\n"


def headers() -> dict[str, str]:
    """Headers every streaming chat or replay response carries."""

    return {
        "cache-control": "no-cache",
        STREAM_HEADER: STREAM_VERSION,
    }


def sse(frame: dict[str, Any]) -> str:
    """Encode one protocol part as an SSE data line."""

    return f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"


def start(message_id: str) -> dict[str, Any]:
    return {"type": "start", "messageId": message_id}


def data_step(step: str, status: str, **extra: Any) -> dict[str, Any]:
    return {"type": "data-step", "data": {"step": step, "status": status, **extra}}


def start_step() -> dict[str, Any]:
    return {"type": "start-step"}


def finish_step() -> dict[str, Any]:
    return {"type": "finish-step"}


def data_tool(data: dict[str, Any]) -> dict[str, Any]:
    """One custom data part carrying a tool call's running or final state."""

    return {"type": "data-tool", "data": data}


def text_start(part_id: str) -> dict[str, Any]:
    return {"type": "text-start", "id": part_id}


def text_delta(part_id: str, delta: str) -> dict[str, Any]:
    return {"type": "text-delta", "id": part_id, "delta": delta}


def text_end(part_id: str) -> dict[str, Any]:
    return {"type": "text-end", "id": part_id}


def reasoning_start(part_id: str) -> dict[str, Any]:
    return {"type": "reasoning-start", "id": part_id}


def reasoning_delta(part_id: str, delta: str) -> dict[str, Any]:
    return {"type": "reasoning-delta", "id": part_id, "delta": delta}


def reasoning_end(part_id: str) -> dict[str, Any]:
    return {"type": "reasoning-end", "id": part_id}


def finish() -> dict[str, Any]:
    return {"type": "finish"}


def error(error_text: str) -> dict[str, Any]:
    return {"type": "error", "errorText": error_text}
