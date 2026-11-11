"""Shared fixtures for the HTTP API tests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from verifiable_tutor.auth.service import bootstrap_instructor
from verifiable_tutor.auth.email import EmailMessage
from verifiable_tutor.api.factory import create_app
from verifiable_tutor.settings import AppSettings, SmtpSettings
from verifiable_tutor.llm.adapter import (
    FetchResult,
    ModelResponseError,
    ModelSelection,
    ModelSelectionError,
    SearchResult,
    SpeechResult,
    StreamEvent,
    TranscriptResult,
)
from verifiable_tutor.orchestrator.tools import ToolResult

DEFAULT_PASSWORD = "correct-horse-battery"

# Mirrors the committed chat defaults in config/models.yaml for the fake seam.
DEFAULT_PROVIDER = "deepseek"
DEFAULT_ALIAS = "flash"
DEFAULT_THINKING = "off"
MODEL_IDS = {
    "deepseek": {"flash": "deepseek-flash"},
    "mimo": {"flash": "mimo-v2.6-flash", "pro": "mimo-v2.6-pro"},
}


class FakeClock:
    """Injected clock so expiry rules are testable without sleeping."""

    def __init__(self, start: datetime | None = None) -> None:
        self.current = start or datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current = self.current + timedelta(**delta)


class FakeToolRegistry:
    """A deterministic tool registry for HTTP tests; no local corpus needed."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def names(self) -> list[str]:
        return ["search_course"]

    def step_for(self, name: str) -> str | None:
        return "retrieve" if name in {"search_course", "web_search"} else None

    def specs(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_course",
                    "description": "Search the course corpus.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            }
        ]

    def execute(self, name: str, arguments: Any, *, context: Any) -> ToolResult:
        self.calls.append({"name": name, "arguments": arguments})
        if name not in {"search_course", "web_search"}:
            payload = {"error": f"unknown tool {name!r}"}
            return ToolResult(
                content=json.dumps(payload),
                output=payload["error"],
                result=payload,
                status="failed",
            )
        if name == "web_search":
            source = context.sources.add_web(
                url="https://example.com/deepseek",
                title="DeepSeek V4 released",
                summary="A summary.",
            )
            result = {
                "title": "DeepSeek V4 released",
                "url": "https://example.com/deepseek",
                "summary": "A summary.",
                "marker": source.marker,
                "citation": f"[{source.marker}]",
            }
            payload = {
                "source": "web",
                "untrusted": True,
                "results": [result],
                "sources": [source.as_dict()],
            }
            return ToolResult(
                content=json.dumps(payload),
                output="1 web results",
                result=payload,
                status="done",
            )
        source = context.sources.add_course(
            doc_id="Tutorial_2",
            page_no=8,
            title="Tutorial 2: Collectives",
            text="MPI_Allreduce reduces a value across all ranks.",
            chunk_id="Tutorial_2:p008:c00",
        )
        payload = {
            "source": "course",
            "chunks": [
                {
                    "doc_id": "Tutorial_2",
                    "page_no": 8,
                    "chunk_id": "Tutorial_2:p008:c00",
                    "section": "Collectives",
                    "text": "MPI_Allreduce reduces a value across all ranks.",
                    "marker": source.marker,
                    "citation": f"[{source.marker}]",
                }
            ],
            "sources": [source.as_dict()],
        }
        return ToolResult(
            content=json.dumps(payload),
            output="1 course chunks",
            result=payload,
            status="done",
        )


class RecordingEmailSender:
    """Email seam fake: records messages for assertions, sends nothing."""

    delivery = "log"

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)

    @property
    def last_message(self) -> EmailMessage:
        return self.sent[-1]


