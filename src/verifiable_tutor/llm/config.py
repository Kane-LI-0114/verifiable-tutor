"""Load and validate the model provider configuration.

The YAML file is committed and holds no secrets. Each provider names the
environment variable that holds its API key, and this loader resolves those
keys at startup. Missing keys or unknown providers/models fail closed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigError(RuntimeError):
    """Raised when the model configuration is unusable."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Defaults(_StrictModel):
    timeout_s: float
    max_retries: int
    temperature: float
    top_p: float
    max_output_tokens: int
    thinking: str


class Supports(_StrictModel):
    image: bool
    audio: bool
    video: bool
    thinking_levels: list[str]


class ProviderConfig(_StrictModel):
    type: Literal["openai_compatible"]
    base_url: str
    api_key_env: str
    max_tokens_field: str
    models: dict[str, str]
    supports: Supports
    asr_model: str | None = None


class ThinkingConfig(_StrictModel):
    mapping: dict[str, dict[str, str]]
    # Per-provider policy for tool-calling turns. DeepSeek supports tools with
    # thinking while tool_choice stays auto; MiMo needs reasoning_content
    # replay, so it stays disabled unless the caller opts in.
    disable_for_tools: dict[str, bool] = Field(
        default_factory=lambda: {"deepseek": False, "mimo": True}
    )


class RoleParams(_StrictModel):
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None


class RoleConfig(_StrictModel):
    provider: str
    model: str
    thinking: str | None = None
    params: RoleParams = Field(default_factory=RoleParams)


class SearchConfig(_StrictModel):
    provider: str
    base_url: str
    api_key_env: str
    search_path: str
    fetch_path: str
    default_count: int = 10
    need_content: bool = True
    timeout_s: float = 30
    max_retries: int = 2


class TtsConfig(_StrictModel):
    provider: str
    models: dict[str, str]
    default_voice: str
    default_format: str
    voices: list[str]
    formats: list[str]
    default_instructions: str


class CacheConfig(_StrictModel):
    enabled: bool = True
    directory: str = "data/caches/model"


class EmbeddingConfig(_StrictModel):
    provider: str
    model: str
    model_path: str
    dimension: int
    device: str
    batch_size: int
    max_length: int


class ModelConfig(_StrictModel):
    defaults: Defaults
    providers: dict[str, ProviderConfig]
    thinking: ThinkingConfig
    roles: dict[str, RoleConfig]
    search: SearchConfig
    tts: TtsConfig
    cache: CacheConfig
    embedding: EmbeddingConfig


class ResolvedModelConfig:
    """Validated configuration plus the API keys resolved from the environment."""

    def __init__(
        self,
        config: ModelConfig,
        api_keys: Mapping[str, str],
        cache_dir: str | Path,
    ) -> None:
        self.config = config
        self.api_keys: dict[str, str] = dict(api_keys)
        self.cache_dir = Path(cache_dir)

    def model_id(self, provider: str, alias: str) -> str:
        return self.config.providers[provider].models[alias]

    def key_for(self, provider: str) -> str:
        return self.api_keys[provider]


def load_dotenv(path: str | Path) -> dict[str, str]:
    """Parse the small KEY=VALUE subset used by .env files."""

    env: dict[str, str] = {}
    text = Path(path).read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        env[key] = value
    return env


def load_model_config(
    config_path: str | Path,
    *,
    env: Mapping[str, str] | None = None,
    env_file: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> ResolvedModelConfig:
    """Load the YAML config and resolve API keys, failing closed on any problem."""

    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    try:
        config = ModelConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid model config: {exc}") from exc

    merged: dict[str, str] = dict(os.environ)
    if env_file is not None:
        merged.update(load_dotenv(env_file))
    if env is not None:
        merged.update(env)

    api_keys: dict[str, str] = {}
    for provider_name, provider in config.providers.items():
        value = merged.get(provider.api_key_env, "").strip()
        if not value:
            raise ConfigError(
                f"missing API key for provider {provider_name!r}: set {provider.api_key_env}"
            )
        api_keys[provider_name] = value

    search_key = merged.get(config.search.api_key_env, "").strip()
    if not search_key:
        raise ConfigError(f"missing API key for search: set {config.search.api_key_env}")
    api_keys["search"] = search_key

    for role_name, role in config.roles.items():
        _validate_role(role_name, role, config)
    _validate_tts(config)
    tool_policy = config.thinking.disable_for_tools
    missing = sorted(set(config.providers) - set(tool_policy))
    if missing:
        raise ConfigError(
            "thinking.disable_for_tools must name every provider: "
            + ", ".join(missing)
        )
    unknown = sorted(set(tool_policy) - set(config.providers))
    if unknown:
        raise ConfigError(
            "thinking.disable_for_tools names unknown providers: "
            + ", ".join(unknown)
        )

    base = (
        Path(base_dir)
        if base_dir is not None
        else Path(config_path).resolve().parent.parent
    )
    cache_dir = Path(config.cache.directory).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = base / cache_dir
    model_path = Path(config.embedding.model_path).expanduser()
    if not model_path.is_absolute():
        model_path = base / model_path
    config.embedding.model_path = str(model_path)
    return ResolvedModelConfig(config, api_keys, cache_dir)


def _validate_role(
    role_name: str,
    role: RoleConfig,
    config: ModelConfig,
) -> None:
    provider = config.providers.get(role.provider)
    if provider is None:
        raise ConfigError(f"role {role_name!r} names unknown provider {role.provider!r}")
    if role.model not in provider.models:
        raise ConfigError(
            f"role {role_name!r} names unknown model alias {role.model!r} "
            f"for provider {role.provider!r}"
        )
    _validate_thinking(role_name, role.provider, role.thinking, config)


def _validate_tts(config: ModelConfig) -> None:
    tts = config.tts
    if tts.provider not in config.providers:
        raise ConfigError(f"tts names unknown provider {tts.provider!r}")
    if not tts.models:
        raise ConfigError("tts.models must define at least one model")
    for alias, model_id in tts.models.items():
        if not model_id:
            raise ConfigError(f"tts model alias {alias!r} has an empty model id")
    if tts.default_format not in tts.formats:
        raise ConfigError(
            f"tts default format {tts.default_format!r} is not in {tts.formats}"
        )
    if tts.default_voice not in tts.voices:
        raise ConfigError(
            f"tts default voice {tts.default_voice!r} is not in {tts.voices}"
        )


def _validate_thinking(
    role_name: str,
    provider: str,
    level: str | None,
    config: ModelConfig,
) -> None:
    if level is None:
        return
    mapping = config.thinking.mapping.get(provider)
    if mapping is None:
        raise ConfigError(f"no thinking mapping for provider {provider!r}")
    if level not in mapping:
        raise ConfigError(
            f"role {role_name!r} uses thinking level {level!r}, "
            f"which provider {provider!r} does not map"
        )
