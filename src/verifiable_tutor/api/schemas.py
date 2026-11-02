"""Response models and tag metadata for the documented HTTP API.

The response bodies are unchanged; these models exist so the OpenAPI schema
(and the local Swagger UI) shows the actual field names, types, and nullability
instead of generic objects. Keep the models in sync with the route returns.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

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


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(_Model):
    status: str
    version: str
    database: str


class RegisterResponse(_Model):
    email: str
    role: str
    verification: str
    email_delivery: str


class VerifyResponse(_Model):
    email: str
    status: str


class LoginUser(_Model):
    id: str
    email: str
    role: str


class LoginResponse(_Model):
    user: LoginUser


class MeResponse(_Model):
    id: str
    email: str
    role: str
    created_at: str


class ResetRequestResponse(_Model):
    email: str
    email_delivery: str


class ResetResponse(_Model):
    email: str
    sessions_invalidated: int


class SessionSummary(_Model):
    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


class SessionListResponse(_Model):
    sessions: list[SessionSummary]


class MessageRecord(_Model):
    id: str
    sequence: int
    role: str
    content: str
    provider: str | None
    tier: str | None
    created_at: str


class SessionMessagesResponse(_Model):
    session_id: str
    messages: list[MessageRecord]


class TranscriptionResponse(_Model):
    text: str
    language: str
    seconds: float | None
    model: str


class CitationRecord(_Model):
    doc_id: str
    page_no: int
    quote: str


class CardRecord(_Model):
    chunk_id: str
    doc_id: str
    page_no: int
    section: str | None
    summary: str
    key_terms: list[str]
    study_questions: list[str]
    citations: list[CitationRecord]
    model: str | None
    prompt_version: str | None
    build_id: str | None
    created_at: str | None


class CardsResponse(_Model):
    cards: list[CardRecord]
    total: int


class BuildAcceptedResponse(_Model):
    build_id: str
    state: str


class BuildRecord(_Model):
    id: str
    state: str
    job_id: str | None
    records_path: str | None
    records_count: int | None
    error: str | None
    created_at: str
    updated_at: str
    request: dict[str, Any]


class BuildListResponse(_Model):
    builds: list[BuildRecord]
