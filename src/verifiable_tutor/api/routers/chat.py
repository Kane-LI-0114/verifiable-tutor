"""Chat route: stream one assistant turn as the AI SDK message stream."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .. import streaming
from ..chat import ChatError, ChatService
from ..deps import ChatDep, CurrentUser, ModelDep

router = APIRouter(tags=["chat"])


class DocumentContextBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(
        min_length=1,
        max_length=64,
        description="Document open in the preview. Example: ACS_Lecture_1_2026F.",
    )
    page_no: int | None = Field(
        default=None,
        ge=1,
        description="Page the preview is showing. Example: 12.",
    )


class ChatBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=8000,
        description=(
            "User message; the answer streams back in the AI SDK protocol. "
            "Example: What is MPI_Allreduce?"
        ),
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Existing conversation id; empty starts a new conversation. "
            "Example: 6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8."
        ),
    )
    provider: str | None = Field(
        default=None,
        description=(
            "Provider alias from config/models.yaml; one of deepseek or mimo. "
            "Empty uses the adapter default."
        ),
    )
    tier: str | None = Field(
        default=None,
        description=(
            "Model tier alias; one of flash or pro (pro is MiMo only). "
            "Empty uses the default."
        ),
    )
    thinking: Literal["off", "low", "high", "max", "on"] | None = Field(
        default=None,
        description=(
            "Unified thinking level; one of off, low, high, max. "
            "Empty uses the configured role default."
        ),
    )
    document_context: DocumentContextBody | None = Field(
        default=None,
        description=(
            "The document and page open in the knowledge-base preview. The "
            "prompt names them; the chunks are not injected yet."
        ),
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
            thinking=body.thinking,
            adapter=model,
            document_context=(
                body.document_context.model_dump()
                if body.document_context is not None
                else None
            ),
        )
    except ChatError as exc:
        headers = (
            {"x-conversation-id": exc.conversation_id}
            if exc.conversation_id is not None
            else None
        )
        raise HTTPException(
            status_code=exc.status_code, detail=exc.detail, headers=headers
        ) from exc

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
