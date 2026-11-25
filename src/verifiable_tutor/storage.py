"""SQLite storage for accounts, sessions, conversations, and builds.

The database lives under the ignored ``data/app/`` directory. Each operation
opens a short-lived connection, enables WAL and foreign keys, and commits on
success, so sync endpoint code running in the AnyIO threadpool never shares a
connection across threads.

The schema is versioned through ``PRAGMA user_version``. ``initialize`` runs
the full current schema (fresh databases) and then applies the column additions
a legacy database is missing (existing databases), so an upgrade never drops
stored conversations, messages, or accounts.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

SCHEMA_VERSION = 11

# The turn-metadata columns added to ``messages`` by schema version 1. They are
# appended after ``created_at`` so a fresh database and an upgraded database
# share the same column order.
_MESSAGE_METADATA_COLUMNS = (
    ("reasoning", "TEXT"),
    ("model", "TEXT"),
    ("thinking", "TEXT"),
)

# The provider-call columns added to ``tool_calls`` by schema version 3. They
# are appended after ``status`` so an upgraded database matches a fresh one.
_TOOL_CALL_COLUMNS = (
    ("tool_call_id", "TEXT"),
    ("arguments_json", "TEXT"),
    ("result_json", "TEXT"),
    ("duration_ms", "INTEGER"),
)

# The work-chain step id added to ``message_events`` by schema version 5.
_MESSAGE_EVENT_COLUMNS = (("step_id", "TEXT"),)

# Soft-delete stamps added to the knowledge tables by schema version 6. A row
# with a stamp stays on disk, with its PDF, chunks, and vectors, but every
# active read excludes it.
_KNOWLEDGE_SOFT_DELETE_COLUMNS = (
    ("kb_folders", "deleted_at"),
    ("kb_documents", "deleted_at"),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'instructor')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'disabled')),
    created_at TEXT NOT NULL,
    verified_at TEXT
);

CREATE TABLE IF NOT EXISTS verification_codes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('verify', 'reset')),
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_codes_user ON verification_codes(user_id, purpose);
CREATE INDEX IF NOT EXISTS idx_codes_hash ON verification_codes(purpose, code_hash);

CREATE TABLE IF NOT EXISTS login_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_sessions_user ON login_sessions(user_id);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    kind TEXT NOT NULL DEFAULT 'chat' CHECK (kind IN ('chat', 'practice')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS practice_sessions (
    conversation_id TEXT PRIMARY KEY
        REFERENCES conversations(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('not_started', 'in_progress', 'completed')
    ),
    best_score REAL NOT NULL DEFAULT 0,
    max_score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS practice_attempts (
    conversation_id TEXT NOT NULL
        REFERENCES practice_sessions(conversation_id) ON DELETE CASCADE,
    attempt_no INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed')),
    answers_json TEXT NOT NULL DEFAULT '{}',
    results_json TEXT NOT NULL DEFAULT '{}',
    option_order_json TEXT NOT NULL DEFAULT '{}',
    score REAL,
    max_score REAL NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    PRIMARY KEY (conversation_id, attempt_no)
);

CREATE TABLE IF NOT EXISTS revision_themes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS revision_documents (
    doc_id TEXT PRIMARY KEY REFERENCES kb_documents(id) ON DELETE CASCADE,
    theme_id TEXT NOT NULL REFERENCES revision_themes(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (
        category IN ('assignment', 'lecture', 'tutorial', 'other')
    ),
    created_at TEXT NOT NULL,
    markdown TEXT,
    intro_markdown TEXT,
    model TEXT,
    prompt_version TEXT,
    generated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_revision_documents_theme
    ON revision_documents(theme_id);

CREATE TABLE IF NOT EXISTS revision_points (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES revision_documents(doc_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    position INTEGER NOT NULL,
    page_no INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (doc_id, position)
);
CREATE INDEX IF NOT EXISTS idx_revision_points_doc
    ON revision_points(doc_id, position);

CREATE TABLE IF NOT EXISTS revision_progress (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    point_id TEXT NOT NULL REFERENCES revision_points(id) ON DELETE CASCADE,
    mastered INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, point_id)
);

CREATE TABLE IF NOT EXISTS topic_progress (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    knowledge_point TEXT NOT NULL,
    covered INTEGER NOT NULL DEFAULT 0,
    mastered INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, topic, knowledge_point)
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
    reasoning TEXT,
    model TEXT,
    thinking TEXT,
    UNIQUE (conversation_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, sequence);

CREATE TABLE IF NOT EXISTS message_steps (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    step TEXT NOT NULL CHECK (
        step IN ('understand', 'retrieve', 'verify', 'decide', 'generate', 'cite')
    ),
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'started', 'done', 'failed')
    ),
    detail TEXT,
    duration_ms INTEGER,
    policy TEXT CHECK (
        policy IS NULL OR policy IN (
            'pre-release', 'active', 'extension-window', 'post-deadline', 'unknown'
        )
    ),
    rule_id TEXT,
    UNIQUE (message_id, position)
);

CREATE TABLE IF NOT EXISTS citations (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    doc_id TEXT NOT NULL,
    page_no INTEGER NOT NULL,
    quoted_span TEXT NOT NULL,
    bbox_norm TEXT,
    verified_at TEXT,
    UNIQUE (message_id, position)
);


CREATE TABLE IF NOT EXISTS message_sources (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    marker INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('course', 'web')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    doc_id TEXT,
    page_no INTEGER,
    url TEXT,
    chunk_id TEXT,
    UNIQUE (message_id, position),
    UNIQUE (message_id, marker),
    CHECK (
        (kind = 'course' AND doc_id IS NOT NULL AND page_no IS NOT NULL AND url IS NULL)
        OR (kind = 'web' AND url IS NOT NULL AND doc_id IS NULL AND page_no IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    command_json TEXT,
    exit_code INTEGER,
    output TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed')),
    tool_call_id TEXT,
    arguments_json TEXT,
    result_json TEXT,
    duration_ms INTEGER,
    UNIQUE (message_id, position)
);

CREATE TABLE IF NOT EXISTS message_events (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('reasoning', 'tool_call')),
    reasoning TEXT,
    tool_call_position INTEGER,
    step_id TEXT,
    UNIQUE (message_id, position),
    CHECK (
        (kind = 'reasoning' AND reasoning IS NOT NULL AND tool_call_position IS NULL)
        OR (kind = 'tool_call' AND tool_call_position IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_message_events_message
    ON message_events(message_id, position);

CREATE TABLE IF NOT EXISTS knowledge_builds (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('queued', 'running', 'ready', 'failed')),
    request_json TEXT NOT NULL,
    job_id TEXT,
    records_path TEXT,
    records_count INTEGER,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_builds_state
    ON knowledge_builds(state, created_at DESC);

CREATE TABLE IF NOT EXISTS kb_folders (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES kb_folders(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE (parent_id, name)
);
CREATE INDEX IF NOT EXISTS idx_kb_folders_parent ON kb_folders(parent_id);

CREATE TABLE IF NOT EXISTS kb_documents (
    id TEXT PRIMARY KEY,
    folder_id TEXT REFERENCES kb_folders(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    pdf_sha256 TEXT NOT NULL UNIQUE,
    byte_size INTEGER,
    page_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    pdf_path TEXT NOT NULL,
    thumbnail_path TEXT,
    summary TEXT,
    summary_model TEXT,
    summary_created_at TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('uploading', 'uploaded', 'upload_failed', 'processing',
                   'ready', 'failed')
    ),
    status_detail TEXT,
    indexed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_kb_documents_folder
    ON kb_documents(folder_id, created_at DESC);

CREATE TABLE IF NOT EXISTS kb_chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    page_no INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    section TEXT,
    text TEXT NOT NULL,
    embed_text TEXT NOT NULL,
    block_ids TEXT,
    bbox_norm TEXT,
    token_estimate INTEGER,
    oversize INTEGER NOT NULL DEFAULT 0,
    embedding BLOB,
    embedding_model TEXT,
    chunker_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (doc_id, page_no, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc ON kb_chunks(doc_id, page_no, chunk_index);

CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(
    text, section,
    content='kb_chunks',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS kb_chunks_ai AFTER INSERT ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(rowid, text, section)
    VALUES (new.rowid, new.text, new.section);
END;

CREATE TRIGGER IF NOT EXISTS kb_chunks_ad AFTER DELETE ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(kb_chunks_fts, rowid, text, section)
    VALUES ('delete', old.rowid, old.text, old.section);
END;

CREATE TRIGGER IF NOT EXISTS kb_chunks_au AFTER UPDATE ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(kb_chunks_fts, rowid, text, section)
    VALUES ('delete', old.rowid, old.text, old.section);
    INSERT INTO kb_chunks_fts(rowid, text, section)
    VALUES (new.rowid, new.text, new.section);
END;

CREATE TABLE IF NOT EXISTS kb_index_state (
    id TEXT PRIMARY KEY CHECK (id = 'current'),
    chunks INTEGER NOT NULL DEFAULT 0,
    dimension INTEGER,
    model TEXT,
    chunker_version TEXT,
    built_at TEXT
);
INSERT OR IGNORE INTO kb_index_state (id) VALUES ('current');
"""


