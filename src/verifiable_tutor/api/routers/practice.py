"""Practice-run scaffold.

The route is part of the known interface surface, but execution needs the
``tacc/exec`` job (FR-E4), which does not exist yet. The documented 503 keeps
the contract stable until the job lands.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..deps import CurrentUser

router = APIRouter(tags=["practice"])

PRACTICE_UNAVAILABLE = (
    "practice execution is not available: the tacc/exec job is pending (FR-E4)"
)


class PracticeRunBody(BaseModel):
    model_config = ConfigDict(extra="allow")

    pack_id: str | None = Field(
        default=None,
        description="Practice pack id. Example: mpi-gemm.",
    )
    question_id: str | None = Field(
        default=None,
        description="Question id inside the pack. Example: q1.",
    )
    answer: str | None = Field(
        default=None,
        description=(
            "Student answer to run against the reference tests. "
            "Example: int x = 1;"
        ),
    )


@router.post(
    "/api/practice/runs",
    summary="Submit a practice run",
    responses={
        401: {"description": "Not signed in."},
        503: {"description": PRACTICE_UNAVAILABLE},
    },
)
def submit_practice_run(user: CurrentUser, body: PracticeRunBody | None = None):
    """Scaffold: report that TACC execution is not available yet."""

    raise HTTPException(status_code=503, detail=PRACTICE_UNAVAILABLE)
