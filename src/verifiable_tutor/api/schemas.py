"""Response models and tag metadata for the documented HTTP API.

The response bodies are unchanged; these models exist so the OpenAPI schema
(and the local Swagger UI) shows the actual field names, types, nullability,
allowed option values, and a per-field ``example`` inside the Schema view.
Model-level examples also prefill "Try it out", but the per-field metadata is
what the Schema tab displays. Keep the models in sync with the route returns.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "health",
        "description": "Liveness and local storage health for the backend.",
    },
    {
        "name": "auth",
        "description": (
            "Registration with email verification, sign-in, server-side "
            "sessions, and one-time password reset."
        ),
    },
    {
        "name": "chat",
        "description": (
            "One streamed assistant turn over the AI SDK UI message stream "
            "protocol version 1."
        ),
    },
    {
        "name": "sessions",
        "description": "Conversation history and replay of recorded stream traces.",
    },
    {
        "name": "voice",
        "description": "MiMo speech transcription and speech synthesis.",
    },
    {
        "name": "knowledge",
        "description": (
            "Validated knowledge cards and the Qwen knowledge-base build "
            "lifecycle."
        ),
    },
    {
        "name": "corpus",
        "description": "Rendered course page images for the citation panel.",
    },
    {
        "name": "practice",
        "description": (
            "Practice execution; a documented scaffold until the tacc/exec job "
            "exists."
        ),
    },
]

_SESSION_ID = "6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8"
_CREATED_AT = "2026-11-02T12:00:00+00:00"
_EMAIL = "student@ust.hk"

SESSION_EXAMPLE: dict[str, Any] = {
    "id": _SESSION_ID,
    "title": "What is MPI_Allreduce?",
    "created_at": _CREATED_AT,
    "updated_at": _CREATED_AT,
    "message_count": 2,
}
MESSAGE_EXAMPLE: dict[str, Any] = {
    "id": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7",
    "sequence": 1,
    "role": "user",
    "content": "What is MPI_Allreduce?",
    "provider": None,
    "tier": None,
    "created_at": _CREATED_AT,
}
CITATION_EXAMPLE: dict[str, Any] = {
    "doc_id": "course_project",
    "page_no": 1,
    "quote": "Building an End-to-End Agent System",
}
CARD_EXAMPLE: dict[str, Any] = {
    "chunk_id": "course_project:p001:c00",
    "doc_id": "course_project",
    "page_no": 1,
    "section": "Course Project",
    "summary": "This page introduces the course project.",
    "key_terms": ["Course Project", "Agent System"],
    "study_questions": [
        "What is the course project?",
        "Which system is built?",
    ],
    "citations": [CITATION_EXAMPLE],
    "model": "qwen3.8-27b",
    "prompt_version": "kb-v1",
    "build_id": "kb-20261102-120000-a1b2c3",
    "created_at": "2026-11-02T03:02:12+00:00",
}
BUILD_ID = "kb-20261102-120000-a1b2c3"
BUILD_EXAMPLE: dict[str, Any] = {
    "id": BUILD_ID,
    "state": "ready",
    "job_id": "28067",
    "records_path": f"data/kb/records/{BUILD_ID}.jsonl",
    "records_count": 8,
    "error": None,
    "created_at": _CREATED_AT,
    "updated_at": "2026-11-02T12:12:00+00:00",
    "request": {"doc_id": "course_project", "max_chunks": 8},
}


def _ex(
    example: Any,
    description: str | None = None,
    enum: list[Any] | None = None,
) -> Any:
    """Required field with a per-field schema example and optional enum docs."""

    extra: dict[str, Any] = {"example": example}
    if enum is not None:
        extra["enum"] = enum
    return Field(description=description, json_schema_extra=extra)


def _opt(
    example: Any,
    description: str | None = None,
    enum: list[Any] | None = None,
) -> Any:
    """Optional field (default ``None``) with schema example/enum docs."""

    extra: dict[str, Any] = {"example": example}
    if enum is not None:
        extra["enum"] = enum
    return Field(default=None, description=description, json_schema_extra=extra)


def _example(data: dict[str, Any]) -> ConfigDict:
    return ConfigDict(extra="forbid", json_schema_extra={"example": data})


class HealthResponse(BaseModel):
    model_config = _example({"status": "ok", "version": "0.1.0", "database": "ok"})

    status: str = _ex("ok", "Liveness status; ok when the backend answers.")
    version: str = _ex("0.1.0", "API version string.")
    database: str = _ex("ok", "Local SQLite database health.")


class RegisterResponse(BaseModel):
    model_config = _example(
        {
            "email": _EMAIL,
            "role": "student",
            "verification": "pending",
            "email_delivery": "log",
        }
    )

    email: str = _ex(_EMAIL, "Normalised student email address.")
    role: Literal["student"] = _ex("student", "Account role created for registration.")
    verification: Literal["pending"] = _ex(
        "pending", "The account waits for the emailed six digit code."
    )
    email_delivery: Literal["log", "smtp"] = _ex(
        "log",
        "log when SMTP is unset in development mode; smtp when mail is sent.",
    )


class VerifyResponse(BaseModel):
    model_config = _example({"email": _EMAIL, "status": "active"})

    email: str = _ex(_EMAIL, "Verified email address.")
    status: Literal["active"] = _ex("active", "The account is now active.")


class LoginUser(BaseModel):
    model_config = _example(
        {"id": _SESSION_ID, "email": _EMAIL, "role": "student"}
    )

    id: str = _ex(_SESSION_ID, "Internal user id.")
    email: str = _ex(_EMAIL, "Account email address.")
    role: Literal["student", "instructor"] = _ex(
        "student", "Account role; instructor can manage knowledge builds."
    )


class LoginResponse(BaseModel):
    model_config = _example(
        {"user": {"id": _SESSION_ID, "email": _EMAIL, "role": "student"}}
    )

    user: LoginUser = _ex(
        {"id": _SESSION_ID, "email": _EMAIL, "role": "student"},
        "The signed-in account.",
    )


class MeResponse(BaseModel):
    model_config = _example(
        {
            "id": _SESSION_ID,
            "email": _EMAIL,
            "role": "student",
            "created_at": _CREATED_AT,
        }
    )

    id: str = _ex(_SESSION_ID, "Internal user id.")
    email: str = _ex(_EMAIL, "Account email address.")
    role: Literal["student", "instructor"] = _ex("student", "Account role.")
    created_at: str = _ex(_CREATED_AT, "ISO-8601 UTC account creation time.")


class ResetRequestResponse(BaseModel):
    model_config = _example({"email": _EMAIL, "email_delivery": "log"})

    email: str = _ex(_EMAIL, "Email the reset link was sent to.")
    email_delivery: Literal["log", "smtp"] = _ex(
        "log", "log when the link goes to the backend log in development mode."
    )


class ResetResponse(BaseModel):
    model_config = _example({"email": _EMAIL, "sessions_invalidated": 1})

    email: str = _ex(_EMAIL, "Email whose password changed.")
    sessions_invalidated: int = _ex(
        1, "Number of server-side sessions removed by the reset."
    )


class SessionSummary(BaseModel):
    model_config = _example(SESSION_EXAMPLE)

    id: str = _ex(_SESSION_ID, "Conversation id, used as session_id in the API.")
    title: str | None = _opt(
        "What is MPI_Allreduce?", "First-message title; null when untitled."
    )
    created_at: str = _ex(_CREATED_AT, "ISO-8601 UTC creation time.")
    updated_at: str = _ex(_CREATED_AT, "ISO-8601 UTC last update time.")
    message_count: int = _ex(2, "Number of stored messages.")


class SessionListResponse(BaseModel):
    model_config = _example({"sessions": [SESSION_EXAMPLE]})

    sessions: list[SessionSummary] = _ex(
        [SESSION_EXAMPLE], "The signed-in user's conversations, newest first."
    )


class MessageRecord(BaseModel):
    model_config = _example(MESSAGE_EXAMPLE)

    id: str = _ex("b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7", "Message id.")
    sequence: int = _ex(1, "Order inside the conversation, starting at 1.")
    role: Literal["user", "assistant"] = _ex(
        "user", "Who produced the message."
    )
    content: str = _ex(
        "What is MPI_Allreduce?", "Message text, in the language used."
    )
    provider: str | None = _opt(
        None, "Model provider for assistant messages; null for user messages."
    )
    tier: str | None = _opt(
        None, "Model tier for assistant messages; null for user messages."
    )
    created_at: str = _ex(_CREATED_AT, "ISO-8601 UTC creation time.")


class SessionMessagesResponse(BaseModel):
    model_config = _example({"session_id": _SESSION_ID, "messages": [MESSAGE_EXAMPLE]})

    session_id: str = _ex(_SESSION_ID, "Conversation id.")
    messages: list[MessageRecord] = _ex(
        [MESSAGE_EXAMPLE], "Messages in sequence order."
    )


class TranscriptionResponse(BaseModel):
    model_config = _example(
        {
            "text": "What is MPI_Allreduce?",
            "language": "en",
            "seconds": 2.1,
            "model": "mimo-v2.5-asr",
        }
    )

    text: str = _ex("What is MPI_Allreduce?", "Transcript of the audio file.")
    language: str = _ex("en", "Detected or requested language.")
    seconds: float | None = _opt(2.1, "Audio duration in seconds when reported.")
    model: str = _ex("mimo-v2.5-asr", "ASR model id that produced the transcript.")


class CitationRecord(BaseModel):
    model_config = _example(CITATION_EXAMPLE)

    doc_id: str = _ex("course_project", "Course document id.")
    page_no: int = _ex(1, "Page number the quote appears on.")
    quote: str = _ex(
        "Building an End-to-End Agent System",
        "Exact quoted span on the page.",
    )


class CardRecord(BaseModel):
    model_config = _example(CARD_EXAMPLE)

    chunk_id: str = _ex("course_project:p001:c00", "Knowledge chunk id.")
    doc_id: str = _ex("course_project", "Course document id.")
    page_no: int = _ex(1, "Page number the card covers.")
    section: str | None = _opt("Course Project", "Section title when detected.")
    summary: str = _ex(
        "This page introduces the course project.", "Card summary."
    )
    key_terms: list[str] = _ex(
        ["Course Project", "Agent System"], "Key terms for review."
    )
    study_questions: list[str] = _ex(
        ["What is the course project?", "Which system is built?"],
        "Study questions generated from the page.",
    )
    citations: list[CitationRecord] = _ex(
        [CITATION_EXAMPLE], "Page citations supporting the card."
    )
    model: str | None = _opt("qwen3.8-27b", "Model that generated the card.")
    prompt_version: str | None = _opt("kb-v1", "Prompt version of the build.")
    build_id: str | None = _opt(BUILD_ID, "Knowledge build that produced the card.")
    created_at: str | None = _opt(
        "2026-11-02T03:02:12+00:00", "ISO-8601 UTC record creation time."
    )


class CardsResponse(BaseModel):
    model_config = _example({"cards": [CARD_EXAMPLE], "total": 1})

    cards: list[CardRecord] = _ex([CARD_EXAMPLE], "Page of matching cards.")
    total: int = _ex(1, "Total matching cards before pagination.")


class BuildAcceptedResponse(BaseModel):
    model_config = _example({"build_id": BUILD_ID, "state": "queued"})

    build_id: str = _ex(BUILD_ID, "Identifier of the queued build.")
    state: Literal["queued"] = _ex("queued", "The build was accepted and queued.")


class BuildRecord(BaseModel):
    model_config = _example(BUILD_EXAMPLE)

    id: str = _ex(BUILD_ID, "Build id.")
    state: Literal["queued", "running", "ready", "failed"] = _ex(
        "ready", "Build state; ready means the validated records were stored."
    )
    job_id: str | None = _opt("28067", "TACC job id when submitted.")
    records_path: str | None = _opt(
        f"data/kb/records/{BUILD_ID}.jsonl", "Local validated records JSONL."
    )
    records_count: int | None = _opt(8, "Number of valid records downloaded.")
    error: str | None = _opt(None, "Failure message when state is failed.")
    created_at: str = _ex(_CREATED_AT, "ISO-8601 UTC creation time.")
    updated_at: str = _ex(
        "2026-11-02T12:12:00+00:00", "ISO-8601 UTC last update time."
    )
    request: dict[str, Any] = _ex(
        {"doc_id": "course_project", "max_chunks": 8},
        "The request recorded when the build was queued.",
    )


class BuildListResponse(BaseModel):
    model_config = _example({"builds": [BUILD_EXAMPLE]})

    builds: list[BuildRecord] = _ex(
        [BUILD_EXAMPLE], "Knowledge builds, newest first."
    )
