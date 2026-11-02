"""Application factory and lifespan for the local FastAPI backend.

``create_app`` is the only place that constructs ``FastAPI``. Tests import the
factory, not ``main``, so importing the app under test never reads ``.env``.
Collaborators at network and subprocess boundaries can be injected so tests
never call a provider, an SMTP server, or TACC.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable

from fastapi import FastAPI

from . import API_VERSION
from ..auth.service import AuthService
from .chat import ChatService
from ..auth.email import EmailSender, build_email_sender
from ..knowledge.service import CardStore, DriverBuildRunner, KnowledgeBuildService
from .replay import ReplayService
from .routers import auth, chat, corpus, health, knowledge, practice, sessions, voice
from ..settings import AppSettings, ensure_runtime_directories, load_settings
from ..storage import Storage
from ..trace import SessionTrace, utc_now

AdapterFactory = Callable[[], Any]


def _default_adapter_factory(settings: AppSettings) -> AdapterFactory:
    def build() -> Any:
        from ..llm.adapter import ModelAdapter
        from ..llm.config import load_model_config

        resolved = load_model_config(
            settings.repo_root / "config" / "models.yaml",
            env_file=settings.repo_root / ".env",
            base_dir=settings.repo_root,
        )
        return ModelAdapter(resolved)

    return build


def create_app(
    settings: AppSettings | None = None,
    *,
    storage: Storage | None = None,
    clock: Callable[[], datetime] | None = None,
    sleep: Callable[[float], None] | None = None,
    adapter_factory: AdapterFactory | None = None,
    email_sender: EmailSender | None = None,
    build_runner: Any | None = None,
) -> FastAPI:
    """Build the application; collaborators are injected for tests."""

    resolved = settings if settings is not None else load_settings()
    resolved_clock = clock or utc_now
    resolved_sleep = sleep or time.sleep
    resolved_email = (
        email_sender if email_sender is not None else build_email_sender(resolved.smtp)
    )
    resolved_adapter_factory = (
        adapter_factory
        if adapter_factory is not None
        else _default_adapter_factory(resolved)
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_runtime_directories(resolved)
        database = storage or Storage(resolved.database_path)
        database.initialize()
        database.fail_interrupted_builds(updated_at=resolved_clock())
        app.state.settings = resolved
        app.state.storage = database
        trace = SessionTrace(resolved.trace_dir)
        app.state.trace = trace
        app.state.clock = resolved_clock
        app.state.sleep = resolved_sleep
        app.state.email_sender = resolved_email
        app.state.adapter_factory = resolved_adapter_factory
        runner = (
            build_runner
            if build_runner is not None
            else DriverBuildRunner(settings=resolved)
        )
        app.state.build_runner = runner
        app.state.model = None
        app.state.auth = AuthService(
            settings=resolved,
            storage=database,
            email_sender=resolved_email,
            clock=resolved_clock,
        )
        app.state.chat = ChatService(
            settings=resolved,
            storage=database,
            trace=trace,
            clock=resolved_clock,
        )
        app.state.replay = ReplayService(
            storage=database,
            trace=trace,
            sleep=resolved_sleep,
            default_speed=resolved.replay_default_speed,
        )
        app.state.cards = CardStore(resolved.knowledge_records_dir)
        app.state.builds = KnowledgeBuildService(
            settings=resolved,
            storage=database,
            runner=runner,
            clock=resolved_clock,
        )
        yield

    app = FastAPI(
        title="Verifiable Tutor API",
        version=API_VERSION,
        description=(
            "Local backend for the course-grounded tutoring agent: accounts, "
            "chat streaming and replay, knowledge cards and builds, corpus "
            "page images, and voice. TACC is reached only through submitted "
            "jobs; this API never exposes a TACC service."
        ),
        lifespan=lifespan,
    )
    router_modules: list[Any] = [
        health,
        auth,
        chat,
        sessions,
        voice,
        knowledge,
        corpus,
        practice,
    ]
    for module in router_modules:
        app.include_router(module.router)
    if (resolved.ui_static_dir / "index.html").is_file():
        app.frontend(
            "/",
            directory=str(resolved.ui_static_dir),
            fallback="auto",
            check_dir=False,
        )
    return app
