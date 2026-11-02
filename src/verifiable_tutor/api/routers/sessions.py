"""Conversation listing, history, and replay for the signed-in user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import streaming
from ..deps import CurrentUser, ReplayDep, StorageDep
from ..replay import ReplayError

router = APIRouter(tags=["sessions"])


def _conversation_or_404(storage, session_id: str, user: dict):
    conversation = storage.find_conversation(session_id)
    if conversation is None or conversation["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


@router.get("/api/sessions")
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


@router.get("/api/sessions/{session_id}/messages")
def session_messages(session_id: str, user: CurrentUser, storage: StorageDep):
    """Return one conversation's messages after an ownership check."""

    _conversation_or_404(storage, session_id, user)
    messages = [
        {
            "id": message["id"],
            "sequence": message["sequence"],
            "role": message["role"],
            "content": message["content"],
            "provider": message["provider"],
            "tier": message["tier"],
            "created_at": message["created_at"],
        }
        for message in storage.list_messages(session_id)
    ]
    return {"session_id": session_id, "messages": messages}


@router.get("/api/sessions/{session_id}/replay")
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
