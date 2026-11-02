"""Dependency wiring for the HTTP API.

Services are created once in the app lifespan, stored on ``app.state``, and
read here. The model adapter is created lazily on the first model-backed
request, because a backend without provider keys must still serve health,
accounts, knowledge browsing, and replay.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Callable

from fastapi import Depends, HTTPException, Request

from ..auth.service import AuthError, AuthService
from .chat import ChatService
from ..auth.email import EmailSender
from ..knowledge.service import CardStore, KnowledgeBuildService
from .replay import ReplayService
from ..settings import AppSettings
from ..storage import Storage
from ..trace import SessionTrace


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


def get_trace(request: Request) -> SessionTrace:
    return request.app.state.trace


def get_clock(request: Request) -> Callable[[], datetime]:
    return request.app.state.clock


def get_sleep(request: Request) -> Callable[[float], None]:
    return request.app.state.sleep


def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def get_chat(request: Request) -> ChatService:
    return request.app.state.chat


def get_email_sender(request: Request) -> EmailSender:
    return request.app.state.email_sender


def get_replay(request: Request) -> ReplayService:
    return request.app.state.replay


def get_cards(request: Request) -> CardStore:
    return request.app.state.cards


def get_builds(request: Request) -> KnowledgeBuildService:
    return request.app.state.builds


def get_current_user(
    request: Request, auth: AuthService = Depends(get_auth)
) -> dict[str, Any]:
    settings: AppSettings = request.app.state.settings
    cookie = request.cookies.get(settings.session_cookie_name)
    try:
        return auth.current_user(cookie)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def require_instructor(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if user.get("role") != "instructor":
        raise HTTPException(status_code=403, detail="instructor role is required")
    return user


def get_model(request: Request) -> Any:
    """Return the lazily created model adapter, or 503 when it is unusable."""

    model = getattr(request.app.state, "model", None)
    if model is None:
        factory = request.app.state.adapter_factory
        try:
            model = factory()
        except Exception as exc:  # missing keys or invalid model config
            raise HTTPException(
                status_code=503,
                detail=f"model layer is not configured: {exc}",
            ) from exc
        request.app.state.model = model
    return model


SettingsDep = Annotated[AppSettings, Depends(get_settings)]
StorageDep = Annotated[Storage, Depends(get_storage)]
TraceDep = Annotated[SessionTrace, Depends(get_trace)]
ClockDep = Annotated[Callable[[], datetime], Depends(get_clock)]
SleepDep = Annotated[Callable[[float], None], Depends(get_sleep)]
AuthDep = Annotated[AuthService, Depends(get_auth)]
ChatDep = Annotated[ChatService, Depends(get_chat)]
EmailDep = Annotated[EmailSender, Depends(get_email_sender)]
ReplayDep = Annotated[ReplayService, Depends(get_replay)]
CardsDep = Annotated[CardStore, Depends(get_cards)]
BuildsDep = Annotated[KnowledgeBuildService, Depends(get_builds)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
Instructor = Annotated[dict[str, Any], Depends(require_instructor)]
ModelDep = Annotated[Any, Depends(get_model)]
