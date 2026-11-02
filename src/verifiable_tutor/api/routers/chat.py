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
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "message": "What is MPI_Allreduce?",
                "session_id": None,
                "provider": "deepseek",
                "tier": "flash",
            }
        },
    )

    message: str = Field(
        min_length=1,
        max_length=8000,
        description="User message; the answer streams back in the AI SDK protocol.",
        json_schema_extra={"example": "What is MPI_Allreduce?"},
    )
    session_id: str | None = Field(
        default=None,
        description="Existing conversation id; empty starts a new conversation.",
        json_schema_extra={"example": "6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8"},
    )
    provider: str | None = Field(
        default=None,
        description="Provider alias from config/models.yaml; the adapter default is used when empty.",
        json_schema_extra={"example": "deepseek", "enum": ["deepseek", "mimo"]},
    )
    tier: str | None = Field(
        default=None,
        description="Model tier alias; flash is on both providers, pro only on MiMo.",
        json_schema_extra={"example": "flash", "enum": ["flash", "pro"]},
    )


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
