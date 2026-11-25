"""The revision guide tree: themes and the documents grouped under them."""

from __future__ import annotations

from fastapi import APIRouter

from ..deps import CurrentUser, StorageDep
from ..schemas import RevisionTreeResponse

router = APIRouter(tags=["revision"])


@router.get(
    "/api/revision",
    response_model=RevisionTreeResponse,
    summary="The revision guide outline",
    responses={401: {"description": "Not signed in."}},
)
def revision_tree(user: CurrentUser, storage: StorageDep):
    """Return the stored outline as themes with their documents."""

    return {"themes": storage.list_revision_tree()}