class FakeAdapter:
    """Model adapter fake at the network boundary."""

    def __init__(self) -> None:
        self.events: list[StreamEvent] = [
            StreamEvent(kind="text", text="Hello"),
            StreamEvent(kind="finish", finish_reason="stop"),
        ]
        # One script per model call; an empty list falls back to ``events``.
        self.scripts: list[list[StreamEvent]] = []
        self.fail_before_first: Exception | None = None
        self.fail_after: int | None = None
        self.calls: list[dict[str, Any]] = []
        self.transcript = TranscriptResult(
            text="hello world", language="en", seconds=1.5, model="mimo-v2.5-asr"
        )
        self.speech = SpeechResult(
            audio=b"RIFFfake", format="wav", voice="mimo_default", model="mimo-v2.5-tts"
        )
        self.transcribe_error: Exception | None = None
        self.speak_error: Exception | None = None
        self.speech_stream_frames: list[str] = ["AAABAA==", "AgADAA=="]
        self.speak_stream_fail_before_first: Exception | None = None
        self.speak_stream_fail_after: int | None = None

    def resolve_selection(
        self,
        *,
        role: str = "chat",
        provider: str | None = None,
        tier: str | None = None,
        thinking: str | None = None,
    ) -> ModelSelection:
        """Mirror the adapter's resolution seam with the configured defaults."""

        resolved_provider = provider or DEFAULT_PROVIDER
        aliases = MODEL_IDS.get(resolved_provider)
        if aliases is None:
            raise ModelSelectionError(f"unknown provider {resolved_provider!r}")
        alias = tier or (
            DEFAULT_ALIAS if resolved_provider == DEFAULT_PROVIDER else None
        )
        if alias not in aliases:
            raise ModelSelectionError(
                f"provider {resolved_provider!r} has no model alias {alias!r}"
            )
        return ModelSelection(
            provider=resolved_provider,
            model=aliases[alias],
            tier=tier,
            thinking=thinking or DEFAULT_THINKING,
        )

    def chat_stream(self, messages: Sequence[Any], **kwargs: Any):
        self.calls.append({"messages": list(messages), "kwargs": dict(kwargs)})
        if self.fail_before_first is not None:
            raise self.fail_before_first
        events = self.scripts.pop(0) if self.scripts else self.events
        for index, event in enumerate(events):
            if self.fail_after is not None and index == self.fail_after:
                raise ModelResponseError("unavailable", 3, "fake mid-stream failure")
            yield event

    def search(self, query: str, *, count: int | None = None, need_content: bool | None = None):
        self.calls.append(
            {"search": query, "count": count, "need_content": need_content}
        )
        return [
            SearchResult(
                title="DeepSeek V4 released",
                url="https://example.com/deepseek",
                snippet="short",
                summary="A summary of the release.",
                content="",
                site_name="Example",
                date="2026-06-01T00:00:00+00:00",
                rerank_score=2.0,
                authority=3,
            )
        ]

    def fetch(self, url: str):
        self.calls.append({"fetch": url})
        return FetchResult(url=url, title="Example", content="Page body.")

    def transcribe(self, audio: bytes, **kwargs: Any) -> TranscriptResult:
        self.calls.append({"audio": audio, "kwargs": dict(kwargs)})
        if self.transcribe_error is not None:
            raise self.transcribe_error
        return self.transcript

    def speak(self, text: str, **kwargs: Any) -> SpeechResult:
        self.calls.append({"text": text, "kwargs": dict(kwargs)})
        if self.speak_error is not None:
            raise self.speak_error
        return self.speech

    def speak_stream(self, text: str, **kwargs: Any):
        self.calls.append({"text": text, "kwargs": dict(kwargs)})
        if self.speak_stream_fail_before_first is not None:
            raise self.speak_stream_fail_before_first
        for index, frame in enumerate(self.speech_stream_frames):
            if (
                self.speak_stream_fail_after is not None
                and index == self.speak_stream_fail_after
            ):
                raise ModelResponseError("unavailable", 3, "fake mid-stream failure")
            yield frame


