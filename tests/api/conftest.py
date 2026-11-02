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
    ModelResponseError,
    SpeechResult,
    StreamEvent,
    TranscriptResult,
)

DEFAULT_PASSWORD = "correct-horse-battery"


class FakeClock:
    """Injected clock so expiry rules are testable without sleeping."""

    def __init__(self, start: datetime | None = None) -> None:
        self.current = start or datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current = self.current + timedelta(**delta)


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

    def chat_stream(self, messages: Sequence[Any], **kwargs: Any):
        self.calls.append({"messages": list(messages), "kwargs": dict(kwargs)})
        if self.fail_before_first is not None:
            raise self.fail_before_first
        for index, event in enumerate(self.events):
            if self.fail_after is not None and index == self.fail_after:
                raise ModelResponseError("unavailable", 3, "fake mid-stream failure")
            yield event

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
