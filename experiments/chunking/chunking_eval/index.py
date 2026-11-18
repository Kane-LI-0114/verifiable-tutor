"""An evaluation-only SQLite store shaped like ``KnowledgeStore``.

``HybridRetriever`` only needs ``search_chunks``, ``get_chunks``,
``stored_vectors`` and ``index_state``. Implementing those four methods here
keeps production code untouched while reusing the production BM25, dense, and
RRF logic. The table adds ``page_nos`` so a cross-page chunk can map back to
every page it covers.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_FTS_WHITESPACE = re.compile(r"\s+")


def _fts_terms(query: str) -> list[str]:
    return [term for term in _FTS_WHITESPACE.split(query or "") if term.strip()]


def _fts_query(query: str, *, join: str = " ") -> str:
    return f" {join} ".join(
        '"' + term.replace('"', '""') + '"' for term in _fts_terms(query)
    )


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "chunk_id": row["chunk_id"],
        "doc_id": row["doc_id"],
        "page_no": int(row["page_no"]),
        "page_nos": json.loads(row["page_nos"] or "[]"),
        "chunk_index": int(row["chunk_index"] or 0),
        "section_title": row["section"],
        "text": row["text"],
        "embed_text": row["embed_text"],
        "token_estimate": int(row["token_estimate"] or 0),
        "oversize": bool(row["oversize"]),
        "chunker_version": row["chunker_version"],
        "score": row["score"] if "score" in row.keys() else None,
    }


class EvalStore:
    """A small chunk store with FTS5 and float32 embedding BLOBs."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._create()

    def _create(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS eval_chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                page_no INTEGER NOT NULL,
                page_nos TEXT NOT NULL,
                chunk_index INTEGER,
                section TEXT,
                text TEXT NOT NULL,
                embed_text TEXT,
                token_estimate INTEGER,
                oversize INTEGER NOT NULL DEFAULT 0,
                chunker_version TEXT NOT NULL,
                embedding BLOB,
                embedding_model TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS eval_chunks_fts USING fts5(
                text, section,
                content='eval_chunks',
                content_rowid='rowid',
                tokenize='unicode61 remove_diacritics 2'
            );
            CREATE TABLE IF NOT EXISTS eval_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self._connection.commit()

    def add_chunks(self, chunks: Sequence[Mapping]) -> None:
        self._connection.executemany(
            "INSERT OR REPLACE INTO eval_chunks (chunk_id, doc_id, page_no,"
            " page_nos, chunk_index, section, text, embed_text, token_estimate,"
            " oversize, chunker_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    chunk["chunk_id"],
                    chunk["doc_id"],
                    int(chunk["page_no"]),
                    json.dumps(chunk.get("page_nos") or [int(chunk["page_no"])]),
                    int(chunk.get("chunk_index") or 0),
                    chunk.get("section_title"),
                    chunk["text"],
                    chunk.get("embed_text") or chunk["text"],
                    int(chunk.get("token_estimate") or 0),
                    1 if chunk.get("oversize") else 0,
                    chunk.get("chunker_version") or "eval/unknown",
                )
                for chunk in chunks
            ],
        )
        self._connection.execute(
            "INSERT INTO eval_chunks_fts(eval_chunks_fts) VALUES('rebuild')"
        )
        self._connection.commit()

    def search_chunks(
        self, query: str, *, limit: int = 20, doc_id: str | None = None
    ) -> list[dict[str, Any]]:
        if not _fts_terms(query):
            return []
        filters = " AND c.doc_id = ?" if doc_id is not None else ""
        rows: list[sqlite3.Row] = []
        for join in (" ", "OR"):
            parameters: list[Any] = [_fts_query(query, join=join)]
            if doc_id is not None:
                parameters.append(doc_id)
            parameters.append(limit)
            rows = self._connection.execute(
                "SELECT c.*, bm25(eval_chunks_fts) AS score"
                " FROM eval_chunks_fts"
                " JOIN eval_chunks c ON c.rowid = eval_chunks_fts.rowid"
                " WHERE eval_chunks_fts MATCH ?"
                f"{filters}"
                " ORDER BY score, c.chunk_id LIMIT ?",
                parameters,
            ).fetchall()
            if rows:
                break
        return [_row_dict(row) for row in rows]

    def get_chunks(self, chunk_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = list(dict.fromkeys(str(chunk_id) for chunk_id in chunk_ids))
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._connection.execute(
            f"SELECT * FROM eval_chunks WHERE chunk_id IN ({placeholders})",
            ids,
        ).fetchall()
        by_id = {row["chunk_id"]: _row_dict(row) for row in rows}
        return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]

    def set_embeddings(
        self,
        doc_id: str,
        vectors: Mapping[str, bytes],
        *,
        model: str,
        built_at: str,
    ) -> None:
        self._connection.executemany(
            "UPDATE eval_chunks SET embedding = ?, embedding_model = ?"
            " WHERE chunk_id = ? AND doc_id = ?",
            [
                (sqlite3.Binary(vector), model, chunk_id, doc_id)
                for chunk_id, vector in vectors.items()
            ],
        )
        self._set_meta("model", model)
        self._set_meta("built_at", built_at)
        self._connection.commit()

    def _set_meta(self, key: str, value: str) -> None:
        self._connection.execute(
            "INSERT INTO eval_meta(key, value) VALUES(?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def _meta(self, key: str) -> str:
        row = self._connection.execute(
            "SELECT value FROM eval_meta WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row else ""

    def stored_vectors(self) -> tuple[list[str], list[bytes]]:
        rows = self._connection.execute(
            "SELECT chunk_id, embedding FROM eval_chunks"
            " WHERE embedding IS NOT NULL ORDER BY rowid"
        ).fetchall()
        return [row["chunk_id"] for row in rows], [row["embedding"] for row in rows]

    def index_state(self) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT COUNT(*) AS chunks,"
            " SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) AS vectors"
            " FROM eval_chunks"
        ).fetchone()
        sample = self._connection.execute(
            "SELECT embedding FROM eval_chunks"
            " WHERE embedding IS NOT NULL LIMIT 1"
        ).fetchone()
        dimension = len(sample["embedding"]) // 4 if sample else 0
        version = self._connection.execute(
            "SELECT chunker_version FROM eval_chunks LIMIT 1"
        ).fetchone()
        return {
            "chunks": int(row["chunks"] or 0),
            "vectors": int(row["vectors"] or 0),
            "dimension": dimension,
            "model": self._meta("model"),
            "chunker_version": version["chunker_version"] if version else "",
            "built_at": self._meta("built_at"),
        }

    def page_map(self) -> dict[str, list[tuple[str, int]]]:
        rows = self._connection.execute(
            "SELECT chunk_id, doc_id, page_nos FROM eval_chunks"
        ).fetchall()
        return {
            row["chunk_id"]: [
                (row["doc_id"], int(page)) for page in json.loads(row["page_nos"] or "[]")
            ]
            for row in rows
        }

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM eval_chunks").fetchone()
        return int(row["n"] or 0)

    def close(self) -> None:
        self._connection.close()
