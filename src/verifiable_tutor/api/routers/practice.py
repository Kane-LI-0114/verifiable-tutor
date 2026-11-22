"""Practice question generation and model grading.

Generation runs through the agent loop (``generate_practice``). Grading runs
through the online model (``grade_answer``): code answers are judged on their
logic, not executed on TACC, so no ``tacc/exec`` job is required.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from ..deps import ChatDep, CurrentUser, ModelDep
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
