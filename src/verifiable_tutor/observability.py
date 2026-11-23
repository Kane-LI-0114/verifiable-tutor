"""Local Langfuse tracing (ADR-0007).

Langfuse is an inspection layer for local development: the JSONL session
trace remains the canonical replay and evaluation record. Every entry point
fails open, so tracing that is disabled, missing its keys, or unable to reach
the local instance never changes the request path.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm.config import load_dotenv


class ObservabilityError(RuntimeError):
    """Raised when the observability configuration cannot be loaded."""


class LangfuseSection(BaseModel):
    """The non-secret Langfuse settings from ``config/observability.yaml``."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    base_url: str = "http://127.0.0.1:3000"
    environment: str = "local"
    release: str = "dev"
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class ObservabilitySettings(BaseModel):
    """Tracing settings: the YAML section plus the two keys from ``.env``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    langfuse: LangfuseSection = Field(default_factory=LangfuseSection)
    public_key: str | None = None
    secret_key: str | None = None


def load_observability_settings(
    *,
    config_path: str | Path | None = None,
    env_file: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    repo_root: str | Path | None = None,
) -> ObservabilitySettings:
    """Load ``config/observability.yaml`` and the two keys from the environment.

    A missing file leaves tracing disabled. A malformed file is an error, so a
    broken configuration is noticed instead of silently switching tracing off.
    """

    root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    config_file = (
        Path(config_path)
        if config_path is not None
        else root / "config" / "observability.yaml"
    )

    raw: Mapping[str, Any] = {}
    if config_file.is_file():
        try:
            loaded = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ObservabilityError(
                f"invalid observability config: {exc}"
            ) from exc
        if loaded is not None and not isinstance(loaded, Mapping):
            raise ObservabilityError(
                "invalid observability config: expected a mapping"
            )
        raw = loaded or {}

    merged: dict[str, str] = {}
    dotenv = Path(env_file) if env_file is not None else root / ".env"
    if dotenv.is_file():
        merged.update(load_dotenv(dotenv))
    if env is not None:
        merged.update(env)

    try:
        return ObservabilitySettings(
            langfuse=raw.get("langfuse") or {},
            public_key=(merged.get("LANGFUSE_PUBLIC_KEY") or "").strip() or None,
            secret_key=(merged.get("LANGFUSE_SECRET_KEY") or "").strip() or None,
        )
    except ValidationError as exc:
        raise ObservabilityError(
            f"invalid observability config: {exc}"
        ) from exc


def _langfuse_client(settings: ObservabilitySettings) -> Any:
    from langfuse import Langfuse

    return Langfuse(
        public_key=settings.public_key,
        secret_key=settings.secret_key,
        base_url=settings.langfuse.base_url,
        environment=settings.langfuse.environment,
        release=settings.langfuse.release,
        sample_rate=settings.langfuse.sample_rate,
    )


def build_tracing(
    settings: ObservabilitySettings,
    *,
    client_factory: Callable[[ObservabilitySettings], Any] | None = None,
) -> "Tracing":
    """Build the tracer, or a no-op tracer when tracing cannot be used."""

    if not settings.langfuse.enabled:
        return Tracing()
    if not settings.public_key or not settings.secret_key:
        return Tracing()
    factory = client_factory or _langfuse_client
    try:
        client = factory(settings)
    except Exception:  # an unavailable SDK must not fail startup
        return Tracing()
    return Tracing(client=client)


@dataclass(frozen=True)
class Tracing:
    """A thin, fail-open wrapper around the Langfuse client."""

    client: Any | None = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def callbacks(self) -> list[Any]:
        """Return the LangChain handler that traces graph nodes and tools."""

        if not self.enabled:
            return []
        try:
            from langfuse.langchain import CallbackHandler

            return [CallbackHandler()]
        except Exception:  # the SDK or its LangChain extra is unavailable
            return []

    def span(self, name: str, *, as_type: str = "span", **kwargs: Any) -> Any:
        """Open a span, or a no-op context when tracing is unavailable."""

        if not self.enabled:
            return nullcontext()
        try:
            return self.client.start_as_current_observation(
                name=name, as_type=as_type, **kwargs
            )
        except Exception:
            return nullcontext()

    def flush(self) -> None:
        if self.client is None:
            return
        try:
            self.client.flush()
        except Exception:
            pass

    def shutdown(self) -> None:
        if self.client is None:
            return
        try:
            self.client.shutdown()
        except Exception:
            pass
