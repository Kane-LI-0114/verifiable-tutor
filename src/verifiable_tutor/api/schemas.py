"""Response models and tag metadata for the documented HTTP API.

The response bodies are unchanged; these models exist so the OpenAPI schema
(and the local Swagger UI) shows the actual field names, types, and nullability
instead of generic objects. Each model carries a realistic example so Swagger
UI can prefill and illustrate the contract. Keep the models in sync with the
route returns.
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

_SESSION_ID = "6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8"
_CREATED_AT = "2026-11-02T12:00:00+00:00"


def _example(data: dict[str, Any]) -> ConfigDict:
    return ConfigDict(extra="forbid", json_schema_extra={"example": data})


class HealthResponse(BaseModel):
    model_config = _example(
        {"status": "ok", "version": "0.1.0", "database": "ok"}
    )

    status: str
    version: str
    database: str


class RegisterResponse(BaseModel):
    model_config = _example(
        {
            "email": "student@ust.hk",
            "role": "student",
            "verification": "pending",
            "email_delivery": "log",
        }
    )

    email: str
    role: str
    verification: str
    email_delivery: str


class VerifyResponse(BaseModel):
    model_config = _example({"email": "student@ust.hk", "status": "active"})

    email: str
    status: str


class LoginUser(BaseModel):
    model_config = _example(
        {"id": _SESSION_ID, "email": "student@ust.hk", "role": "student"}
    )

    id: str
    email: str
    role: str


class LoginResponse(BaseModel):
    model_config = _example(
        {"user": {"id": _SESSION_ID, "email": "student@ust.hk", "role": "student"}}
    )

    user: LoginUser


class MeResponse(BaseModel):
    model_config = _example(
        {
            "id": _SESSION_ID,
            "email": "student@ust.hk",
            "role": "student",
            "created_at": _CREATED_AT,
        }
    )

    id: str
    email: str
    role: str
    created_at: str


class ResetRequestResponse(BaseModel):
    model_config = _example(
        {"email": "student@ust.hk", "email_delivery": "log"}
    )

    email: str
    email_delivery: str


class ResetResponse(BaseModel):
    model_config = _example(
        {"email": "student@ust.hk", "sessions_invalidated": 1}
    )

    email: str
    sessions_invalidated: int


class SessionSummary(BaseModel):
    model_config = _example(
        {
            "id": _SESSION_ID,
            "title": "What is MPI_Allreduce?",
            "created_at": _CREATED_AT,
            "updated_at": _CREATED_AT,
            "message_count": 2,
        }
    )

    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


class SessionListResponse(BaseModel):
    model_config = _example(
        {
            "sessions": [
                {
                    "id": _SESSION_ID,
                    "title": "What is MPI_Allreduce?",
                    "created_at": _CREATED_AT,
                    "updated_at": _CREATED_AT,
                    "message_count": 2,
                }
            ]
        }
    )

    sessions: list[SessionSummary]


class MessageRecord(BaseModel):
    model_config = _example(
        {
            "id": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7",
            "sequence": 1,
            "role": "user",
            "content": "What is MPI_Allreduce?",
            "provider": None,
            "tier": None,
            "created_at": _CREATED_AT,
        }
    )

    id: str
    sequence: int
    role: str
    content: str
    provider: str | None
    tier: str | None
    created_at: str


class SessionMessagesResponse(BaseModel):
    model_config = _example(
        {
            "session_id": _SESSION_ID,
            "messages": [
                {
                    "id": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7",
                    "sequence": 1,
                    "role": "user",
                    "content": "What is MPI_Allreduce?",
                    "provider": None,
                    "tier": None,
                    "created_at": _CREATED_AT,
                }
            ],
        }
    )

    session_id: str
    messages: list[MessageRecord]


class TranscriptionResponse(BaseModel):
    model_config = _example(
        {
            "text": "What is MPI_Allreduce?",
            "language": "en",
            "seconds": 2.1,
            "model": "mimo-v2.5-asr",
        }
    )

    text: str
    language: str
    seconds: float | None
    model: str


class CitationRecord(BaseModel):
    model_config = _example(
        {
            "doc_id": "course_project",
            "page_no": 1,
            "quote": "Building an End-to-End Agent System",
        }
    )

    doc_id: str
    page_no: int
    quote: str


class CardRecord(BaseModel):
    model_config = _example(
        {
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
            "citations": [
                {
                    "doc_id": "course_project",
                    "page_no": 1,
                    "quote": "Building an End-to-End Agent System",
                }
            ],
            "model": "qwen3.8-27b",
            "prompt_version": "kb-v1",
            "build_id": "kb-20261102-120000-a1b2c3",
            "created_at": "2026-11-02T03:02:12+00:00",
        }
    )

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


class CardsResponse(BaseModel):
    model_config = _example(
        {
            "cards": [
                {
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
                    "citations": [
                        {
                            "doc_id": "course_project",
                            "page_no": 1,
                            "quote": "Building an End-to-End Agent System",
                        }
                    ],
                    "model": "qwen3.8-27b",
                    "prompt_version": "kb-v1",
                    "build_id": "kb-20261102-120000-a1b2c3",
                    "created_at": "2026-11-02T03:02:12+00:00",
                }
            ],
            "total": 1,
        }
    )

    cards: list[CardRecord]
    total: int


class BuildAcceptedResponse(BaseModel):
    model_config = _example(
        {"build_id": "kb-20261102-120000-a1b2c3", "state": "queued"}
    )

    build_id: str
    state: str


class BuildRecord(BaseModel):
    model_config = _example(
        {
            "id": "kb-20261102-120000-a1b2c3",
            "state": "ready",
            "job_id": "28067",
            "records_path": "data/kb/records/kb-20261102-120000-a1b2c3.jsonl",
            "records_count": 8,
            "error": None,
            "created_at": _CREATED_AT,
            "updated_at": "2026-11-02T12:12:00+00:00",
            "request": {"doc_id": "course_project", "max_chunks": 8},
        }
    )

    id: str
    state: str
    job_id: str | None
    records_path: str | None
    records_count: int | None
    error: str | None
    created_at: str
    updated_at: str
    request: dict[str, Any]


class BuildListResponse(BaseModel):
    model_config = _example(
        {
            "builds": [
                {
                    "id": "kb-20261102-120000-a1b2c3",
                    "state": "ready",
                    "job_id": "28067",
                    "records_path": "data/kb/records/kb-20261102-120000-a1b2c3.jsonl",
                    "records_count": 8,
                    "error": None,
                    "created_at": _CREATED_AT,
                    "updated_at": "2026-11-02T12:12:00+00:00",
                    "request": {"doc_id": "course_project", "max_chunks": 8},
                }
            ]
        }
    )

    builds: list[BuildRecord]
