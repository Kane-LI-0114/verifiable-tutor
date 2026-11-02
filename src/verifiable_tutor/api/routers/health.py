"""Liveness endpoint for the local backend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import API_VERSION
from ..deps import get_storage
from ...storage import Storage

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health(storage: Storage = Depends(get_storage)) -> dict[str, str]:
    """Report liveness and the database connection state."""

    if not storage.ping():
        raise HTTPException(status_code=503, detail="database is not reachable")
    return {"status": "ok", "version": API_VERSION, "database": "ok"}
