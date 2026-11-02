"""Corpus page images for the citation panel (FR-B5)."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse

from ..deps import CurrentUser, SettingsDep

router = APIRouter(tags=["corpus"])

_DOC_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@router.get(
    "/api/corpus/{doc_id}/pages/{page_no}.webp",
    summary="Rendered page image for the citation panel",
    responses={
        200: {
            "description": "Rendered page image.",
            "content": {
                "image/webp": {"schema": {"type": "string", "format": "binary"}}
            },
        },
        401: {"description": "Not signed in."},
        404: {"description": "Page image not found."},
        422: {"description": "Invalid document id or page number."},
    },
)
def page_image(
    doc_id: str,
    page_no: Annotated[int, Path(ge=1, le=9999)],
    user: CurrentUser,
    settings: SettingsDep,
):
    """Serve one rendered page WebP from the local OCR mirror."""

    if not _DOC_ID.fullmatch(doc_id):
        raise HTTPException(status_code=422, detail="invalid document id")
    filename = f"{doc_id}.p{page_no:03d}.webp"
    root = settings.corpus_images_dir.resolve()
    path = (root / filename).resolve()
    if root not in path.parents:
        raise HTTPException(status_code=422, detail="invalid page path")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="page image not found")
    return FileResponse(path, media_type="image/webp", filename=filename)
