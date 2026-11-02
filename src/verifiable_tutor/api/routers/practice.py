"""Practice-run scaffold.

The route is part of the known interface surface, but execution needs the
``tacc/exec`` job (FR-E4), which does not exist yet. The documented 503 keeps
the contract stable until the job lands.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ..deps import CurrentUser

router = APIRouter(tags=["practice"])

PRACTICE_UNAVAILABLE = (
    "practice execution is not available: the tacc/exec job is pending (FR-E4)"
)


class PracticeRunBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    pack_id: str | None = None
    question_id: str | None = None
    answer: str | None = None


@router.post("/api/practice/runs")
def submit_practice_run(user: CurrentUser, body: PracticeRunBody | None = None):
    """Scaffold: report that TACC execution is not available yet."""

    raise HTTPException(status_code=503, detail=PRACTICE_UNAVAILABLE)
