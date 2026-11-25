"""Practice question generation and model grading.

Generation runs through the agent loop (``generate_practice``). Grading runs
through the online model (``grade_answer``): code answers are judged on their
logic, not executed on TACC, so no ``tacc/exec`` job is required.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ..deps import ChatDep, ClockDep, CurrentUser, ModelDep, StorageDep
from ...policy.deadline import load_deadlines
from ...storage import PracticeAttemptOpenError
from ...policy.guard import guard
from ...practice.grading import grade_answer
from ...practice.sessions import UnknownQuestionError, submit_attempt
from ...prompts import load_prompt

router = APIRouter(tags=["practice"])

PracticeQuestionType = Literal[
    "single-choice",
    "multiple-choice",
    "true-false",
    "short-answer",
    "code",
]


class PracticeRunBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, description="The question text.")
    answer: str = Field(min_length=1, description="The student's answer.")
    reference_answer: str = Field(
        min_length=1, description="The reference answer to grade against."
    )
    scoring_points: list[str] = Field(
        default_factory=list, description="Itemized scoring points."
    )
    max_score: float = Field(gt=0, description="Maximum score.")
    sources: list[dict] = Field(
        default_factory=list, description="The numbered course sources."
    )


@router.post(
    "/api/practice/runs",
    summary="Grade a practice answer with the online model",
    responses={401: {"description": "Not signed in."}},
)
def submit_practice_run(user: CurrentUser, body: PracticeRunBody, model: ModelDep):
    """Grade the student answer against the reference answer and scoring points."""

    result = grade_answer(
        question=body.question,
        student_answer=body.answer,
        reference_answer=body.reference_answer,
        scoring_points=body.scoring_points,
        max_score=body.max_score,
        sources=body.sources,
        adapter=model,
    )
    return {
        "score": result.score,
        "max_score": result.max_score,
        "explanation": result.explanation,
    }


class PracticeGenerateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(
        min_length=1,
        max_length=200,
        description="Course topic to generate self-test questions for.",
    )
    types: list[PracticeQuestionType] | None = Field(
        default=None,
        description="Question types to generate, for example [\"single-choice\", \"code\"].",
    )


@router.post(
    "/api/practice/generate",
    summary="Generate self-test questions for a topic",
    responses={401: {"description": "Not signed in."}},
)
def generate_practice_questions(
    user: CurrentUser,
    body: PracticeGenerateBody,
    chat: ChatDep,
    model: ModelDep,
):
    """Generate self-test questions through the agent loop."""

    questions, sources = chat.generate_practice(
        body.topic, adapter=model, types=body.types
    )
    return {
        "questions": [asdict(question) for question in questions],
        "sources": sources,
    }


class PracticeCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(
        min_length=1,
        max_length=200,
        description="Course topic to generate self-test questions for.",
    )
    types: list[PracticeQuestionType] | None = Field(
        default=None,
        description="Question types to generate, for example [\"single-choice\"].",
    )


class PracticeResultBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, description="Points earned on the question.")
    max_score: float = Field(gt=0, description="Maximum points of the question.")
    explanation: str = Field(default="", description="Feedback shown to the student.")


class PracticeAnswersBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Question id to the selected choices or typed answer.",
    )


class PracticeSubmitBody(PracticeAnswersBody):
    results: dict[str, PracticeResultBody] = Field(
        default_factory=dict,
        description="Question id to its stored grading result.",
    )


class PracticeQuestionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Stable question id inside the session, q1..qN.")
    type: str = Field(description="Question type, for example single-choice.")
    topic: str = Field(description="Course topic the question belongs to.")
    question: str = Field(description="Question stem.")
    choices: list[str] = Field(default_factory=list, description="Selectable choices.")
    correct_answer: str = Field(
        default="", description="Exact correct choice text for objective questions."
    )
    reference_answer: str = Field(description="Reference answer used for grading.")
    scoring_points: list[str] = Field(default_factory=list)
    max_score: float = Field(description="Maximum points of the question.")
    knowledge_points: list[str] = Field(default_factory=list)


class PracticeAttemptRecord(BaseModel):
    attempt_no: int = Field(description="1-based attempt number.")
    status: Literal["in_progress", "completed"] = Field(
        description="Whether this attempt is still open or submitted."
    )
    answers: dict[str, list[str]] = Field(default_factory=dict)
    results: dict[str, PracticeResultBody] = Field(default_factory=dict)
    option_orders: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Question id to the choice order shown in this attempt.",
    )
    score: float | None = Field(default=None, description="Total score; null while open.")
    max_score: float = Field(description="Maximum total score of the session.")
    started_at: str = Field(description="ISO-8601 UTC time the attempt opened.")
    submitted_at: str | None = Field(
        default=None, description="ISO-8601 UTC submission time; null while open."
    )


class PracticeSessionRecord(BaseModel):
    id: str = Field(description="Practice conversation id.")
    title: str | None = Field(default=None, description="Sidebar title.")
    topic: str = Field(description="Topic the questions were generated for.")
    status: Literal["not_started", "in_progress", "completed"] = Field(
        description="Session status, decided by the first attempt only."
    )
    best_score: float = Field(description="Highest total score across attempts.")
    max_score: float = Field(description="Sum of every question's maximum score.")
    questions: list[PracticeQuestionRecord] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    attempts: list[PracticeAttemptRecord] = Field(default_factory=list)
    created_at: str = Field(description="ISO-8601 UTC generation time.")
    updated_at: str = Field(description="ISO-8601 UTC last activity time.")
    completed_at: str | None = Field(
        default=None, description="When the first attempt was submitted."
    )


class PracticeSaveResponse(BaseModel):
    status: Literal["not_started", "in_progress", "completed"]
    attempt_no: int


def _practice_conversation(storage, user: dict, session_id: str) -> dict:
    conversation = storage.find_conversation(session_id)
    if (
        conversation is None
        or conversation["user_id"] != user["id"]
        or conversation["kind"] != "practice"
    ):
        raise HTTPException(status_code=404, detail="practice session not found")
    return conversation


def _session_payload(storage, conversation: dict) -> dict:
    session = storage.find_practice_session(conversation["id"])
    if session is None:
        raise HTTPException(status_code=404, detail="practice session not found")
    return {
        "id": conversation["id"],
        "title": conversation["title"],
        "topic": session["topic"],
        "status": session["status"],
        "best_score": session["best_score"],
        "max_score": session["max_score"],
        "questions": session["questions"],
        "sources": session["sources"],
        "attempts": storage.list_practice_attempts(conversation["id"]),
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "completed_at": session["completed_at"],
    }


def _attempt_or_409(storage, session_id: str, attempt_no: int) -> dict:
    attempt = storage.find_practice_attempt(session_id, attempt_no)
    if attempt is None:
        raise HTTPException(status_code=404, detail="attempt not found")
    if attempt["status"] != "in_progress":
        raise HTTPException(status_code=409, detail="attempt is already submitted")
    return attempt


@router.post(
    "/api/practice/sessions",
    status_code=201,
    response_model=PracticeSessionRecord,
    summary="Generate and save a practice session",
    responses={
        401: {"description": "Not signed in."},
        502: {"description": "The model returned no usable questions."},
    },
)
def create_practice_session(
    user: CurrentUser,
    body: PracticeCreateBody,
    chat: ChatDep,
    model: ModelDep,
    storage: StorageDep,
    clock: ClockDep,
):
    """Generate the questions and persist them before the first answer.

    Saving at generation time is what makes a reload resume the session; an
    empty generation stores nothing so the sidebar never fills with blanks.
    """

    questions, sources = chat.generate_practice(
        body.topic, adapter=model, types=body.types
    )
    if not questions:
        raise HTTPException(
            status_code=502, detail="question generation returned no questions"
        )
    now = clock()
    conversation_id = uuid.uuid4().hex
    storage.create_practice_session(
        conversation_id=conversation_id,
        user_id=user["id"],
        title=f"{body.topic} {now:%Y%m%d}",
        topic=body.topic,
        questions=[asdict(question) for question in questions],
        sources=sources,
        created_at=now,
    )
    conversation = storage.find_conversation(conversation_id)
    assert conversation is not None
    return _session_payload(storage, conversation)


@router.get(
    "/api/practice/sessions/{session_id}",
    response_model=PracticeSessionRecord,
    summary="Load a practice session with its attempts",
    responses={401: {"description": "Not signed in."}, 404: {"description": "Not found."}},
)
def get_practice_session(
    session_id: str, user: CurrentUser, storage: StorageDep
):
    conversation = _practice_conversation(storage, user, session_id)
    return _session_payload(storage, conversation)


@router.patch(
    "/api/practice/sessions/{session_id}/attempts/{attempt_no}/answers",
    response_model=PracticeSaveResponse,
    summary="Autosave the answers of one attempt",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Not found."},
        409: {"description": "The attempt is already submitted."},
    },
)
def save_practice_answers(
    session_id: str,
    attempt_no: int,
    body: PracticeAnswersBody,
    user: CurrentUser,
    storage: StorageDep,
    clock: ClockDep,
):
    """Persist the current answers so a reload resumes the attempt."""

    _practice_conversation(storage, user, session_id)
    _attempt_or_409(storage, session_id, attempt_no)
    storage.save_practice_answers(
        conversation_id=session_id,
        attempt_no=attempt_no,
        answers=body.answers,
        updated_at=clock(),
    )
    session = storage.find_practice_session(session_id)
    assert session is not None
    return {"status": session["status"], "attempt_no": attempt_no}


@router.post(
    "/api/practice/sessions/{session_id}/attempts/{attempt_no}/submit",
    response_model=PracticeSessionRecord,
    summary="Submit and grade one attempt",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Not found."},
        409: {"description": "The attempt is already submitted."},
    },
)
def submit_practice_attempt(
    session_id: str,
    attempt_no: int,
    body: PracticeSubmitBody,
    user: CurrentUser,
    storage: StorageDep,
    clock: ClockDep,
):
    """Store the grading result of an attempt.

    The first attempt completes the session and records knowledge-point
    progress; later attempts only contribute to the best score.
    """

    conversation = _practice_conversation(storage, user, session_id)
    _attempt_or_409(storage, session_id, attempt_no)
    session = storage.find_practice_session(session_id)
    assert session is not None
    try:
        submit_attempt(
            storage=storage,
            session_id=session_id,
            topic=session["topic"],
            questions=session["questions"],
            attempt_no=attempt_no,
            answers=body.answers,
            results={
                question_id: {
                    "score": result.score,
                    "max_score": result.max_score,
                    "explanation": result.explanation,
                }
                for question_id, result in body.results.items()
            },
            user_id=user["id"],
            submitted_at=clock(),
        )
    except UnknownQuestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    refreshed = storage.find_conversation(session_id)
    assert refreshed is not None
    return _session_payload(storage, refreshed)


@router.post(
    "/api/practice/sessions/{session_id}/attempts",
    status_code=201,
    response_model=PracticeSessionRecord,
    summary="Start another attempt",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Not found."},
        409: {"description": "The first attempt is not submitted yet."},
    },
)
def start_practice_attempt(
    session_id: str, user: CurrentUser, storage: StorageDep, clock: ClockDep
):
    """Open a new attempt; the session status stays decided by attempt one."""

    conversation = _practice_conversation(storage, user, session_id)
    session = storage.find_practice_session(session_id)
    assert session is not None
    if session["status"] != "completed":
        raise HTTPException(
            status_code=409, detail="submit the first attempt before a redo"
        )
    try:
        storage.start_practice_attempt(
            conversation_id=session_id, started_at=clock()
        )
    except PracticeAttemptOpenError:
        raise HTTPException(
            status_code=409,
            detail="finish the open attempt before starting another",
        )
    return _session_payload(storage, conversation)


@router.delete(
    "/api/practice/sessions/{session_id}/attempts/{attempt_no}",
    status_code=204,
    summary="Delete one attempt, and the session when no attempt remains",
    responses={401: {"description": "Not signed in."}, 404: {"description": "Not found."}},
)
def delete_practice_attempt(
    session_id: str,
    attempt_no: int,
    user: CurrentUser,
    storage: StorageDep,
    clock: ClockDep,
):
    """Remove one attempt; the practice disappears only with its last attempt."""

    _practice_conversation(storage, user, session_id)
    if storage.find_practice_attempt(session_id, attempt_no) is None:
        raise HTTPException(status_code=404, detail="attempt not found")
    storage.delete_practice_attempt(
        conversation_id=session_id,
        attempt_no=attempt_no,
        updated_at=clock(),
    )
    return None


@router.delete(
    "/api/practice/sessions/{session_id}",
    status_code=204,
    summary="Delete a practice session and all of its attempts",
    responses={401: {"description": "Not signed in."}, 404: {"description": "Not found."}},
)
def delete_practice_session(
    session_id: str, user: CurrentUser, storage: StorageDep
):
    conversation = storage.find_conversation(session_id)
    if conversation is None or conversation["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="practice session not found")
    if conversation["kind"] == "practice":
        storage.delete_conversation(session_id, user["id"])
    else:
        raise HTTPException(status_code=404, detail="practice session not found")
    return None


class ParsePracticeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000, description="The user message.")


@router.post(
    "/api/practice/parse",
    summary="Decide whether a message asks to practice and extract topic and types",
    responses={401: {"description": "Not signed in."}},
)
def parse_practice_request(
    user: CurrentUser,
    body: ParsePracticeBody,
    model: ModelDep,
    clock: ClockDep,
    request: Request,
):
    """Parse a chat message into a practice request, if it is one."""

    settings = request.app.state.settings
    deadlines = load_deadlines(settings.repo_root / "config" / "deadlines.yaml")
    if guard(body.message, now=clock(), deadlines=deadlines).blocked:
        return {"practice": False, "blocked": True}

    prompt = load_prompt("practice_parse").replace("%%MESSAGE%%", body.message)
    result = model.chat(
        [{"role": "user", "content": prompt}], role="chat", temperature=0.0
    )
    text = (result.text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    data: dict = {}
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            data = {}
    return {
        "practice": bool(data.get("practice")),
        "topic": str(data.get("topic", "")),
        "types": [str(item) for item in (data.get("types") or [])],
    }
