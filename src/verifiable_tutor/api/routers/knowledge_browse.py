"""Knowledge-base browser routes: folders, files, search, and PDF bytes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from ..deps import CurrentUser, KnowledgeDep, RetrieverDep
from ...knowledge.browse import _Invalid, _Missing
from ...evidence.query import plan_query
from ..schemas import (
    DeleteDocumentResponse,
    DeleteFolderResponse,
    DocumentListResponse,
    FolderTreeResponse,
    KnowledgeDocumentPatchBody,
    KnowledgeDocumentRecord,
    KnowledgeFolderBody,
    KnowledgeFolderPatchBody,
    KnowledgeFolderRecord,
    KnowledgeSearchResponse,
    RetrievalResponse,
)

router = APIRouter(tags=["knowledge"])


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, _Missing):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/api/knowledge/folders",
    response_model=FolderTreeResponse,
    summary="The knowledge-base folder tree",
    responses={401: {"description": "Not signed in."}},
)
def list_folders(user: CurrentUser, knowledge: KnowledgeDep):
    """Return every folder with its ancestor path and the archive file count."""

    return knowledge.folder_tree()


@router.post(
    "/api/knowledge/folders",
    status_code=201,
    response_model=KnowledgeFolderRecord,
    summary="Create a folder",
    responses={
        400: {"description": "Empty name or unknown parent folder."},
        401: {"description": "Not signed in."},
    },
)
def create_folder(body: KnowledgeFolderBody, user: CurrentUser, knowledge: KnowledgeDep):
    """Create a folder at the root or under another folder."""

    try:
        return knowledge.create_folder(name=body.name, parent_id=body.parent_id)
    except ValueError as exc:
        raise _handle(exc) from exc


@router.patch(
    "/api/knowledge/folders/{folder_id}",
    response_model=KnowledgeFolderRecord,
    summary="Rename or move a folder",
    responses={
        400: {"description": "Unknown parent or a move under the folder's own descendant."},
        401: {"description": "Not signed in."},
        404: {"description": "Folder not found."},
    },
)
def update_folder(
    folder_id: str,
    body: KnowledgeFolderPatchBody,
    user: CurrentUser,
    knowledge: KnowledgeDep,
):
    """Rename a folder, move it, or both."""

    try:
        return knowledge.update_folder(
            folder_id,
            name=body.name,
            parent_id=body.parent_id,
            parent_given="parent_id" in body.model_fields_set,
        )
    except (ValueError, _Missing, _Invalid) as exc:
        raise _handle(exc) from exc


@router.delete(
    "/api/knowledge/folders/{folder_id}",
    response_model=DeleteFolderResponse,
    summary="Soft-delete a folder and the files inside it",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Folder not found."},
    },
)
def delete_folder(folder_id: str, user: CurrentUser, knowledge: KnowledgeDep):
    """Hide a folder subtree; rows, PDFs, chunks, and vectors stay on disk."""

    try:
        return knowledge.delete_folder(folder_id)
    except _Missing as exc:
        raise _handle(exc) from exc


@router.get(
    "/api/knowledge/documents",
    response_model=DocumentListResponse,
    summary="List the files in one folder",
    responses={401: {"description": "Not signed in."}},
)
def list_documents(
    user: CurrentUser,
    knowledge: KnowledgeDep,
    folder_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """List one folder's documents; omit ``folder_id`` for the root."""

    items, total = knowledge.list_documents(
        folder_id=folder_id, limit=limit, offset=offset
    )
    return {"documents": items, "total": total}


@router.get(
    "/api/knowledge/documents/{doc_id}",
    response_model=KnowledgeDocumentRecord,
    summary="One file's metadata, summary, and counts",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Document not found."},
    },
)
def get_document(doc_id: str, user: CurrentUser, knowledge: KnowledgeDep):
    """Return one document record."""

    try:
        return knowledge.document(doc_id)
    except _Missing as exc:
        raise _handle(exc) from exc


@router.patch(
    "/api/knowledge/documents/{doc_id}",
    response_model=KnowledgeDocumentRecord,
    summary="Move a file to another folder",
    responses={
        400: {"description": "Unknown folder."},
        401: {"description": "Not signed in."},
        404: {"description": "Document not found."},
    },
)
def move_document(
    doc_id: str,
    body: KnowledgeDocumentPatchBody,
    user: CurrentUser,
    knowledge: KnowledgeDep,
):
    """Move one document; ``folder_id`` null moves it to the root."""

    if "folder_id" not in body.model_fields_set:
        raise HTTPException(status_code=400, detail="folder_id is required")
    try:
        return knowledge.move_document(doc_id, folder_id=body.folder_id)
    except (_Missing, _Invalid) as exc:
        raise _handle(exc) from exc


@router.delete(
    "/api/knowledge/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    summary="Soft-delete a file",
    responses={
        401: {"description": "Not signed in."},
        404: {"description": "Document not found."},
    },
)
def delete_document(doc_id: str, user: CurrentUser, knowledge: KnowledgeDep):
    """Hide a document; its row, chunks, vectors, and mirror files stay on disk."""

    try:
        document = knowledge.delete_document(doc_id)
    except _Missing as exc:
        raise _handle(exc) from exc
    return {"id": document["id"], "deleted": True}


@router.get(
    "/api/knowledge/search",
    response_model=KnowledgeSearchResponse,
    summary="Search file names, folders, page text, and summaries",
    responses={401: {"description": "Not signed in."}},
)
def search(
    user: CurrentUser,
    knowledge: KnowledgeDep,
    q: Annotated[str, Query(min_length=0, max_length=200)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Return matching documents with the reason and the highlight ranges."""

    return knowledge.search(q, limit=limit)


@router.get(
    "/api/knowledge/documents/{doc_id}/file",
    summary="The source PDF",
    responses={
        200: {
            "description": "The source PDF as served to the preview.",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        },
        401: {"description": "Not signed in."},
        404: {"description": "Document or file not found."},
        422: {"description": "Invalid document id."},
    },
)
def document_file(doc_id: str, user: CurrentUser, knowledge: KnowledgeDep):
    """Serve the source PDF from the local mirror."""

    try:
        path = knowledge.pdf_path(doc_id)
    except _Invalid as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except _Missing as exc:
        raise _handle(exc) from exc
    return FileResponse(path, media_type="application/pdf", filename=f"{doc_id}.pdf")


def _optional_model(request: Request) -> object | None:
    """Return the model adapter, or None when the model layer is not set up."""

    from ..deps import get_model

    try:
        return get_model(request)
    except HTTPException:
        return None


@router.get(
    "/api/knowledge/retrieve",
    response_model=RetrievalResponse,
    summary="Hybrid retrieval over the course chunks",
    responses={
        401: {"description": "Not signed in."},
        422: {"description": "Invalid k or an over-long question."},
    },
)
def retrieve(
    request: Request,
    user: CurrentUser,
    retriever: RetrieverDep,
    q: Annotated[str, Query(min_length=0, max_length=500)] = "",
    k: Annotated[int, Query(ge=1, le=50)] = 8,
):
    """Run the rewrite, both arms, and reciprocal rank fusion.

    This stage returns chunks and never writes a prompt or a citation; the chat
    tool and the citation module are recorded as TODO in ADR-0015.
    """

    plan = plan_query(_optional_model(request), q)
    result = retriever.search(plan, k=k)
    return {
        "query": q,
        "keyword_query": plan.keyword_query,
        "need_retrieval": plan.need_retrieval,
        "lexical": result.lexical,
        "dense": result.dense,
        "chunks": result.chunks,
    }
