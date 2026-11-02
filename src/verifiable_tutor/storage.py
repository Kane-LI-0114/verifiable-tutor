"""SQLite storage for accounts, sessions, conversations, and builds.

The database lives under the ignored ``data/app/`` directory. Each operation
opens a short-lived connection, enables WAL and foreign keys, and commits on
success, so sync endpoint code running in the AnyIO threadpool never shares a
connection across threads.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

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
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations(user_id, updated_at DESC);

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
"""


def iso(moment: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC string with second precision."""

    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp written by :func:`iso`."""

    return datetime.fromisoformat(value)


class Storage:
    """Repository for the local SQLite database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

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
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations"
                " (id, user_id, title, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (conversation_id, user_id, title, iso(created_at), iso(created_at)),
            )
        return self.find_conversation(conversation_id)  # type: ignore[return-value]

    def find_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT c.*, (SELECT COUNT(*) FROM messages m"
                " WHERE m.conversation_id = c.id) AS message_count"
                " FROM conversations c WHERE c.user_id = ?"
                " ORDER BY c.updated_at DESC, c.id",
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
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ?"
                " ORDER BY sequence",
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

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