def iso(moment: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC string with second precision."""

    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp written by :func:`iso`."""

    return datetime.fromisoformat(value)


def _encode_json(value: Any) -> str | None:
    """Serialize a list or mapping for a TEXT column, preserving null."""

    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _decode_json(value: str | None) -> Any:
    """Parse a TEXT JSON column written by :func:`_encode_json`."""

    if value is None:
        return None
    return json.loads(value)


def _practice_session_row(row: sqlite3.Row) -> dict[str, Any]:
    """Decode one practice session row for the API and the tests."""

    return {
        "conversation_id": row["conversation_id"],
        "topic": row["topic"],
        "questions": _decode_json(row["questions_json"]),
        "sources": _decode_json(row["sources_json"]),
        "status": row["status"],
        "best_score": row["best_score"],
        "max_score": row["max_score"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row["completed_at"],
    }


def _practice_attempt_row(row: sqlite3.Row) -> dict[str, Any]:
    """Decode one practice attempt row, including its saved answers."""

    return {
        "attempt_no": row["attempt_no"],
        "status": row["status"],
        "answers": _decode_json(row["answers_json"]) or {},
        "results": _decode_json(row["results_json"]) or {},
        "option_orders": _decode_json(row["option_order_json"]) or {},
        "score": row["score"],
        "max_score": row["max_score"],
        "started_at": row["started_at"],
        "submitted_at": row["submitted_at"],
    }


_OBJECTIVE_TYPES = {"single-choice", "multiple-choice"}


def _option_order(
    questions: Sequence[Mapping[str, Any]], *, seed: str
) -> dict[str, list[str]]:
    """Shuffle the choices of each objective question for one attempt.

    The generator tends to place the correct option first, so every answer
    reads as A. The answers are stored as text, so shuffling here cannot break
    grading, and each attempt gets its own stable order.
    """

    rng = random.Random(seed)
    order: dict[str, list[str]] = {}
    for question in questions:
        choices = list(question.get("choices") or [])
        if question.get("type") in _OBJECTIVE_TYPES and len(choices) > 1:
            rng.shuffle(choices)
            order[str(question.get("id") or "")] = choices
    return order


def _insert_step(
    connection: sqlite3.Connection,
    message_id: str,
    position: int,
    step: Mapping[str, Any],
) -> None:
    """Insert one ordered work-chain step for a stored assistant message."""

    connection.execute(
        "INSERT INTO message_steps"
        " (id, message_id, position, step, status, detail, duration_ms,"
        "  policy, rule_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            step.get("id") or uuid.uuid4().hex,
            message_id,
            position,
            step["step"],
            step["status"],
            step.get("detail"),
            step.get("duration_ms"),
            step.get("policy"),
            step.get("rule_id"),
        ),
    )


class PracticeAttemptOpenError(RuntimeError):
    """A redo cannot start while another attempt is still open."""


class Storage:
    """Repository for the local SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open one short-lived connection with the repository pragmas."""

        with self._connect() as connection:
            yield connection

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # -- lifecycle ---------------------------------------------------------
    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)
            self._add_missing_message_columns(connection)
            self._add_missing_tool_call_columns(connection)
            self._add_missing_message_event_columns(connection)
            self._add_missing_soft_delete_columns(connection)
            self._add_missing_conversation_kind_column(connection)
            self._add_missing_practice_attempt_columns(connection)
            self._add_missing_revision_document_columns(connection)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _add_missing_message_columns(connection: sqlite3.Connection) -> None:
        """Add turn-metadata columns a database created before version 1 lacks."""

        existing = {
            row[1] for row in connection.execute("PRAGMA table_info(messages)")
        }
        for name, sql_type in _MESSAGE_METADATA_COLUMNS:
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE messages ADD COLUMN {name} {sql_type}"
                )

    @staticmethod
    def _add_missing_tool_call_columns(connection: sqlite3.Connection) -> None:
        """Add provider-call columns a database created before version 3 lacks."""

        existing = {
            row[1] for row in connection.execute("PRAGMA table_info(tool_calls)")
        }
        for name, sql_type in _TOOL_CALL_COLUMNS:
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE tool_calls ADD COLUMN {name} {sql_type}"
                )

    @staticmethod
    def _add_missing_message_event_columns(connection: sqlite3.Connection) -> None:
        """Add the step tag a database created before version 5 lacks."""

        existing = {
            row[1] for row in connection.execute("PRAGMA table_info(message_events)")
        }
        for name, sql_type in _MESSAGE_EVENT_COLUMNS:
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE message_events ADD COLUMN {name} {sql_type}"
                )

    @staticmethod
    def _add_missing_soft_delete_columns(connection: sqlite3.Connection) -> None:
        """Add the soft-delete stamp a database created before version 6 lacks."""

        for table, column in _KNOWLEDGE_SOFT_DELETE_COLUMNS:
            existing = {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} TEXT"
                )

    @staticmethod
    def _add_missing_conversation_kind_column(connection: sqlite3.Connection) -> None:
        """Add the conversation kind a database created before version 7 lacks."""

        existing = {
            row[1] for row in connection.execute("PRAGMA table_info(conversations)")
        }
        if "kind" not in existing:
            connection.execute(
                "ALTER TABLE conversations"
                " ADD COLUMN kind TEXT NOT NULL DEFAULT 'chat'"
            )

    @staticmethod
    def _add_missing_practice_attempt_columns(
        connection: sqlite3.Connection,
    ) -> None:
        """Add the option order a database created before version 9 lacks."""

        existing = {
            row[1]
            for row in connection.execute("PRAGMA table_info(practice_attempts)")
        }
        if "option_order_json" not in existing:
            connection.execute(
                "ALTER TABLE practice_attempts"
                " ADD COLUMN option_order_json TEXT NOT NULL DEFAULT '{}'"
            )

    @staticmethod
    def _add_missing_revision_document_columns(
        connection: sqlite3.Connection,
    ) -> None:
        """Add the generated document columns a database before version 11 lacks."""

        existing = {
            row[1]
            for row in connection.execute("PRAGMA table_info(revision_documents)")
        }
        for name, sql_type in (
            ("markdown", "TEXT"),
            ("intro_markdown", "TEXT"),
            ("model", "TEXT"),
            ("prompt_version", "TEXT"),
            ("generated_at", "TEXT"),
        ):
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE revision_documents ADD COLUMN {name} {sql_type}"
                )

    def ping(self) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    # -- users -------------------------------------------------------------
    def create_user(
        self,
        *,
        user_id: str,
        email: str,
        password_hash: str,
        role: str,
        status: str,
        created_at: datetime,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO users (id, email, password_hash, role, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, email, password_hash, role, status, iso(created_at)),
            )
        return self.find_user_by_id(user_id)  # type: ignore[return-value]

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
        return dict(row) if row is not None else None

    def find_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def update_user(self, user_id: str, **fields: Any) -> None:
        allowed = {"password_hash", "role", "status", "verified_at"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE users SET {assignments} WHERE id = ?",
                (*updates.values(), user_id),
            )

    # -- verification and reset codes --------------------------------------
    def replace_open_code(
        self,
        *,
        code_id: str,
        user_id: str,
        purpose: str,
        code_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM verification_codes WHERE user_id = ? AND purpose = ?"
                " AND consumed_at IS NULL",
                (user_id, purpose),
            )
            connection.execute(
                "INSERT INTO verification_codes"
                " (id, user_id, purpose, code_hash, created_at, expires_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    code_id,
                    user_id,
                    purpose,
                    code_hash,
                    iso(created_at),
                    iso(expires_at),
                ),
            )

    def find_open_code_for_user(
        self, user_id: str, purpose: str
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM verification_codes"
                " WHERE user_id = ? AND purpose = ? AND consumed_at IS NULL"
                " ORDER BY created_at DESC LIMIT 1",
                (user_id, purpose),
            ).fetchone()
        return dict(row) if row is not None else None

    def find_open_code_by_hash(
        self, purpose: str, code_hash: str
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM verification_codes"
                " WHERE purpose = ? AND code_hash = ? AND consumed_at IS NULL"
                " ORDER BY created_at DESC LIMIT 1",
                (purpose, code_hash),
            ).fetchone()
        return dict(row) if row is not None else None

    def consume_code(self, code_id: str, consumed_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE verification_codes SET consumed_at = ? WHERE id = ?",
                (iso(consumed_at), code_id),
            )

    # -- login sessions ----------------------------------------------------
    def create_login_session(
        self,
        *,
        session_id: str,
        user_id: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO login_sessions"
                " (id, user_id, created_at, last_seen_at, expires_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    user_id,
                    iso(created_at),
                    iso(created_at),
                    iso(expires_at),
                ),
            )

    def find_login_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM login_sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def touch_login_session(
        self, session_id: str, *, seen_at: datetime, expires_at: datetime
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE login_sessions SET last_seen_at = ?, expires_at = ?"
                " WHERE id = ?",
                (iso(seen_at), iso(expires_at), session_id),
            )

    def delete_login_session(self, session_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM login_sessions WHERE id = ?", (session_id,)
            )

    def delete_login_sessions_for_user(self, user_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM login_sessions WHERE user_id = ?", (user_id,)
            )
            return int(cursor.rowcount)

    # -- conversations and messages ---------------------------------------
    def create_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str | None,
        created_at: datetime,
        kind: str = "chat",
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations"
                " (id, user_id, title, kind, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    user_id,
                    title,
                    kind,
                    iso(created_at),
                    iso(created_at),
                ),
            )
        return self.find_conversation(conversation_id)  # type: ignore[return-value]

    def find_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_conversations(
        self, user_id: str, *, kind: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT c.*, (SELECT COUNT(*) FROM messages m"
            " WHERE m.conversation_id = c.id) AS message_count,"
            " (ps.conversation_id IS NOT NULL) AS has_practice,"
            " ps.status AS practice_status,"
            " ps.best_score AS practice_best_score,"
            " ps.max_score AS practice_max_score"
            " FROM conversations c"
            " LEFT JOIN practice_sessions ps ON ps.conversation_id = c.id"
            " WHERE c.user_id = ?"
        )
        parameters: list[Any] = [user_id]
        if kind is not None:
            query += " AND c.kind = ?"
            parameters.append(kind)
        query += " ORDER BY c.updated_at DESC, c.id"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [dict(row) for row in rows]

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete one conversation and everything cascading from it."""

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
            return cursor.rowcount > 0

    # -- practice sessions -------------------------------------------------
    def create_practice_session(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str | None,
        topic: str,
        questions: Sequence[Mapping[str, Any]],
        sources: Sequence[Mapping[str, Any]] = (),
        created_at: datetime,
    ) -> dict[str, Any]:
        """Store the generated questions and start the first attempt.

        Saving at generation time is what lets a reload resume the questions,
        so the first attempt opens in progress before any answer exists.
        """

        stored: list[dict[str, Any]] = []
        for index, question in enumerate(questions, start=1):
            item = dict(question)
            item.setdefault("id", f"q{index}")
            stored.append(item)
        max_score = sum(float(item.get("max_score") or 0) for item in stored)
        option_order = _option_order(stored, seed=f"{conversation_id}:1")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations"
                " (id, user_id, title, kind, created_at, updated_at)"
                " VALUES (?, ?, ?, 'practice', ?, ?)",
                (
                    conversation_id,
                    user_id,
                    title,
                    iso(created_at),
                    iso(created_at),
                ),
            )
            connection.execute(
                "INSERT INTO practice_sessions"
                " (conversation_id, topic, questions_json, sources_json, status,"
                "  best_score, max_score, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, 'not_started', 0, ?, ?, ?)",
                (
                    conversation_id,
                    topic,
                    json.dumps(stored),
                    json.dumps(list(sources)),
                    max_score,
                    iso(created_at),
                    iso(created_at),
                ),
            )
            connection.execute(
                "INSERT INTO practice_attempts"
                " (conversation_id, attempt_no, status, answers_json,"
                "  results_json, option_order_json, score, max_score, started_at)"
                " VALUES (?, 1, 'in_progress', '{}', '{}', ?, NULL, ?, ?)",
                (
                    conversation_id,
                    json.dumps(option_order),
                    max_score,
                    iso(created_at),
                ),
            )
        return {
            "conversation_id": conversation_id,
            "status": "not_started",
            "max_score": max_score,
        }

    def find_practice_session(
        self, conversation_id: str
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM practice_sessions WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return _practice_session_row(row)

    def list_practice_attempts(self, conversation_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM practice_attempts WHERE conversation_id = ?"
                " ORDER BY attempt_no",
                (conversation_id,),
            ).fetchall()
        return [_practice_attempt_row(row) for row in rows]

    def find_practice_attempt(
        self, conversation_id: str, attempt_no: int
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM practice_attempts"
                " WHERE conversation_id = ? AND attempt_no = ?",
                (conversation_id, attempt_no),
            ).fetchone()
        return None if row is None else _practice_attempt_row(row)

    def save_practice_answers(
        self,
        *,
        conversation_id: str,
        attempt_no: int,
        answers: Mapping[str, Any],
        updated_at: datetime,
    ) -> None:
        """Autosave the current answers and start the session if needed."""

        with self._connect() as connection:
            connection.execute(
                "UPDATE practice_attempts SET answers_json = ?"
                " WHERE conversation_id = ? AND attempt_no = ?",
                (
                    json.dumps(dict(answers)),
                    conversation_id,
                    attempt_no,
                ),
            )
            connection.execute(
                "UPDATE practice_sessions SET status = 'in_progress',"
                " updated_at = ? WHERE conversation_id = ?"
                " AND status = 'not_started'",
                (iso(updated_at), conversation_id),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (iso(updated_at), conversation_id),
            )

    def submit_practice_attempt(
        self,
        *,
        conversation_id: str,
        attempt_no: int,
        answers: Mapping[str, Any],
        results: Mapping[str, Mapping[str, Any]],
        submitted_at: datetime,
    ) -> dict[str, Any]:
        """Grade one attempt, and complete the session only on the first one."""

        score = sum(float(result.get("score") or 0) for result in results.values())
        with self._connect() as connection:
            session = connection.execute(
                "SELECT max_score FROM practice_sessions"
                " WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if session is None:
                raise LookupError(f"no practice session {conversation_id!r}")
            max_score = float(session["max_score"])
            connection.execute(
                "UPDATE practice_attempts"
                " SET answers_json = ?, results_json = ?, status = 'completed',"
                "  score = ?, max_score = ?, submitted_at = ?"
                " WHERE conversation_id = ? AND attempt_no = ?",
                (
                    json.dumps(dict(answers)),
                    json.dumps(dict(results)),
                    score,
                    max_score,
                    iso(submitted_at),
                    conversation_id,
                    attempt_no,
                ),
            )
            if attempt_no == 1:
                connection.execute(
                    "UPDATE practice_sessions"
                    " SET status = 'completed', completed_at = ?,"
                    "  best_score = MAX(best_score, ?), updated_at = ?"
                    " WHERE conversation_id = ?",
                    (
                        iso(submitted_at),
                        score,
                        iso(submitted_at),
                        conversation_id,
                    ),
                )
            else:
                connection.execute(
                    "UPDATE practice_sessions"
                    " SET best_score = MAX(best_score, ?), updated_at = ?"
                    " WHERE conversation_id = ?",
                    (score, iso(submitted_at), conversation_id),
                )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (iso(submitted_at), conversation_id),
            )
        return {"score": score, "max_score": max_score}

    def start_practice_attempt(
        self, *, conversation_id: str, started_at: datetime
    ) -> dict[str, Any]:
        """Open the next attempt without touching the first-attempt status."""

        with self._connect() as connection:
            session = connection.execute(
                "SELECT max_score, questions_json FROM practice_sessions"
                " WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if session is None:
                raise LookupError(f"no practice session {conversation_id!r}")
            row = connection.execute(
                "SELECT COALESCE(MAX(attempt_no), 0) AS current"
                " FROM practice_attempts WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            attempt_no = int(row["current"]) + 1
            max_score = float(session["max_score"])
            questions = _decode_json(session["questions_json"]) or []
            option_order = _option_order(
                questions, seed=f"{conversation_id}:{attempt_no}"
            )
            inserted = connection.execute(
                "INSERT INTO practice_attempts"
                " (conversation_id, attempt_no, status, answers_json,"
                "  results_json, option_order_json, score, max_score, started_at)"
                " SELECT ?, ?, 'in_progress', '{}', '{}', ?, NULL, ?, ?"
                " WHERE NOT EXISTS ("
                "  SELECT 1 FROM practice_attempts"
                "  WHERE conversation_id = ? AND status = 'in_progress')",
                (
                    conversation_id,
                    attempt_no,
                    json.dumps(option_order),
                    max_score,
                    iso(started_at),
                    conversation_id,
                ),
            )
            if inserted.rowcount == 0:
                raise PracticeAttemptOpenError(
                    f"practice {conversation_id!r} already has an open attempt"
                )
            connection.execute(
                "UPDATE practice_sessions SET updated_at = ?"
                " WHERE conversation_id = ?",
                (iso(started_at), conversation_id),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (iso(started_at), conversation_id),
            )
        stored = self.find_practice_attempt(conversation_id, attempt_no)
        assert stored is not None
        return stored

    def delete_practice_attempt(
        self,
        *,
        conversation_id: str,
        attempt_no: int,
        updated_at: datetime,
    ) -> dict[str, Any] | None:
        """Delete one attempt, and the session only when none remain.

        The remaining attempts keep their order and are renumbered, and the
        earliest one decides whether the session is new, in progress, or
        completed, so the first-attempt rule survives a deletion.
        """

        with self._connect() as connection:
            session = connection.execute(
                "SELECT conversation_id FROM practice_sessions"
                " WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if session is None:
                raise LookupError(f"no practice session {conversation_id!r}")
            connection.execute(
                "DELETE FROM practice_attempts"
                " WHERE conversation_id = ? AND attempt_no = ?",
                (conversation_id, attempt_no),
            )
            remaining = connection.execute(
                "SELECT attempt_no FROM practice_attempts"
                " WHERE conversation_id = ? ORDER BY attempt_no",
                (conversation_id,),
            ).fetchall()
            if not remaining:
                connection.execute(
                    "DELETE FROM conversations WHERE id = ?", (conversation_id,)
                )
                return None
            for new_no, row in enumerate(remaining, start=1):
                if row["attempt_no"] != new_no:
                    connection.execute(
                        "UPDATE practice_attempts SET attempt_no = ?"
                        " WHERE conversation_id = ? AND attempt_no = ?",
                        (new_no, conversation_id, row["attempt_no"]),
                    )
            attempts = connection.execute(
                "SELECT * FROM practice_attempts"
                " WHERE conversation_id = ? ORDER BY attempt_no",
                (conversation_id,),
            ).fetchall()
            earliest = attempts[0]
            if earliest["status"] == "completed":
                status = "completed"
                completed_at = earliest["submitted_at"]
            else:
                answers = _decode_json(earliest["answers_json"]) or {}
                results = _decode_json(earliest["results_json"]) or {}
                status = "in_progress" if (answers or results) else "not_started"
                completed_at = None
            best_score = max(
                (
                    float(attempt["score"])
                    for attempt in attempts
                    if attempt["status"] == "completed" and attempt["score"] is not None
                ),
                default=0,
            )
            connection.execute(
                "UPDATE practice_sessions SET status = ?, best_score = ?,"
                " completed_at = ?, updated_at = ? WHERE conversation_id = ?",
                (
                    status,
                    best_score,
                    completed_at,
                    iso(updated_at),
                    conversation_id,
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (iso(updated_at), conversation_id),
            )
        return self.find_practice_session(conversation_id)

    # -- revision guide ----------------------------------------------------
    def replace_revision_outline(
        self,
        *,
        themes: Sequence[Mapping[str, Any]],
        documents: Sequence[Mapping[str, Any]],
        created_at: datetime,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        """Replace the whole outline; one document belongs to one theme."""

        with self._connect() as connection:
            connection.execute("DELETE FROM revision_documents")
            connection.execute("DELETE FROM revision_themes")
            for theme in themes:
                connection.execute(
                    "INSERT INTO revision_themes"
                    " (id, title, summary, position, created_at, model,"
                    "  prompt_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        theme["id"],
                        theme["title"],
                        theme["summary"],
                        int(theme["position"]),
                        iso(created_at),
                        model,
                        prompt_version,
                    ),
                )
            for document in documents:
                connection.execute(
                    "INSERT INTO revision_documents"
                    " (doc_id, theme_id, category, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (
                        document["doc_id"],
                        document["theme_id"],
                        document["category"],
                        iso(created_at),
                    ),
                )

    def list_revision_tree(self, user_id: str) -> list[dict[str, Any]]:
        """Return the outline with per-document totals and the user's progress."""

        with self._connect() as connection:
            themes = connection.execute(
                "SELECT * FROM revision_themes ORDER BY position, id"
            ).fetchall()
            documents = connection.execute(
                "SELECT d.doc_id, d.theme_id, d.category, d.markdown, doc.title,"
                " doc.filename, COUNT(p.id) AS total,"
                " COALESCE(SUM(CASE WHEN rp.mastered = 1 THEN 1 ELSE 0 END), 0)"
                " AS mastered"
                " FROM revision_documents d"
                " LEFT JOIN kb_documents doc ON doc.id = d.doc_id"
                " LEFT JOIN revision_points p ON p.doc_id = d.doc_id"
                " LEFT JOIN revision_progress rp ON rp.point_id = p.id"
                " AND rp.user_id = ?"
                " GROUP BY d.doc_id, d.theme_id, d.category, d.markdown,"
                " doc.title, doc.filename"
                " ORDER BY d.category, doc.title, d.doc_id",
                (user_id,),
            ).fetchall()
        by_theme: dict[str, list[dict[str, Any]]] = {}
        for row in documents:
            item = dict(row)
            item["generated"] = item.pop("markdown") is not None
            item["total"] = int(item["total"])
            item["mastered"] = int(item["mastered"])
            by_theme.setdefault(item.pop("theme_id"), []).append(item)
        return [
            {
                "id": theme["id"],
                "title": theme["title"],
                "summary": theme["summary"],
                "position": theme["position"],
                "total": sum(doc["total"] for doc in by_theme.get(theme["id"], [])),
                "mastered": sum(
                    doc["mastered"] for doc in by_theme.get(theme["id"], [])
                ),
                "documents": by_theme.get(theme["id"], []),
            }
            for theme in themes
        ]

    def revision_outline_status(self) -> dict[str, Any]:
        """Return the outline, generation, and point counts for the CLI."""

        with self._connect() as connection:
            themes = connection.execute(
                "SELECT t.title, COUNT(d.doc_id) AS documents"
                " FROM revision_themes t"
                " LEFT JOIN revision_documents d ON d.theme_id = t.id"
                " GROUP BY t.id ORDER BY t.position, t.id"
            ).fetchall()
            totals = connection.execute(
                "SELECT COUNT(*) AS documents,"
                " COALESCE(SUM(markdown IS NOT NULL), 0) AS generated"
                " FROM revision_documents"
            ).fetchone()
            points = connection.execute(
                "SELECT COUNT(*) AS points FROM revision_points"
            ).fetchone()
        return {
            "themes": [dict(row) for row in themes],
            "documents": int(totals["documents"]),
            "generated": int(totals["generated"]),
            "points": int(points["points"]),
        }

    def revision_snapshot(self) -> dict[str, Any]:
        """Return a portable snapshot of the outline, chapters, and points.

        The snapshot has no user data; progress stays in the local database.
        """

        with self._connect() as connection:
            themes = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, title, summary, position, created_at, model,"
                    " prompt_version FROM revision_themes ORDER BY position, id"
                )
            ]
            documents = [
                dict(row)
                for row in connection.execute(
                    "SELECT d.doc_id, d.theme_id, d.category, d.markdown,"
                    " d.intro_markdown, d.model, d.prompt_version,"
                    " d.generated_at, doc.title, doc.filename"
                    " FROM revision_documents d"
                    " LEFT JOIN kb_documents doc ON doc.id = d.doc_id"
                    " ORDER BY d.doc_id"
                )
            ]
            points = [
                dict(row)
                for row in connection.execute(
                    "SELECT doc_id, title, body_markdown, position, page_no"
                    " FROM revision_points ORDER BY doc_id, position"
                )
            ]
        by_doc: dict[str, list[dict[str, Any]]] = {}
        for point in points:
            by_doc.setdefault(point.pop("doc_id"), []).append(point)
        for document in documents:
            document["points"] = by_doc.get(document["doc_id"], [])
        return {
            "schema": "vt-revision/1",
            "themes": themes,
            "documents": documents,
        }

    def import_revision_snapshot(
        self,
        payload: Mapping[str, Any],
        *,
        imported_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Load a tracked snapshot when the revision tables are still empty."""

        if payload.get("schema") != "vt-revision/1":
            raise ValueError("unsupported revision snapshot schema")
        themes = payload.get("themes") or []
        documents = payload.get("documents") or []
        if not themes or not documents:
            raise ValueError("the revision snapshot is empty")
        now = iso(imported_at or datetime.now(timezone.utc))
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT COUNT(*) AS count FROM revision_themes"
            ).fetchone()["count"]
            if int(existing) > 0:
                return {
                    "imported": False,
                    "themes": int(existing),
                    "documents": 0,
                    "points": 0,
                }
            known = {
                row[0]
                for row in connection.execute("SELECT id FROM kb_documents")
            }
            missing = [
                document["doc_id"]
                for document in documents
                if document["doc_id"] not in known
            ]
            if missing:
                raise LookupError(
                    "the corpus is not imported: " + ", ".join(sorted(missing))
                )
            for theme in themes:
                connection.execute(
                    "INSERT INTO revision_themes"
                    " (id, title, summary, position, created_at, model,"
                    "  prompt_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        theme["id"],
                        theme["title"],
                        theme["summary"],
                        int(theme["position"]),
                        theme.get("created_at") or now,
                        theme.get("model"),
                        theme.get("prompt_version"),
                    ),
                )
            point_count = 0
            for document in documents:
                connection.execute(
                    "INSERT INTO revision_documents"
                    " (doc_id, theme_id, category, created_at, markdown,"
                    "  intro_markdown, model, prompt_version, generated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        document["doc_id"],
                        document["theme_id"],
                        document["category"],
                        now,
                        document.get("markdown"),
                        document.get("intro_markdown"),
                        document.get("model"),
                        document.get("prompt_version"),
                        document.get("generated_at"),
                    ),
                )
                for position, point in enumerate(document.get("points") or []):
                    title = str(point["title"]).strip()
                    point_id = hashlib.sha256(
                        f"{document['doc_id']}\n{title}".encode("utf-8")
                    ).hexdigest()[:16]
                    connection.execute(
                        "INSERT INTO revision_points"
                        " (id, doc_id, title, body_markdown, position, page_no,"
                        "  created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            point_id,
                            document["doc_id"],
                            title,
                            point["body_markdown"],
                            position,
                            point.get("page_no"),
                            now,
                        ),
                    )
                    point_count += 1
        return {
            "imported": True,
            "themes": len(themes),
            "documents": len(documents),
            "points": point_count,
        }

    def list_revision_chunks(self, doc_id: str) -> list[dict[str, Any]]:
        """Return the OCR chunks of one document in reading order."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT page_no, section, text FROM kb_chunks WHERE doc_id = ?"
                " ORDER BY page_no, chunk_index",
                (doc_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def find_revision_document(self, doc_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT d.*, doc.title, doc.filename, doc.summary,"
                " t.title AS theme_title"
                " FROM revision_documents d"
                " LEFT JOIN kb_documents doc ON doc.id = d.doc_id"
                " LEFT JOIN revision_themes t ON t.id = d.theme_id"
                " WHERE d.doc_id = ?",
                (doc_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def revision_document_detail(
        self, doc_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Return one generated document with its points and the user's checks."""

        document = self.find_revision_document(doc_id)
        if document is None or document.get("markdown") is None:
            return None
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT p.id, p.title, p.body_markdown, p.position, p.page_no,"
                " COALESCE(rp.mastered, 0) AS mastered"
                " FROM revision_points p"
                " LEFT JOIN revision_progress rp ON rp.point_id = p.id"
                " AND rp.user_id = ?"
                " WHERE p.doc_id = ? ORDER BY p.position",
                (user_id, doc_id),
            ).fetchall()
        points = [dict(row) for row in rows]
        for point in points:
            point["mastered"] = bool(point["mastered"])
        return {
            "document": document,
            "points": points,
            "total": len(points),
            "mastered": sum(1 for point in points if point["mastered"]),
        }

    def save_revision_document(
        self,
        *,
        doc_id: str,
        markdown: str,
        intro_markdown: str,
        points: Sequence[Mapping[str, Any]],
        model: str | None,
        prompt_version: str,
        generated_at: datetime,
    ) -> int:
        """Replace one generated document and its knowledge points."""

        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE revision_documents SET markdown = ?, intro_markdown = ?,"
                " model = ?, prompt_version = ?, generated_at = ?"
                " WHERE doc_id = ?",
                (
                    markdown,
                    intro_markdown,
                    model,
                    prompt_version,
                    iso(generated_at),
                    doc_id,
                ),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"no revision document {doc_id!r}")
            prepared = []
            for position, point in enumerate(points):
                title = str(point["title"]).strip()
                point_id = hashlib.sha256(
                    f"{doc_id}\n{title}".encode("utf-8")
                ).hexdigest()[:16]
                prepared.append((point_id, title, point, position))
            new_ids = {row[0] for row in prepared}
            existing = {
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM revision_points WHERE doc_id = ?", (doc_id,)
                )
            }
            removed = existing - new_ids
            if removed:
                placeholders = ", ".join("?" for _ in removed)
                connection.execute(
                    "DELETE FROM revision_points"
                    f" WHERE doc_id = ? AND id IN ({placeholders})",
                    (doc_id, *removed),
                )
            if existing & new_ids:
                connection.execute(
                    "UPDATE revision_points SET position = position + 1000000"
                    " WHERE doc_id = ?",
                    (doc_id,),
                )
            for point_id, title, point, position in prepared:
                connection.execute(
                    "INSERT INTO revision_points"
                    " (id, doc_id, title, body_markdown, position, page_no,"
                    "  created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT(id) DO UPDATE SET"
                    " title = excluded.title,"
                    " body_markdown = excluded.body_markdown,"
                    " position = excluded.position,"
                    " page_no = excluded.page_no",
                    (
                        point_id,
                        doc_id,
                        title,
                        point["body_markdown"],
                        position,
                        point.get("page_no"),
                        iso(generated_at),
                    ),
                )
        return len(points)

    def set_revision_progress(
        self,
        *,
        user_id: str,
        point_id: str,
        mastered: bool,
        updated_at: datetime,
    ) -> dict[str, Any] | None:
        """Store one self-check and return the document's new counts."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT doc_id FROM revision_points WHERE id = ?", (point_id,)
            ).fetchone()
            if row is None:
                return None
            doc_id = row["doc_id"]
            connection.execute(
                "INSERT INTO revision_progress"
                " (user_id, point_id, mastered, updated_at)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(user_id, point_id) DO UPDATE SET"
                " mastered = excluded.mastered, updated_at = excluded.updated_at",
                (user_id, point_id, 1 if mastered else 0, iso(updated_at)),
            )
            counts = connection.execute(
                "SELECT COUNT(p.id) AS total,"
                " COALESCE(SUM(CASE WHEN rp.mastered = 1 THEN 1 ELSE 0 END), 0)"
                " AS mastered"
                " FROM revision_points p"
                " LEFT JOIN revision_progress rp ON rp.point_id = p.id"
                " AND rp.user_id = ?"
                " WHERE p.doc_id = ?",
                (user_id, doc_id),
            ).fetchone()
        return {
            "doc_id": doc_id,
            "total": int(counts["total"]),
            "mastered": int(counts["mastered"]),
        }

    def list_revision_candidates(self) -> list[dict[str, Any]]:
        """Return the summarised documents an outline can group."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id AS doc_id, title, filename, summary FROM kb_documents"
                " WHERE deleted_at IS NULL AND summary IS NOT NULL"
                " AND summary <> '' ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def record_progress(
        self,
        *,
        user_id: str,
        topic: str,
        covered_points: Sequence[str],
        mastered_points: Sequence[str],
    ) -> None:
        """Record the knowledge points a quiz covered and fully mastered.

        Both sets only grow: a covered point stays covered, and a mastered
        point stays mastered even when a later attempt is not full marks.
        """

        mastered_set = set(mastered_points)
        points = set(covered_points) | mastered_set
        if not points:
            return
        with self._connect() as connection:
            for point in points:
                connection.execute(
                    "INSERT INTO topic_progress"
                    " (user_id, topic, knowledge_point, covered, mastered)"
                    " VALUES (?, ?, ?, 1, ?)"
                    " ON CONFLICT(user_id, topic, knowledge_point) DO UPDATE SET"
                    " covered = 1,"
                    " mastered = MAX(mastered, excluded.mastered)",
                    (user_id, topic, point, 1 if point in mastered_set else 0),
                )

    def list_progress(self, user_id: str) -> list[dict[str, Any]]:
        """Return one row per topic knowledge point with its flags."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT topic, knowledge_point, covered, mastered"
                " FROM topic_progress WHERE user_id = ?"
                " ORDER BY topic, knowledge_point",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def touch_conversation(self, conversation_id: str, *, updated_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (iso(updated_at), conversation_id),
            )

    def next_message_sequence(self, conversation_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS current FROM messages"
                " WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        return int(row["current"]) + 1

    def add_message(
        self,
        *,
        message_id: str,
        conversation_id: str,
        sequence: int,
        role: str,
        content: str,
        created_at: datetime,
        provider: str | None = None,
        tier: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages"
                " (id, conversation_id, sequence, role, content, provider, tier,"
                "  created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    conversation_id,
                    sequence,
                    role,
                    content,
                    provider,
                    tier,
                    iso(created_at),
                ),
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "sequence": sequence,
            "role": role,
            "content": content,
            "provider": provider,
            "tier": tier,
            "created_at": iso(created_at),
        }

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        """Return a conversation's messages with their persisted turn metadata."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ?"
                " ORDER BY sequence",
                (conversation_id,),
            ).fetchall()
            messages = [dict(row) for row in rows]
            by_id = {message["id"]: message for message in messages}
            for message in messages:
                message["work_steps"] = []
                message["sources"] = []
                message["citations"] = []
                message["tool_calls"] = []
                message["events"] = []

            steps = connection.execute(
                "SELECT s.* FROM message_steps s"
                " JOIN messages m ON m.id = s.message_id"
                " WHERE m.conversation_id = ?"
                " ORDER BY s.message_id, s.position",
                (conversation_id,),
            ).fetchall()
            for row in steps:
                by_id[row["message_id"]]["work_steps"].append(
                    {
                        "id": row["id"],
                        "position": row["position"],
                        "step": row["step"],
                        "status": row["status"],
                        "detail": row["detail"],
                        "duration_ms": row["duration_ms"],
                        "policy": row["policy"],
                        "rule_id": row["rule_id"],
                    }
                )

            sources = connection.execute(
                "SELECT s.* FROM message_sources s"
                " JOIN messages m ON m.id = s.message_id"
                " WHERE m.conversation_id = ?"
                " ORDER BY s.message_id, s.position",
                (conversation_id,),
            ).fetchall()
            for row in sources:
                by_id[row["message_id"]]["sources"].append(
                    {
                        "position": row["position"],
                        "marker": row["marker"],
                        "kind": row["kind"],
                        "title": row["title"],
                        "summary": row["summary"],
                        "doc_id": row["doc_id"],
                        "page_no": row["page_no"],
                        "url": row["url"],
                        "chunk_id": row["chunk_id"],
                    }
                )

            citations = connection.execute(
                "SELECT c.* FROM citations c"
                " JOIN messages m ON m.id = c.message_id"
                " WHERE m.conversation_id = ?"
                " ORDER BY c.message_id, c.position",
                (conversation_id,),
            ).fetchall()
            for row in citations:
                by_id[row["message_id"]]["citations"].append(
                    {
                        "position": row["position"],
                        "doc_id": row["doc_id"],
                        "page_no": row["page_no"],
                        "quoted_span": row["quoted_span"],
                        "bbox_norm": _decode_json(row["bbox_norm"]),
                        "verified_at": row["verified_at"],
                    }
                )

            tool_calls = connection.execute(
                "SELECT t.* FROM tool_calls t"
                " JOIN messages m ON m.id = t.message_id"
                " WHERE m.conversation_id = ?"
                " ORDER BY t.message_id, t.position",
                (conversation_id,),
            ).fetchall()
            for row in tool_calls:
                by_id[row["message_id"]]["tool_calls"].append(
                    {
                        "position": row["position"],
                        "name": row["name"],
                        "command": _decode_json(row["command_json"]),
                        "exit_code": row["exit_code"],
                        "output": row["output"],
                        "status": row["status"],
                        "tool_call_id": row["tool_call_id"],
                        "arguments": _decode_json(row["arguments_json"]),
                        "result": _decode_json(row["result_json"]),
                        "duration_ms": row["duration_ms"],
                    }
                )

            events = connection.execute(
                "SELECT e.* FROM message_events e"
                " JOIN messages m ON m.id = e.message_id"
                " WHERE m.conversation_id = ?"
                " ORDER BY e.message_id, e.position",
                (conversation_id,),
            ).fetchall()
            for row in events:
                message = by_id[row["message_id"]]
                tool_call = None
                if row["kind"] == "tool_call":
                    position = row["tool_call_position"]
                    tool_call = next(
                        (
                            call
                            for call in message["tool_calls"]
                            if call["position"] == position
                        ),
                        None,
                    )
                message["events"].append(
                    {
                        "position": row["position"],
                        "kind": row["kind"],
                        "reasoning": row["reasoning"],
                        "step_id": row["step_id"],
                        "tool_call": tool_call,
                    }
                )
        return messages

    def add_assistant_turn(
        self,
        *,
        message_id: str,
        conversation_id: str,
        sequence: int,
        content: str,
        created_at: datetime,
        provider: str | None = None,
        tier: str | None = None,
        model: str | None = None,
        thinking: str | None = None,
        reasoning: str | None = None,
        steps: Sequence[Mapping[str, Any]] = (),
        sources: Sequence[Mapping[str, Any]] = (),
        citations: Sequence[Mapping[str, Any]] = (),
        tool_calls: Sequence[Mapping[str, Any]] = (),
        events: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Persist one assistant turn and its turn metadata in one transaction.

        A failure while inserting a child row rolls the whole turn back, so a
        stored answer either has all of its metadata or none of it.
        """

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages"
                " (id, conversation_id, sequence, role, content, provider, tier,"
                "  created_at, reasoning, model, thinking)"
                " VALUES (?, ?, ?, 'assistant', ?, ?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    conversation_id,
                    sequence,
                    content,
                    provider,
                    tier,
                    iso(created_at),
                    reasoning,
                    model,
                    thinking,
                ),
            )
            for position, step in enumerate(steps):
                _insert_step(connection, message_id, position, step)
            for position, source in enumerate(sources):
                connection.execute(
                    "INSERT INTO message_sources"
                    " (id, message_id, position, marker, kind, title, summary,"
                    "  doc_id, page_no, url, chunk_id)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex,
                        message_id,
                        position,
                        int(source["marker"]),
                        source["kind"],
                        source["title"],
                        source["summary"],
                        source.get("doc_id"),
                        source.get("page_no"),
                        source.get("url"),
                        source.get("chunk_id"),
                    ),
                )
            for position, citation in enumerate(citations):
                connection.execute(
                    "INSERT INTO citations"
                    " (id, message_id, position, doc_id, page_no, quoted_span,"
                    "  bbox_norm, verified_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex,
                        message_id,
                        position,
                        citation["doc_id"],
                        citation["page_no"],
                        citation["quoted_span"],
                        _encode_json(citation.get("bbox_norm")),
                        citation.get("verified_at"),
                    ),
                )
            for position, call in enumerate(tool_calls):
                connection.execute(
                    "INSERT INTO tool_calls"
                    " (id, message_id, position, name, command_json, exit_code,"
                    "  output, status, tool_call_id, arguments_json, result_json,"
                    "  duration_ms)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex,
                        message_id,
                        position,
                        call["name"],
                        _encode_json(call.get("command")),
                        call.get("exit_code"),
                        call.get("output"),
                        call["status"],
                        call.get("tool_call_id"),
                        _encode_json(call.get("arguments")),
                        _encode_json(call.get("result")),
                        call.get("duration_ms"),
                    ),
                )
            for position, event in enumerate(events):
                connection.execute(
                    "INSERT INTO message_events"
                    " (id, message_id, position, kind, reasoning,"
                    "  tool_call_position, step_id)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex,
                        message_id,
                        position,
                        event["kind"],
                        event.get("reasoning"),
                        event.get("tool_call_position"),
                        event.get("step_id"),
                    ),
                )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "sequence": sequence,
            "role": "assistant",
            "content": content,
            "provider": provider,
            "tier": tier,
            "created_at": iso(created_at),
            "reasoning": reasoning,
            "model": model,
            "thinking": thinking,
            "work_steps": list(steps),
            "sources": list(sources),
            "citations": list(citations),
            "tool_calls": list(tool_calls),
            "events": list(events),
        }

    # -- knowledge builds --------------------------------------------------
    def create_build(
        self,
        *,
        build_id: str,
        user_id: str,
        request_json: str,
        created_at: datetime,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO knowledge_builds"
                " (id, user_id, state, request_json, created_at, updated_at)"
                " VALUES (?, ?, 'queued', ?, ?, ?)",
                (build_id, user_id, request_json, iso(created_at), iso(created_at)),
            )
        return self.find_build(build_id)  # type: ignore[return-value]

    def find_build(self, build_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_builds WHERE id = ?", (build_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_builds(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_builds ORDER BY created_at DESC, id"
            ).fetchall()
        return [dict(row) for row in rows]

    def active_build(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_builds WHERE state IN ('queued', 'running')"
                " ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row is not None else None

    def update_build(
        self,
        build_id: str,
        *,
        state: str,
        updated_at: datetime,
        job_id: str | None = None,
        records_path: str | None = None,
        records_count: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE knowledge_builds SET state = ?, updated_at = ?,"
                " job_id = COALESCE(?, job_id),"
                " records_path = COALESCE(?, records_path),"
                " records_count = COALESCE(?, records_count),"
                " error = ? WHERE id = ?",
                (
                    state,
                    iso(updated_at),
                    job_id,
                    records_path,
                    records_count,
                    error,
                    build_id,
                ),
            )

    def fail_interrupted_builds(self, *, updated_at: datetime) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE knowledge_builds SET state = 'failed', updated_at = ?,"
                " error = 'interrupted by restart'"
                " WHERE state IN ('queued', 'running')",
                (iso(updated_at),),
            )
            return int(cursor.rowcount)

    # -- generic helpers ---------------------------------------------------
    def scalar(self, sql: str, parameters: tuple[Any, ...] = ()) -> Any:
        """Run a single-value query, used by small counts in services."""

        with self._connect() as connection:
            row = connection.execute(sql, parameters).fetchone()
        return None if row is None else row[0]


def row_to_public_user(row: Mapping[str, Any]) -> dict[str, Any]:
    """Strip the password hash from a user row before it leaves the backend."""

    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }
