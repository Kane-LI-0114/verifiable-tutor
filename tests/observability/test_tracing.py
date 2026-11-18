"""Local Langfuse tracing: configuration, fail-open no-ops, and delegation."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

from verifiable_tutor.observability import (
    ObservabilityError,
    ObservabilitySettings,
    build_tracing,
    load_observability_settings,
)


def test_missing_observability_file_leaves_tracing_disabled(tmp_path: Path):
    settings = load_observability_settings(
        config_path=tmp_path / "missing.yaml",
        env_file=tmp_path / "missing.env",
        env={},
    )

    assert settings.langfuse.enabled is False
    assert settings.public_key is None
    assert settings.secret_key is None


def test_loader_reads_the_file_and_the_keys(tmp_path: Path):
    config = tmp_path / "observability.yaml"
    config.write_text(
        "langfuse:\n"
        "  enabled: true\n"
        "  base_url: http://127.0.0.1:3000\n"
        "  environment: local\n"
        "  release: dev\n"
        "  sample_rate: 0.5\n",
        encoding="utf-8",
    )

    settings = load_observability_settings(
        config_path=config,
        env_file=tmp_path / "missing.env",
        env={
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        },
    )

    assert settings.langfuse.enabled is True
    assert settings.langfuse.base_url == "http://127.0.0.1:3000"
    assert settings.langfuse.sample_rate == 0.5
    assert settings.public_key == "pk-lf-test"
    assert settings.secret_key == "sk-lf-test"


def test_invalid_observability_config_is_rejected(tmp_path: Path):
    config = tmp_path / "observability.yaml"
    config.write_text("langfuse:\n  sample_rate: 2\n", encoding="utf-8")

    with pytest.raises(ObservabilityError):
        load_observability_settings(
            config_path=config,
            env_file=tmp_path / "missing.env",
            env={},
        )


class FakeClient:
    def __init__(self) -> None:
        self.spans: list[tuple[str, str, dict]] = []
        self.flushed = 0
        self.shut_down = 0

    def start_as_current_observation(self, *, name, as_type="span", **kwargs):
        self.spans.append((name, as_type, kwargs))
        return nullcontext()

    def flush(self) -> None:
        self.flushed += 1

    def shutdown(self) -> None:
        self.shut_down += 1


def test_disabled_tracing_is_a_no_op_and_never_builds_a_client():
    built = []
    settings = ObservabilitySettings(public_key="pk", secret_key="sk")

    tracing = build_tracing(settings, client_factory=lambda item: built.append(item))

    assert tracing.enabled is False
    assert built == []
    assert tracing.callbacks() == []
    with tracing.span("chat-turn"):
        pass
    tracing.flush()
    tracing.shutdown()


def test_enabled_tracing_without_keys_is_a_no_op():
    built = []
    settings = ObservabilitySettings(
        langfuse={"enabled": True}, public_key="", secret_key=""
    )

    tracing = build_tracing(settings, client_factory=lambda item: built.append(item))

    assert tracing.enabled is False
    assert built == []


def test_a_client_that_cannot_be_built_fails_open():
    settings = ObservabilitySettings(
        langfuse={"enabled": True}, public_key="pk", secret_key="sk"
    )

    def broken(item):
        raise RuntimeError("sdk unavailable")

    tracing = build_tracing(settings, client_factory=broken)

    assert tracing.enabled is False
    assert tracing.callbacks() == []


def test_enabled_tracing_delegates_spans_flush_and_shutdown():
    client = FakeClient()
    settings = ObservabilitySettings(
        langfuse={"enabled": True}, public_key="pk", secret_key="sk"
    )

    tracing = build_tracing(settings, client_factory=lambda item: client)
    with tracing.span(
        "chat-turn", as_type="agent", metadata={"session": "s1"}
    ):
        pass
    tracing.flush()
    tracing.shutdown()

    assert tracing.enabled is True
    assert client.spans == [
        ("chat-turn", "agent", {"metadata": {"session": "s1"}})
    ]
    assert client.flushed == 1
    assert client.shut_down == 1


def test_a_failing_span_falls_back_to_a_no_op():
    class Failing(FakeClient):
        def start_as_current_observation(self, **kwargs):
            raise RuntimeError("exporter down")

    client = Failing()
    settings = ObservabilitySettings(
        langfuse={"enabled": True}, public_key="pk", secret_key="sk"
    )
    tracing = build_tracing(settings, client_factory=lambda item: client)

    with tracing.span("chat-turn"):
        pass


def test_enabled_tracing_returns_a_langchain_callback_handler():
    client = FakeClient()
    settings = ObservabilitySettings(
        langfuse={"enabled": True}, public_key="pk", secret_key="sk"
    )
    tracing = build_tracing(settings, client_factory=lambda item: client)

    callbacks = tracing.callbacks()

    assert len(callbacks) == 1