class FakeBuildRunner:
    """Knowledge-build runner fake at the subprocess boundary."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: dict[str, Any] = {
            "job_id": "28067",
            "records_path": "data/kb/records/kb-test.jsonl",
            "records_count": 8,
        }
        self.error: Exception | None = None

    def run(self, build_id: str, *, doc_id: str | None, max_chunks: int):
        self.calls.append(
            {"build_id": build_id, "doc_id": doc_id, "max_chunks": max_chunks}
        )
        if self.error is not None:
            raise self.error
        return dict(self.result)


def make_settings(tmp_path: Path, **overrides: Any) -> AppSettings:
    """Build explicit settings rooted in a temporary directory."""

    data = tmp_path / "data"
    values: dict[str, Any] = {
        "repo_root": tmp_path,
        "base_url": "http://testserver",
        "data_dir": data,
        "database_path": data / "app" / "app.sqlite3",
        "trace_dir": data / "app" / "traces",
        "knowledge_records_dir": data / "kb" / "records",
        "corpus_images_dir": data / "corpus" / "images",
        "corpus_pdf_dir": data / "corpus" / "pdf",
        "ui_static_dir": tmp_path / "static",
        "allowed_email_domains": ("ust.hk",),
        "session_cookie_name": "vt_session",
        "session_ttl": timedelta(days=7),
        "cookie_secure": False,
        "verification_code_ttl": timedelta(minutes=10),
        "reset_token_ttl": timedelta(minutes=30),
        "chat_history_messages": 12,
        "replay_default_speed": 1.0,
        "knowledge_pages_path": None,
        "knowledge_max_chunks": 8,
        "knowledge_driver": tmp_path / "scripts" / "tacc" / "run_kb_job.py",
        "knowledge_build_timeout_s": 60.0,
        "knowledge_top_k": 8,
        "knowledge_embedding_provider": "local",
        "session_secret": "test-session-secret-0123456789abcdef",
        "smtp": SmtpSettings(),
    }
    values.update(overrides)
    return AppSettings(**values)


@dataclass
class Harness:
    app: FastAPI
    client: TestClient
    settings: AppSettings
    clock: FakeClock
    adapter: FakeAdapter
    email: RecordingEmailSender
    runner: FakeBuildRunner
    sleep_calls: list[float] = field(default_factory=list)

    def register(self, email: str = "alice@ust.hk", password: str = DEFAULT_PASSWORD):
        return self.client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )

    def verification_code(self) -> str:
        match = re.search(r"\b(\d{6})\b", self.email.last_message.body)
        assert match is not None, f"no code in {self.email.last_message.body!r}"
        return match.group(1)

    def reset_token(self) -> str:
        match = re.search(r"token=([A-Za-z0-9_\-]+)", self.email.last_message.body)
        assert match is not None, f"no token in {self.email.last_message.body!r}"
        return match.group(1)

    def verify(self, email: str = "alice@ust.hk", code: str | None = None):
        return self.client.post(
            "/api/auth/verify",
            json={"email": email, "code": code if code is not None else self.verification_code()},
        )

    def login(
        self, email: str = "alice@ust.hk", password: str = DEFAULT_PASSWORD
    ) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        cookie = response.cookies.get(self.settings.session_cookie_name)
        return {} if cookie is None else {self.settings.session_cookie_name: cookie}

    def create_active_account(
        self, email: str = "alice@ust.hk", password: str = DEFAULT_PASSWORD
    ) -> dict[str, str]:
        self.register(email=email, password=password)
        response = self.verify(email=email)
        assert response.status_code == 200, response.text
        return self.login(email=email, password=password)

    def login_response(self, email: str = "alice@ust.hk", password: str = DEFAULT_PASSWORD):
        return self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )

    def set_cookie(self, value: str | None) -> None:
        """Replace the client cookie jar with one explicit session value."""

        self.client.cookies.clear()
        if value is not None:
            self.client.cookies.set(self.settings.session_cookie_name, value)

    def clear_cookies(self) -> None:
        self.client.cookies.clear()

    def create_instructor(
        self, email: str = "teacher@ust.hk", password: str = DEFAULT_PASSWORD
    ) -> dict[str, str]:
        bootstrap_instructor(
            storage=self.app.state.storage,
            email=email,
            password=password,
            clock=self.clock,
        )
        self.clear_cookies()
        return self.login(email, password)


@contextmanager
def _harness(tmp_path: Path, settings_overrides: dict[str, Any] | None = None, **app_kwargs: Any):
    settings = make_settings(tmp_path, **(settings_overrides or {}))
    clock = FakeClock()
    adapter = FakeAdapter()
    email = RecordingEmailSender()
    runner = FakeBuildRunner()
    sleep_calls: list[float] = []
    app = create_app(
        settings,
        clock=clock,
        sleep=sleep_calls.append,
        adapter_factory=lambda: adapter,
        email_sender=email,
        build_runner=runner,
        **app_kwargs,
    )
    with TestClient(app) as client:
        yield Harness(
            app=app,
            client=client,
            settings=settings,
            clock=clock,
            adapter=adapter,
            email=email,
            runner=runner,
            sleep_calls=sleep_calls,
        )


@pytest.fixture
def api(tmp_path: Path):
    with _harness(tmp_path) as harness:
        yield harness


@pytest.fixture
def agent_api(tmp_path: Path):
    with _harness(tmp_path, tool_registry=FakeToolRegistry()) as harness:
        yield harness


@pytest.fixture
def domains_api(tmp_path: Path):
    with _harness(
        tmp_path, {"allowed_email_domains": ("connect.ust.hk", "ust.hk")}
    ) as harness:
        yield harness


@pytest.fixture
def kb_api(tmp_path: Path):
    pages = tmp_path / "pages.jsonl"
    pages.write_text('{"doc_id": "course_project", "page_no": 1}\n', encoding="utf-8")
    with _harness(tmp_path, {"knowledge_pages_path": pages}) as harness:
        yield harness


@pytest.fixture
def ui_api(tmp_path: Path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><h1>built ui</h1>", encoding="utf-8")
    with _harness(tmp_path, {"ui_static_dir": static}) as harness:
        yield harness


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def docs_api(tmp_path: Path):
    with _harness(tmp_path, docs_api_dir=REPO_ROOT / "docs" / "api") as harness:
        yield harness


@pytest.fixture
def missing_docs_api(tmp_path: Path):
    with _harness(tmp_path, docs_api_dir=tmp_path / "missing-docs") as harness:
        yield harness
