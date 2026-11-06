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
CITATION_EXAMPLE: dict[str, Any] = {
    "doc_id": "course_project",
    "page_no": 1,
    "quote": "Building an End-to-End Agent System",
}
WORK_STEP_EXAMPLE: dict[str, Any] = {
    "step": "generate",
    "status": "done",
    "detail": None,
    "duration_ms": 812,
    "policy": None,
    "rule_id": None,
}
TOOL_CALL_EXAMPLE: dict[str, Any] = {
    "tool_call_id": "call_1",
    "name": "search_course",
    "arguments": {"query": "MPI_Allreduce", "k": 3},
    "result": {"chunks": [{"doc_id": "Tutorial_2", "page_no": 8}]},
    "command": [],
    "exit_code": None,
    "output": "3 course chunks",
    "duration_ms": 42,
    "status": "done",
}
MESSAGE_EVENT_EXAMPLE: dict[str, Any] = {
    "kind": "reasoning",
    "reasoning": "The question asks about a collective operation.",
    "tool_call": None,
}
MESSAGE_EXAMPLE: dict[str, Any] = {
    "id": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7",
    "sequence": 2,
    "role": "assistant",
    "content": "MPI_Allreduce reduces a value across all ranks.",
    "provider": "deepseek",
    "tier": "flash",
    "reasoning": "The question asks about a collective operation.",
    "model": "deepseek-flash",
    "thinking": "high",
    "work_steps": [WORK_STEP_EXAMPLE],
    "citations": [CITATION_EXAMPLE],
    "tool_calls": [],
    "events": [MESSAGE_EVENT_EXAMPLE],
    "created_at": _CREATED_AT,
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


class DomainsResponse(BaseModel):
    model_config = _example({"domains": ["connect.ust.hk", "ust.hk"]})

    domains: list[str] = _ex(
        ["connect.ust.hk", "ust.hk"],
        "Allowed registration email domains, in the configured order.",
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


class WorkStepRecord(BaseModel):
    model_config = _example(WORK_STEP_EXAMPLE)

    step: Literal[
        "understand", "retrieve", "verify", "decide", "generate", "cite"
    ] = _ex(
        "generate",
        "Work-chain step; one of understand, retrieve, verify, decide, "
        "generate, or cite.",
    )
    status: Literal["pending", "started", "done", "failed"] = _ex(
        "done",
        "Step state; one of pending, started, done, or failed.",
    )
    detail: str | None = _opt(None, "Step detail shown under the step when set.")
    duration_ms: int | None = _opt(812, "Step duration in milliseconds when known.")
    policy: (
        Literal[
            "pre-release",
            "active",
            "extension-window",
            "post-deadline",
            "unknown",
        ]
        | None
    ) = _opt(
        None,
        "Disclosure policy state carried by the decide step, when decided.",
    )
    rule_id: str | None = _opt(None, "Deadline-registry rule that decided the step.")


class ToolCallRecord(BaseModel):
    model_config = _example(TOOL_CALL_EXAMPLE)

    tool_call_id: str | None = _opt(
        "call_1", "Provider tool call id the result is correlated with."
    )
    name: str = _ex("search_course", "Typed tool that ran during the answer.")
    arguments: dict[str, Any] | None = _opt(
        {"query": "MPI_Allreduce", "k": 3}, "Parsed tool arguments."
    )
    result: Any = _opt(
        {"chunks": [{"doc_id": "Tutorial_2", "page_no": 8}]},
        "Structured tool result returned to the model.",
    )
    command: list[str] = _ex(
        [],
        "Exact command line as an argument vector; empty when the tool has none.",
    )
    exit_code: int | None = _opt(None, "Process exit code; null while running.")
    output: str | None = _opt("3 course chunks", "Truncated tool output.")
    duration_ms: int | None = _opt(42, "Tool execution time in milliseconds.")
    status: Literal["running", "done", "failed"] = _ex(
        "done",
        "Tool state; one of running, done, or failed.",
    )


class MessageEventRecord(BaseModel):
    model_config = _example(MESSAGE_EVENT_EXAMPLE)

    kind: Literal["reasoning", "tool_call"] = _ex(
        "reasoning", "Work-chain event kind; reasoning or tool_call."
    )
    reasoning: str | None = _opt(
        None, "Reasoning text for a reasoning event; null for a tool call."
    )
    tool_call: ToolCallRecord | None = _opt(
        None, "The tool call for a tool_call event; null for reasoning."
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
    reasoning: str | None = _opt(
        None,
        "Streamed model thinking for assistant messages; null when the model "
        "produced none or the message predates turn metadata.",
    )
    model: str | None = _opt(
        "deepseek-flash",
        "Resolved model id for assistant messages; null for user messages or "
        "legacy answers.",
    )
    thinking: str | None = _opt(
        "high",
        "Effective thinking level for assistant messages; null for user "
        "messages or legacy answers.",
    )
    work_steps: list[WorkStepRecord] = _ex(
        [WORK_STEP_EXAMPLE],
        "Ordered work-chain steps for assistant messages; empty for user "
        "messages and legacy answers.",
    )
    citations: list[MessageCitationRecord] = _ex(
        [{**CITATION_EXAMPLE, "bbox_norm": None}],
        "Page citations carried by the answer, in display order.",
    )
    tool_calls: list[ToolCallRecord] = _ex(
        [TOOL_CALL_EXAMPLE],
        "Tool calls executed for the answer, in display order.",
    )
    events: list[MessageEventRecord] = _ex(
        [MESSAGE_EVENT_EXAMPLE],
        "Ordered work-chain events: reasoning segments and tool calls, in the "
        "order the model produced them.",
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


class MessageCitationRecord(CitationRecord):
    model_config = _example({**CITATION_EXAMPLE, "bbox_norm": [0.1, 0.2, 0.3, 0.4]})

    bbox_norm: list[float] | None = _opt(
        [0.1, 0.2, 0.3, 0.4],
        "Normalized page box [x1, y1, x2, y2] for the evidence panel, when the "
        "citation carries one.",
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


FOLDER_ID = "6f1a2b3c4d5e"
DOC_EXAMPLE = {
    "id": "ACS_Lecture_1_2026F",
    "title": "ACS_Lecture_1_2026F",
    "filename": "ACS_Lecture_1_2026F.pdf",
    "folder_id": None,
    "page_count": 67,
    "chunk_count": 71,
    "byte_size": 10470744,
    "status": "ready",
    "status_detail": None,
    "summary": "A lecture on GPU architecture and CUDA execution.",
    "summary_model": "qwen3.8-27b",
    "created_at": "2026-11-05T04:00:00+00:00",
    "indexed_at": "2026-11-05T04:20:00+00:00",
    "pdf_url": "/api/knowledge/documents/ACS_Lecture_1_2026F/file",
    "thumbnail_url": "/api/corpus/ACS_Lecture_1_2026F/pages/1.webp",
}


class FolderPathSegment(BaseModel):
    id: str = _ex(FOLDER_ID, "Folder id.")
    name: str = _ex("Lectures", "Folder name.")


class KnowledgeFolderRecord(BaseModel):
    model_config = _example(
        {
            "id": FOLDER_ID,
            "name": "Lectures",
            "parent_id": None,
            "position": 0,
            "created_at": "2026-11-05T04:00:00+00:00",
            "file_count": 3,
            "path": [{"id": FOLDER_ID, "name": "Lectures"}],
        }
    )

    id: str = _ex(FOLDER_ID, "Folder id.")
    name: str = _ex("Lectures", "Folder name.")
    parent_id: str | None = _opt(None, "Parent folder; null for the root.")
    position: int = _ex(0, "Sort order among the siblings of one parent.")
    created_at: str = _ex("2026-11-05T04:00:00+00:00", "ISO-8601 UTC creation time.")
    file_count: int = _ex(3, "Documents directly in this folder.")
    path: list[FolderPathSegment] = _ex(
        [{"id": FOLDER_ID, "name": "Lectures"}],
        "Ancestors from the root, used for the breadcrumb.",
    )


class FolderTreeResponse(BaseModel):
    model_config = _example(
        {
            "folders": [
                {
                    "id": FOLDER_ID,
                    "name": "Lectures",
                    "parent_id": None,
                    "position": 0,
                    "created_at": "2026-11-05T04:00:00+00:00",
                    "file_count": 3,
                    "path": [{"id": FOLDER_ID, "name": "Lectures"}],
                }
            ],
            "total_files": 12,
        }
    )

    folders: list[KnowledgeFolderRecord] = _ex([], "Folders, root first then children.")
    total_files: int = _ex(12, "Documents in the whole archive.")


class KnowledgeDocumentRecord(BaseModel):
    model_config = _example(DOC_EXAMPLE)

    id: str = _ex("ACS_Lecture_1_2026F", "Document id (the PDF stem).")
    title: str = _ex("ACS_Lecture_1_2026F", "Title the browser shows.")
    filename: str = _ex("ACS_Lecture_1_2026F.pdf", "Original PDF file name.")
    folder_id: str | None = _opt(None, "Folder that holds the file; null is the root.")
    page_count: int = _ex(67, "Pages the OCR pipeline parsed.")
    chunk_count: int = _ex(71, "Chunks stored for the document.")
    byte_size: int | None = _opt(10470744, "Source PDF size in bytes.")
    status: Literal[
        "uploading", "uploaded", "upload_failed", "processing", "ready", "failed"
    ] = _ex("ready", "Ingestion status the tile renders.")
    status_detail: str | None = _opt(None, "Failure reason or progress note.")
    summary: str | None = _opt(
        "A lecture on GPU architecture and CUDA execution.",
        "Qwen document summary; null until the summary job lands.",
    )
    summary_model: str | None = _opt("qwen3.8-27b", "Model that wrote the summary.")
    created_at: str = _ex("2026-11-05T04:00:00+00:00", "ISO-8601 UTC ingestion time.")
    indexed_at: str | None = _opt(
        "2026-11-05T04:20:00+00:00", "ISO-8601 UTC time chunks and vectors were stored."
    )
    pdf_url: str = _ex(
        "/api/knowledge/documents/ACS_Lecture_1_2026F/file",
        "Route that serves the source PDF.",
    )
    thumbnail_url: str = _ex(
        "/api/corpus/ACS_Lecture_1_2026F/pages/1.webp",
        "First-page image used as the tile icon.",
    )


class DocumentListResponse(BaseModel):
    model_config = _example({"documents": [DOC_EXAMPLE], "total": 1})

    documents: list[KnowledgeDocumentRecord] = _ex([], "Page of documents.")
    total: int = _ex(1, "Documents in the requested folder.")


class SearchMatchRecord(BaseModel):
    model_config = _example(
        {
            "kind": "content",
            "page_no": 12,
            "snippet": "The allreduce operation combines gradients.",
            "highlights": [[4, 13]],
        }
    )

    kind: Literal["filename", "folder", "summary", "content"] = _ex(
        "content", "Why the document matched."
    )
    page_no: int | None = _opt(12, "Page number for a content match.")
    snippet: str = _ex(
        "The allreduce operation combines gradients.", "Text around the match."
    )
    highlights: list[list[int]] = _ex(
        [[4, 13]], "Half-open [start, end) ranges to mark inside the snippet."
    )


class SearchDocumentRecord(KnowledgeDocumentRecord):
    model_config = _example({**DOC_EXAMPLE, "matches": []})

    matches: list[SearchMatchRecord] = _ex([], "Matches for this document, best first.")


class KnowledgeSearchResponse(BaseModel):
    model_config = _example({"query": "allreduce", "documents": []})

    query: str = _ex("allreduce", "The query as submitted.")
    documents: list[SearchDocumentRecord] = _ex([], "Documents that matched.")


class KnowledgeFolderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64, examples=["Lectures"])
    parent_id: str | None = Field(default=None, examples=[None])


class KnowledgeFolderPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=64)
    parent_id: str | None = Field(default=None)


class KnowledgeDocumentPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    folder_id: str | None = Field(default=None, examples=[None])


class DeleteDocumentResponse(BaseModel):
    model_config = _example({"id": "ACS_Lecture_1_2026F", "deleted": True})

    id: str = _ex("ACS_Lecture_1_2026F", "Document that was deleted.")
    deleted: bool = _ex(True, "Always true on success.")


class DeleteFolderResponse(BaseModel):
    model_config = _example({"deleted_documents": 3})

    deleted_documents: int = _ex(3, "Documents removed with the folder.")


class RetrievalChunkRecord(BaseModel):
    model_config = _example(
        {
            "chunk_id": "ACS_Lecture_1_2026F:p012:c00",
            "doc_id": "ACS_Lecture_1_2026F",
            "page_no": 12,
            "section": "Collective operations",
            "text": "The allreduce operation combines gradients.",
            "bbox_norm": [0.1, 0.2, 0.9, 0.6],
            "score": 0.032522,
            "sources": ["lexical", "dense"],
        }
    )

    chunk_id: str = _ex("ACS_Lecture_1_2026F:p012:c00", "Chunk id.")
    doc_id: str = _ex("ACS_Lecture_1_2026F", "Document id.")
    page_no: int = _ex(12, "1-based page number.")
    section: str | None = _opt("Collective operations", "Slide title when known.")
    text: str = _ex(
        "The allreduce operation combines gradients.", "Chunk text."
    )
    bbox_norm: list[float] | None = _opt(
        [0.1, 0.2, 0.9, 0.6], "Union box for the page overlay."
    )
    score: float = _ex(0.032522, "Fused reciprocal-rank score.")
    sources: list[Literal["lexical", "dense"]] = _ex(
        ["lexical", "dense"], "Retrieval arms that returned the chunk."
    )


class RetrievalResponse(BaseModel):
    model_config = _example(
        {
            "query": "how are gradients combined",
            "keyword_query": "allreduce gradients",
            "need_retrieval": True,
            "lexical": True,
            "dense": True,
            "chunks": [],
        }
    )

    query: str = _ex("how are gradients combined", "The question as submitted.")
    keyword_query: str = _ex("allreduce gradients", "Query the lexical arm ran.")
    need_retrieval: bool = _ex(True, "False when the question needs no course material.")
    lexical: bool = _ex(True, "Whether the lexical arm returned anything.")
    dense: bool = _ex(True, "Whether the dense arm ran and returned anything.")
    chunks: list[RetrievalChunkRecord] = _ex([], "Fused top-k chunks, best first.")
