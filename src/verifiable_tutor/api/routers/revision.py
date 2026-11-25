"""The revision guide tree, a document's review chapter, and self-check state."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Response

from ..deps import ClockDep, CurrentUser, StorageDep
from ..schemas import (
    RevisionDocumentDetail,
    RevisionProgressBody,
    RevisionProgressResponse,
    RevisionTreeResponse,
)

router = APIRouter(tags=["revision"])


class MarkdownResponse(Response):
    """A downloadable Markdown document with a documented media type."""

    media_type = "text/markdown"


@router.get(
    "/api/revision",
    response_model=RevisionTreeResponse,
    summary="The revision guide outline",
    responses={401: {"description": "Not signed in."}},
)
def revision_tree(user: CurrentUser, storage: StorageDep):
    """Return the stored outline with the user's three-level progress."""

    themes = storage.list_revision_tree(user["id"])
    return {
        "themes": themes,
        "total": sum(theme["total"] for theme in themes),
        "mastered": sum(theme["mastered"] for theme in themes),
    }


@router.get(
    "/api/revision/docs/{doc_id}",
    response_model=RevisionDocumentDetail,
    summary="One generated review chapter with its knowledge points",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Unknown document or chapter not generated yet."},
    },
)
def revision_document(doc_id: str, user: CurrentUser, storage: StorageDep):
    """Return the chapter and the signed-in user's self-check state."""

    detail = storage.revision_document_detail(doc_id, user["id"])
    if detail is None:
        raise HTTPException(status_code=404, detail="review chapter not generated")
    document = detail["document"]
    return {
        "doc_id": document["doc_id"],
        "title": document.get("title"),
        "filename": document.get("filename"),
        "category": document["category"],
        "theme_id": document["theme_id"],
        "theme_title": document.get("theme_title"),
        "intro_markdown": document.get("intro_markdown") or "",
        "model": document.get("model"),
        "generated_at": document.get("generated_at"),
        "total": detail["total"],
        "mastered": detail["mastered"],
        "points": detail["points"],
    }


@router.patch(
    "/api/revision/points/{point_id}",
    response_model=RevisionProgressResponse,
    summary="Mark one knowledge point as known or unknown",
    responses={401: {"description": "Not signed in."}, 404: {"description": "Not found."}},
)
def update_revision_point(
    point_id: str,
    body: RevisionProgressBody,
    user: CurrentUser,
    storage: StorageDep,
    clock: ClockDep,
):
    """Store one self-check and return the document's new counts."""

    result = storage.set_revision_progress(
        user_id=user["id"],
        point_id=point_id,
        mastered=body.mastered,
        updated_at=clock(),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="knowledge point not found")
    return result


@router.get(
    "/api/revision/docs/{doc_id}/markdown",
    response_class=MarkdownResponse,
    summary="Download one review chapter as Markdown",
    responses={
        200: {
            "description": "A clean Markdown file, with no internal page markers.",
            "content": {"text/markdown": {"schema": {"type": "string"}}},
        },
        401: {"description": "Not signed in."},
        404: {"description": "Unknown document or chapter not generated yet."},
    },
)
def download_revision_document(
    doc_id: str, user: CurrentUser, storage: StorageDep
):
    """Return the stored chapter as a downloadable Markdown file."""

    document = storage.find_revision_document(doc_id)
    if document is None or document.get("markdown") is None:
        raise HTTPException(status_code=404, detail="review chapter not generated")
    title = document.get("title") or doc_id
    body = f"# {title}\n\n{document['markdown']}"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", doc_id) or "revision"
    return MarkdownResponse(
        content=body,
        headers={"Content-Disposition": f'attachment; filename="{safe}.md"'},
    )
