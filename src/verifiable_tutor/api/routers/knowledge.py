"""Knowledge-base routes: card browsing and build lifecycle."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..deps import BuildsDep, CardsDep, CurrentUser, Instructor
from ...knowledge.service import KnowledgeBuildError
from ..schemas import (
    BuildAcceptedResponse,
    BuildListResponse,
    BuildRecord,
    CardsResponse,
)

router = APIRouter(tags=["knowledge"])


class BuildBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"doc_id": "course_project", "max_chunks": 8}
        },
    )

    doc_id: str | None = Field(
        default=None,
        description="Document id from the local page records; empty builds the configured file.",
        json_schema_extra={"example": "course_project"},
    )
    max_chunks: int | None = Field(
        default=None,
        description="Chunks to process; bounded by knowledge.max_chunks_per_job.",
        json_schema_extra={"example": 8},
    )


@router.get(
    "/api/knowledge/cards",
    response_model=CardsResponse,
    summary="Browse validated knowledge cards",
)
def list_cards(
    user: CurrentUser,
    cards: CardsDep,
    doc_id: str | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Browse validated knowledge cards with a simple filter and pagination."""

    items, total = cards.search(doc_id=doc_id, q=q, limit=limit, offset=offset)
    return {"cards": items, "total": total}


@router.post(
    "/api/knowledge/builds",
    status_code=202,
    response_model=BuildAcceptedResponse,
    summary="Queue a Qwen knowledge-base build",
    responses={
        400: {"description": "Invalid max_chunks value."},
        401: {"description": "Not signed in."},
        403: {"description": "Instructor role is required."},
        409: {"description": "Another build is already queued or running."},
        503: {"description": "knowledge.pages_path is not configured."},
    },
)
def create_build(
    body: BuildBody,
    instructor: Instructor,
    builds: BuildsDep,
    background: BackgroundTasks,
):
    """Queue one Qwen knowledge-base build for the local driver."""

    try:
        return builds.submit(
            instructor,
            doc_id=body.doc_id,
            max_chunks=body.max_chunks,
            background=background,
        )
    except KnowledgeBuildError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/api/knowledge/builds",
    response_model=BuildListResponse,
    summary="List knowledge-base builds",
)
def list_builds(instructor: Instructor, builds: BuildsDep):
    """List knowledge-base builds, newest first."""

    return {"builds": builds.list()}


@router.get(
    "/api/knowledge/builds/{build_id}",
    response_model=BuildRecord,
    summary="Knowledge-base build state",
    responses={
        401: {"description": "Not signed in."},
        403: {"description": "Instructor role is required."},
        404: {"description": "Build not found."},
    },
)
def get_build(build_id: str, instructor: Instructor, builds: BuildsDep):
    """Return one build's state, job id, and record count."""

    try:
        return builds.get(build_id)
    except KnowledgeBuildError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
