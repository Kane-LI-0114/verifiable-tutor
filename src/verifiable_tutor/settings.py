"""Application settings for the local FastAPI backend.

Non-secret settings live in ``config/app.yaml``. Secrets (the session signing
secret and the SMTP authorization code) live in the ignored ``.env`` and are
read through the existing ``llm.config.load_dotenv`` parser, so the repository
keeps one dotenv reader. Relative paths resolve against the repository root.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Literal, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm.config import load_dotenv


class SettingsError(RuntimeError):
    """Raised when the application settings cannot be loaded or validated."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppSection(_StrictModel):
    base_url: str = "http://127.0.0.1:8000"


class DataSection(_StrictModel):
    data_dir: str = "data"
    database_path: str = "data/app/app.sqlite3"
    trace_dir: str = "data/app/traces"
    knowledge_records_dir: str = "data/kb/records"
    corpus_images_dir: str = "data/corpus/images"
    ui_static_dir: str = "src/verifiable_tutor/ui/static"


class AuthSection(_StrictModel):
    allowed_email_domains: list[str] = Field(
        default_factory=lambda: ["connect.ust.hk", "ust.hk"]
    )
    session_cookie_name: str = "vt_session"
    session_ttl_days: int = 7
    cookie_secure: bool = False
    verification_code_ttl_minutes: int = 10
    reset_token_ttl_minutes: int = 30


class ChatSection(_StrictModel):
    history_messages: int = 12
    replay_default_speed: float = 1.0


class KnowledgeSection(_StrictModel):
    pages_path: str | None = None
    max_chunks_per_job: int = 8
    driver: str = "scripts/tacc/run_kb_job.py"
    build_timeout_s: float = 4000.0


class AppConfig(_StrictModel):
    app: AppSection = Field(default_factory=AppSection)
    data: DataSection = Field(default_factory=DataSection)
    auth: AuthSection = Field(default_factory=AuthSection)
    chat: ChatSection = Field(default_factory=ChatSection)
    knowledge: KnowledgeSection = Field(default_factory=KnowledgeSection)


class SmtpSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str | None = None
    port: int = 465
    security: Literal["ssl", "starttls"] = "ssl"
    user: str | None = None
    password: str | None = None
    sender: str | None = None


class AppSettings(BaseModel):
    """Resolved settings handed to the app factory and every service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repo_root: Path
    base_url: str
    data_dir: Path
    database_path: Path
    trace_dir: Path
    knowledge_records_dir: Path
    corpus_images_dir: Path
    ui_static_dir: Path
    allowed_email_domains: tuple[str, ...]
    session_cookie_name: str
    session_ttl: timedelta
    cookie_secure: bool
    verification_code_ttl: timedelta
    reset_token_ttl: timedelta
    chat_history_messages: int
    replay_default_speed: float
    knowledge_pages_path: Path | None
    knowledge_max_chunks: int
    knowledge_driver: Path
    knowledge_build_timeout_s: float
    session_secret: str
    smtp: SmtpSettings = Field(default_factory=SmtpSettings)


def _resolve(repo_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else repo_root / path


def _resolve_optional(repo_root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    return _resolve(repo_root, value)


def _required(merged: Mapping[str, str], name: str) -> str:
    value = merged.get(name, "").strip()
    if not value:
        raise SettingsError(
            f"{name} is not set; add it to the ignored .env "
            "(.env.example is the committed template)"
        )
    return value


def load_settings(
    *,
    config_path: str | Path | None = None,
    env_file: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    repo_root: str | Path | None = None,
) -> AppSettings:
    """Load and validate ``config/app.yaml`` plus the environment secrets."""

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    config_file = Path(config_path) if config_path is not None else root / "config" / "app.yaml"
    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        config = AppConfig.model_validate(raw)
    except FileNotFoundError as exc:
        raise SettingsError(f"application config not found: {config_file}") from exc
    except yaml.YAMLError as exc:
        raise SettingsError(f"invalid application config: {exc}") from exc
    except ValidationError as exc:
        raise SettingsError(f"invalid application config: {exc}") from exc

    merged: dict[str, str] = {}
    dotenv = Path(env_file) if env_file is not None else root / ".env"
    if dotenv.is_file():
        merged.update(load_dotenv(dotenv))
    if env is not None:
        merged.update(env)

    session_secret = _required(merged, "SESSION_SECRET")
    try:
        smtp = SmtpSettings(
            host=(merged.get("SMTP_HOST") or "").strip() or None,
            port=int((merged.get("SMTP_PORT") or "465").strip() or 465),
            security=(merged.get("SMTP_SECURITY") or "ssl").strip().lower(),
            user=(merged.get("SMTP_USER") or "").strip() or None,
            password=(merged.get("SMTP_PASSWORD") or "").strip() or None,
            sender=(merged.get("SMTP_FROM") or "").strip() or None,
        )
    except (ValidationError, ValueError) as exc:
        raise SettingsError(f"invalid SMTP settings: {exc}") from exc

    domains = tuple(
        domain.strip().lower()
        for domain in config.auth.allowed_email_domains
        if domain.strip()
    )
    try:
        settings = AppSettings(
            repo_root=root,
            base_url=config.app.base_url,
            data_dir=_resolve(root, config.data.data_dir),
            database_path=_resolve(root, config.data.database_path),
            trace_dir=_resolve(root, config.data.trace_dir),
            knowledge_records_dir=_resolve(root, config.data.knowledge_records_dir),
            corpus_images_dir=_resolve(root, config.data.corpus_images_dir),
            ui_static_dir=_resolve(root, config.data.ui_static_dir),
            allowed_email_domains=domains,
            session_cookie_name=config.auth.session_cookie_name,
            session_ttl=timedelta(days=config.auth.session_ttl_days),
            cookie_secure=config.auth.cookie_secure,
            verification_code_ttl=timedelta(
                minutes=config.auth.verification_code_ttl_minutes
            ),
            reset_token_ttl=timedelta(minutes=config.auth.reset_token_ttl_minutes),
            chat_history_messages=config.chat.history_messages,
            replay_default_speed=config.chat.replay_default_speed,
            knowledge_pages_path=_resolve_optional(
                root, config.knowledge.pages_path
            ),
            knowledge_max_chunks=config.knowledge.max_chunks_per_job,
            knowledge_driver=_resolve(root, config.knowledge.driver),
            knowledge_build_timeout_s=config.knowledge.build_timeout_s,
            session_secret=session_secret,
            smtp=smtp,
        )
    except ValidationError as exc:
        raise SettingsError(f"invalid application settings: {exc}") from exc
    return settings


def ensure_runtime_directories(settings: AppSettings) -> None:
    """Create the data and trace directories the backend writes to."""

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.trace_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
