from pathlib import Path

import pytest

from verifiable_tutor.llm.config import (
    ConfigError,
    load_dotenv,
    load_model_config,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"

MINIMAL_CONFIG = """
defaults:
  timeout_s: 60
  max_retries: 2
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 4096
  thinking: "off"
providers:
  deepseek:
    type: openai_compatible
    base_url: https://api.deepseek.com
    api_key_env: DEEPSEEK_API_KEY
    max_tokens_field: max_tokens
    models:
      flash: deepseek-flash
    supports:
      image: true
      audio: false
      video: false
      thinking_levels: ["off", low, high, max]
  mimo:
    type: openai_compatible
    base_url: https://api.xiaomimimo.com/v1
    api_key_env: MIMO_API_KEY
    max_tokens_field: max_completion_tokens
    asr_model: mimo-v2.5-asr
    models:
      flash: mimo-v2.6-flash
      pro: mimo-v2.6-pro
    supports:
      image: true
      audio: true
      video: true
      thinking_levels: ["off", high]
thinking:
  mapping:
    deepseek: {"off": none, low: low, high: high, max: max}
    mimo: {"off": disabled, low: enabled, high: enabled, max: enabled}
  disable_for_tools: true
roles:
  chat:
    provider: deepseek
    model: flash
    thinking: "off"
    params:
      max_output_tokens: 2048
  classify_intent:
    provider: mimo
    model: flash
search:
  provider: deepseek
  base_url: https://api.deepseek.com/v1
  api_key_env: DEEPSEEK_API_KEY
  search_path: /tools/search
  fetch_path: /tools/fetch
  default_count: 10
  need_content: true
  timeout_s: 30
  max_retries: 2
tts:
  provider: mimo
  models:
    default: mimo-v2.5-tts
  default_voice: mimo_default
  default_format: wav
  voices: [mimo_default, 茉莉]
  formats: [wav, mp3]
  default_instructions: "Speak clearly with a steady pace."
cache:
  enabled: true
  directory: data/caches/model
embedding:
  provider: local
  model: BAAI/bge-m3
  model_path: ~/models/bge-m3
  dimension: 1024
  device: cpu
  batch_size: 16
  max_length: 512
"""

ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text(MINIMAL_CONFIG, encoding="utf-8")
    return path


def test_resolves_model_aliases_and_api_keys(config_path: Path) -> None:
    resolved = load_model_config(config_path, env=ENV)

    assert resolved.config.providers["deepseek"].models["flash"] == "deepseek-flash"
    assert resolved.config.providers["mimo"].models["pro"] == "mimo-v2.6-pro"
    assert resolved.config.providers["mimo"].asr_model == "mimo-v2.5-asr"
    assert resolved.api_keys["deepseek"] == "sk-deepseek-test"
    assert resolved.api_keys["mimo"] == "sk-mimo-test"
    assert resolved.api_keys["search"] == "sk-deepseek-test"


def test_missing_provider_key_fails_closed(config_path: Path) -> None:
    with pytest.raises(ConfigError, match="DEEPSEEK_API_KEY"):
        load_model_config(config_path, env={"MIMO_API_KEY": "sk-mimo-test"})


def test_missing_search_key_fails_closed(config_path: Path) -> None:
    env = {"DEEPSEEK_API_KEY": "", "MIMO_API_KEY": "sk-mimo-test"}
    with pytest.raises(ConfigError, match="DEEPSEEK_API_KEY"):
        load_model_config(config_path, env=env)


def test_unknown_role_provider_is_rejected(config_path: Path) -> None:
    path = config_path
    path.write_text(
        MINIMAL_CONFIG.replace("provider: deepseek\n    model: flash", "provider: nope\n    model: flash", 1),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="nope"):
        load_model_config(path, env=ENV)


def test_unknown_role_model_alias_is_rejected(config_path: Path) -> None:
    path = config_path
    path.write_text(
        MINIMAL_CONFIG.replace("model: flash\n    thinking", "model: missing\n    thinking", 1),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="missing"):
        load_model_config(path, env=ENV)


def test_load_dotenv_reads_keys_and_ignores_comments(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nDEEPSEEK_API_KEY=sk-from-file\n\nMIMO_API_KEY='sk-mimo-file'\n",
        encoding="utf-8",
    )

    env = load_dotenv(env_file)

    assert env == {"DEEPSEEK_API_KEY": "sk-from-file", "MIMO_API_KEY": "sk-mimo-file"}


def test_env_file_is_used_when_env_mapping_is_absent(config_path: Path, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=sk-envfile\nMIMO_API_KEY=sk-envfile-mimo\n", encoding="utf-8")

    resolved = load_model_config(config_path, env_file=env_file)

    assert resolved.api_keys["deepseek"] == "sk-envfile"


def test_repository_config_matches_provider_documentation() -> None:
    resolved = load_model_config(
        REAL_CONFIG,
        env={"DEEPSEEK_API_KEY": "sk-test", "MIMO_API_KEY": "sk-test"},
    )

    providers = resolved.config.providers
    assert providers["deepseek"].base_url == "https://api.deepseek.com"
    assert providers["deepseek"].max_tokens_field == "max_tokens"
    assert providers["deepseek"].models == {"flash": "deepseek-flash"}
    assert providers["mimo"].base_url == "https://api.xiaomimimo.com/v1"
    assert providers["mimo"].max_tokens_field == "max_completion_tokens"
    assert providers["mimo"].models == {"flash": "mimo-v2.6-flash", "pro": "mimo-v2.6-pro"}
    assert providers["mimo"].asr_model == "mimo-v2.5-asr"
    assert resolved.config.search.provider == "deepseek"
    assert resolved.config.tts.provider == "mimo"
    assert resolved.config.tts.models["default"] == "mimo-v2.5-tts"
    assert resolved.config.tts.default_voice == "mimo_default"
    assert resolved.config.thinking.mapping["deepseek"]["off"] == "none"
    assert resolved.config.thinking.mapping["mimo"]["high"] == "enabled"
