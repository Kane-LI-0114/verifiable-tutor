"""The SQLite schema upgrades legacy databases in place.

The fixture below is the schema that shipped before turn metadata existed. The
upgrade must add the new columns and tables without touching stored rows, and a
second initialization must be a no-op.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from verifiable_tutor.storage import Storage

# Independent expected value: ADR-0014 defined user_version 1 for the schema
# that stores turn metadata, and ADR-0015 bumps it to 2 for the knowledge
# tables (folders, documents, chunks, the full-text index, and index state).
SCHEMA_VERSION = 2

LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'instructor')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'disabled')),
    created_at TEXT NOT NULL,
    verified_at TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    provider TEXT,
    tier TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (conversation_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, sequence);
"""

LEGACY_ROWS = (
    "INSERT INTO users (id, email, password_hash, role, status, created_at)"
    " VALUES ('user-1', 'alice@ust.hk', 'hash', 'student', 'active',"
    " '2026-11-02T12:00:00+00:00')",
    "INSERT INTO conversations (id, user_id, title, created_at, updated_at)"
    " VALUES ('conv-1', 'user-1', 'Legacy question',"
    " '2026-11-02T12:00:00+00:00', '2026-11-02T12:01:00+00:00')",
    "INSERT INTO messages"
    " (id, conversation_id, sequence, role, content, provider, tier, created_at)"
    " VALUES ('msg-1', 'conv-1', 1, 'user', 'legacy question', NULL, NULL,"
    " '2026-11-02T12:00:00+00:00')",
    "INSERT INTO messages"
    " (id, conversation_id, sequence, role, content, provider, tier, created_at)"
    " VALUES ('msg-2', 'conv-1', 2, 'assistant', 'legacy answer', 'deepseek',"
    " 'flash', '2026-11-02T12:01:00+00:00')",
)


def _legacy_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(LEGACY_SCHEMA)
        for statement in LEGACY_ROWS:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def _connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path)


def test_initialize_upgrades_a_legacy_database_without_losing_rows(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    _legacy_database(path)

    Storage(path).initialize()

    connection = _connection(path)
    try:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(messages)")
        }
        assert {"reasoning", "model", "thinking"} <= columns

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"message_steps", "citations", "tool_calls"} <= tables
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION

        legacy = connection.execute(
            "SELECT content, provider, tier FROM messages WHERE id = 'msg-2'"
        ).fetchone()
        assert legacy == ("legacy answer", "deepseek", "flash")
        assert (
            connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
        )
    finally:
        connection.close()


def test_initialize_is_idempotent_on_an_upgraded_database(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    _legacy_database(path)
    storage = Storage(path)
    storage.initialize()

    storage.initialize()

    connection = _connection(path)
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
        )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    finally:
        connection.close()


def test_initialize_creates_the_current_schema_on_a_fresh_database(tmp_path):
    path = tmp_path / "fresh.sqlite3"

    Storage(path).initialize()

    connection = _connection(path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "users",
            "verification_codes",
            "login_sessions",
            "conversations",
            "messages",
            "message_steps",
            "citations",
            "tool_calls",
            "knowledge_builds",
            "kb_folders",
            "kb_documents",
            "kb_chunks",
            "kb_chunks_fts",
            "kb_index_state",
        } <= tables
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    finally:
        connection.close()
