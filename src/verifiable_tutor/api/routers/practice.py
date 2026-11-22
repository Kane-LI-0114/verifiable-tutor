"""Practice question generation and model grading.

Generation runs through the agent loop (``generate_practice``). Grading runs
through the online model (``grade_answer``): code answers are judged on their
logic, not executed on TACC, so no ``tacc/exec`` job is required.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from ..deps import ChatDep, ClockDep, CurrentUser, ModelDep, StorageDep
from ...practice.grading import grade_answer

router = APIRouter(tags=["practice"])


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
    types: list[str] | None = Field(
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


class TopicProgressBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1, description="The topic.")
    covered_points: list[str] = Field(
        default_factory=list, description="Knowledge points the quiz covered."
    )
    mastered_points: list[str] = Field(
        default_factory=list,
        description="Knowledge points answered with full marks.",
    )


class PracticeSessionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1, max_length=200, description="The topic.")
    content: str = Field(min_length=1, description="The rendered result, markdown.")
    sources: list[dict] = Field(
        default_factory=list, description="The numbered course sources."
    )
    progress: list[TopicProgressBody] = Field(
        default_factory=list, description="Per-topic knowledge-point progress."
    )


@router.post(
    "/api/practice/sessions",
    status_code=201,
    summary="Save a practice session so it appears in the conversation list",
    responses={401: {"description": "Not signed in."}},
)
def save_practice_session(
    user: CurrentUser,
    body: PracticeSessionBody,
    storage: StorageDep,
    clock: ClockDep,
):
    """Persist a finished practice result as a conversation."""

    conversation_id = uuid.uuid4().hex
    storage.create_conversation(
        conversation_id=conversation_id,
        user_id=user["id"],
        title=body.topic,
        created_at=clock(),
        kind="practice",
    )
    storage.add_assistant_turn(
        message_id=uuid.uuid4().hex,
        conversation_id=conversation_id,
        sequence=1,
        content=body.content,
        created_at=clock(),
        sources=body.sources,
    )
    for entry in body.progress:
        storage.record_progress(
            user_id=user["id"],
            topic=entry.topic,
            covered_points=entry.covered_points,
            mastered_points=entry.mastered_points,
        )
    return {"session_id": conversation_id}
