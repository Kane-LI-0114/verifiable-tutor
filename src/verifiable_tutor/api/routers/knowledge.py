"""Knowledge-base routes: card browsing and build lifecycle."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from ..deps import BuildsDep, CardsDep, CurrentUser, Instructor
from ...knowledge.service import KnowledgeBuildError

router = APIRouter(tags=["knowledge"])


class BuildBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str | None = None
    max_chunks: int | None = None


@router.get("/api/knowledge/cards")
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


@router.post("/api/knowledge/builds", status_code=202)
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


@router.get("/api/knowledge/builds")
def list_builds(instructor: Instructor, builds: BuildsDep):
    """List knowledge-base builds, newest first."""

    return {"builds": builds.list()}


@router.get("/api/knowledge/builds/{build_id}")
def get_build(build_id: str, instructor: Instructor, builds: BuildsDep):
    """Return one build's state, job id, and record count."""

    try:
        return builds.get(build_id)
    except KnowledgeBuildError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
