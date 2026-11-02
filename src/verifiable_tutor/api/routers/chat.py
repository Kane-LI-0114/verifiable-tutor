"""Chat route: stream one assistant turn as the AI SDK message stream."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import streaming
from ..chat import ChatError, ChatService
from ..deps import ChatDep, CurrentUser, ModelDep

router = APIRouter(tags=["chat"])


class ChatBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    provider: str | None = None
    tier: str | None = None


@router.post(
    "/api/chat",
    summary="Stream one assistant turn",
    responses={
        200: {
            "description": "AI SDK UI message stream version 1 frames.",
            "content": {
                "text/event-stream": {"schema": {"type": "string"}}
            },
        },
        400: {"description": "Invalid body or model selection."},
        401: {"description": "Not signed in."},
        404: {"description": "Conversation not found or not owned by the caller."},
        503: {
            "description": (
                "Model layer unavailable or the model failed before the first frame."
            )
        },
    },
)
def create_turn(
    body: ChatBody,
    user: CurrentUser,
    chat: ChatDep,
    model: ModelDep,
):
    """Start one turn and stream its frames with the recorded trace."""

    try:
        turn = chat.begin_turn(
            user,
            session_id=body.session_id,
            message=body.message,
            provider=body.provider,
            tier=body.tier,
            adapter=model,
        )
    except ChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    def body_stream():
        for frame in turn.frames:
            yield streaming.sse(frame)
        yield streaming.DONE_FRAME

    headers = {
        **streaming.headers(),
        "x-conversation-id": turn.conversation_id,
    }
    return StreamingResponse(
        body_stream(),
        media_type=streaming.STREAM_MEDIA_TYPE,
        headers=headers,
    )
