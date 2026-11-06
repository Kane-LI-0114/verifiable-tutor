"""Application factory and lifespan for the local FastAPI backend.

``create_app`` is the only place that constructs ``FastAPI``. Tests import the
factory, not ``main``, so importing the app under test never reads ``.env``.
Collaborators at network and subprocess boundaries can be injected so tests
never call a provider, an SMTP server, or TACC.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from . import API_VERSION
from ..auth.service import AuthService
from .chat import ChatService
from ..auth.email import EmailSender, build_email_sender
from pathlib import Path

from ..corpus.store import KnowledgeStore
from ..evidence.embedding import LocalEmbedder
from ..evidence.retrieval import HybridRetriever
from ..knowledge.browse import KnowledgeBrowser
from ..knowledge.service import CardStore, DriverBuildRunner, KnowledgeBuildService
from ..orchestrator.builtin_tools import build_tool_registry
from .replay import ReplayService
from .routers import (
    auth,
    chat,
    corpus,
    health,
    knowledge,
    knowledge_browse,
    practice,
    sessions,
    voice,
)
from .schemas import OPENAPI_TAGS
from ..settings import AppSettings, ensure_runtime_directories, load_settings
from ..storage import Storage
from ..trace import SessionTrace, utc_now

AdapterFactory = Callable[[], Any]


def _build_embedder(settings: AppSettings) -> LocalEmbedder | None:
    """Build the local query embedder from ``config/models.yaml``, or None.

    The model is not loaded here; the embedder resolves it on the first query.
    A missing configuration or a missing model stack degrades retrieval to the
    lexical arm instead of failing startup.
    """

    try:
        from ..llm.config import load_model_config

        config = load_model_config(
            settings.repo_root / "config" / "models.yaml",
            env_file=settings.repo_root / ".env",
            base_dir=settings.repo_root,
        )
        embedding = config.config.embedding
    except Exception:  # no config, no keys, or a missing optional dependency
        return None
    model_path = Path(embedding.model_path).expanduser()
    return LocalEmbedder(
        model_path=str(model_path),
        device=embedding.device,
        max_length=embedding.max_length,
        batch_size=embedding.batch_size,
        dimension=embedding.dimension,
    )

logger = logging.getLogger(__name__)


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
    tool_registry: Any | None = None,
    docs_api_dir: str | Path | None = None,
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
    docs_root = (
        Path(docs_api_dir)
        if docs_api_dir is not None
        else Path(__file__).resolve().parents[3] / "docs" / "api"
    )
    local_docs = (
        (docs_root / "index.html").is_file()
        and (docs_root / "vendor" / "swagger-ui" / "swagger-ui-bundle.js").is_file()
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
        knowledge_store = KnowledgeStore(database)
        app.state.knowledge_store = knowledge_store
        retriever = HybridRetriever(
            store=knowledge_store, embedder=_build_embedder(resolved)
        )
        app.state.retriever = retriever
        registry = (
            tool_registry
            if tool_registry is not None
            else build_tool_registry(settings=resolved)
        )
        app.state.tool_registry = registry
        app.state.chat = ChatService(
            settings=resolved,
            storage=database,
            trace=trace,
            clock=resolved_clock,
            tool_registry=registry,
            retriever=retriever,
            knowledge_store=knowledge_store,
        )
        app.state.replay = ReplayService(
            storage=database,
            trace=trace,
            sleep=resolved_sleep,
            default_speed=resolved.replay_default_speed,
        )
        app.state.cards = CardStore(resolved.knowledge_records_dir)
        app.state.knowledge = KnowledgeBrowser(
            store=knowledge_store, settings=resolved, clock=resolved_clock
        )
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
        openapi_tags=OPENAPI_TAGS,
        docs_url=None,
        redoc_url=None,
    )
    router_modules: list[Any] = [
        health,
        auth,
        chat,
        sessions,
        voice,
        knowledge,
        knowledge_browse,
        corpus,
        practice,
    ]
    for module in router_modules:
        app.include_router(module.router)
    if local_docs:
        app.mount(
            "/api-docs",
            StaticFiles(directory=str(docs_root), html=True),
            name="api-docs",
        )

        @app.get("/docs", include_in_schema=False)
        def swagger_ui() -> Any:
            return get_swagger_ui_html(
                openapi_url=app.openapi_url,
                title=f"{app.title} - Swagger UI",
                swagger_js_url=(
                    "/api-docs/vendor/swagger-ui/swagger-ui-bundle.js"
                ),
                swagger_css_url="/api-docs/vendor/swagger-ui/swagger-ui.css",
                swagger_favicon_url=(
                    "/api-docs/vendor/swagger-ui/favicon-32x32.png"
                ),
            )
    else:
        logger.warning(
            "local API docs bundle missing at %s; /docs and /api-docs are disabled",
            docs_root,
        )
    if (resolved.ui_static_dir / "index.html").is_file():
        app.frontend(
            "/",
            directory=str(resolved.ui_static_dir),
            fallback="auto",
            check_dir=False,
        )
    return app
