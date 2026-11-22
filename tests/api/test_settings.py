"""Settings loading: YAML config, path resolution, and the required secret."""

from __future__ import annotations

from pathlib import Path

import pytest

from verifiable_tutor.settings import SettingsError, load_settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_settings_resolves_paths_and_domains(tmp_path: Path):
    settings = load_settings(
        repo_root=REPO_ROOT,
        env_file=tmp_path / "missing.env",
        env={"SESSION_SECRET": "unit-test-secret"},
    )

    assert settings.repo_root == REPO_ROOT
    assert settings.database_path == REPO_ROOT / "data" / "app" / "app.sqlite3"
    assert settings.trace_dir == REPO_ROOT / "data" / "app" / "traces"
    assert settings.allowed_email_domains == ("connect.ust.hk", "ust.hk")
    assert settings.session_cookie_name == "vt_session"
    assert settings.session_ttl.days == 7
    assert settings.smtp.host is None
    assert settings.knowledge_pages_path is None
    assert settings.agent_max_model_calls == 20
    assert settings.agent_max_tool_calls == 50
    assert settings.agent_recursion_limit == 60
    assert settings.agent_max_tool_output_chars == 4000
    assert settings.agent_retrieval_k == 8
    assert settings.agent_web_search_count == 10
    assert settings.agent_web_fetch_max_chars == 6000
    assert settings.agent_web_tools_enabled is True


def test_load_settings_fails_closed_when_the_session_secret_is_missing(tmp_path: Path):
    with pytest.raises(SettingsError, match="SESSION_SECRET"):
        load_settings(
            repo_root=REPO_ROOT,
            env_file=tmp_path / "missing.env",
            env={},
        )


def test_load_settings_reads_smtp_from_the_environment(tmp_path: Path):
    settings = load_settings(
        repo_root=REPO_ROOT,
        env_file=tmp_path / "missing.env",
        env={
            "SESSION_SECRET": "unit-test-secret",
            "SMTP_HOST": "smtp.qq.com",
            "SMTP_PORT": "587",
            "SMTP_SECURITY": "starttls",
            "SMTP_USER": "sender@qq.com",
            "SMTP_PASSWORD": "authorization-code",
            "SMTP_FROM": "sender@qq.com",
        },
    )

    assert settings.smtp.host == "smtp.qq.com"
    assert settings.smtp.port == 587
    assert settings.smtp.security == "starttls"
    assert settings.smtp.sender == "sender@qq.com"
