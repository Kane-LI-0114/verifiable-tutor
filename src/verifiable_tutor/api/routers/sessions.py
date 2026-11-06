"""Conversation listing, history, and replay for the signed-in user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import streaming
from ..deps import CurrentUser, ReplayDep, StorageDep
from ..replay import ReplayError
from ..schemas import SessionListResponse, SessionMessagesResponse

router = APIRouter(tags=["sessions"])


def _conversation_or_404(storage, session_id: str, user: dict):
    conversation = storage.find_conversation(session_id)
    if conversation is None or conversation["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


@router.get(
    "/api/sessions",
    response_model=SessionListResponse,
    summary="List the signed-in user's conversations",
)
def list_sessions(user: CurrentUser, storage: StorageDep):
    """List the signed-in user's conversations, newest first."""

    sessions = [
        {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "message_count": row["message_count"],
        }
        for row in storage.list_conversations(user["id"])
    ]
    return {"sessions": sessions}


@router.get(
    "/api/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
    summary="Conversation message history",
)
def session_messages(session_id: str, user: CurrentUser, storage: StorageDep):
    """Return one conversation's messages with their turn metadata."""

    _conversation_or_404(storage, session_id, user)
    messages = [
        {
            "id": message["id"],
            "sequence": message["sequence"],
            "role": message["role"],
            "content": message["content"],
            "provider": message["provider"],
            "tier": message["tier"],
            "reasoning": message["reasoning"],
            "model": message["model"],
            "thinking": message["thinking"],
            "work_steps": [
                {
                    "step": step["step"],
                    "status": step["status"],
                    "detail": step["detail"],
                    "duration_ms": step["duration_ms"],
                    "policy": step["policy"],
                    "rule_id": step["rule_id"],
                }
                for step in message["work_steps"]
            ],
            "citations": [
                {
                    "doc_id": citation["doc_id"],
                    "page_no": citation["page_no"],
                    "quote": citation["quoted_span"],
                    "bbox_norm": citation["bbox_norm"],
                }
                for citation in message["citations"]
            ],
            "tool_calls": [
                {
                    "tool_call_id": call.get("tool_call_id"),
                    "name": call["name"],
                    "arguments": call.get("arguments"),
                    "result": call.get("result"),
                    "command": call["command"] or [],
                    "exit_code": call["exit_code"],
                    "output": call["output"],
                    "duration_ms": call.get("duration_ms"),
                    "status": call["status"],
                }
                for call in message["tool_calls"]
            ],
            "created_at": message["created_at"],
        }
        for message in storage.list_messages(session_id)
    ]
    return {"session_id": session_id, "messages": messages}


@router.get(
    "/api/sessions/{session_id}/replay",
    summary="Replay a recorded session stream",
    responses={
        200: {
            "description": "Recorded AI SDK UI message stream frames.",
            "content": {
                "text/event-stream": {"schema": {"type": "string"}}
            },
        },
        401: {"description": "Not signed in."},
        404: {"description": "Conversation not found, not owned, or no trace."},
    },
)
def replay_session(
    session_id: str,
    user: CurrentUser,
    replay: ReplayDep,
    speed: Annotated[float | None, Query(ge=0.1, le=10.0)] = None,
):
    """Re-emit the recorded trace through the normal AI SDK stream path."""

    try:
        frames = replay.frames_for(user, session_id)
    except ReplayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return StreamingResponse(
        replay.event_stream(frames, speed=speed),
        media_type=streaming.STREAM_MEDIA_TYPE,
        headers=streaming.headers(),
    )
