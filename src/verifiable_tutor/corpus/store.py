"""Local knowledge store: folders, documents, chunks, full-text search, index state.

The store is the one owner of the corpus rows ([ADR-0015](../../../docs/adr/0015-local-knowledge-store-and-chunking.md)).
It keeps SQL in :mod:`verifiable_tutor.storage`'s schema and exposes the
operations the ingestion CLI, the HTTP API, and the retriever need. Rows are
returned as plain dicts with the column names the API serializes.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from typing import Any, Iterable, Mapping, Sequence

from ..storage import Storage

#: Document statuses, matching the CHECK constraint in the storage schema.
DOCUMENT_STATUSES = (
    "uploading",
    "uploaded",
    "upload_failed",
    "processing",
    "ready",
    "failed",
)

_FTS_WHITESPACE = re.compile(r"\s+")


def _fts_terms(query: str) -> list[str]:
    return [term for term in _FTS_WHITESPACE.split(query or "") if term.strip()]


def _fts_query(query: str, *, join: str = " ") -> str:
    """Quote each term so FTS5 operators in user text are inert.

    The default join is the implicit AND; ``join="OR"`` widens a rewrite that
    carries terms the corpus does not contain.
    """

    return f" {join} ".join(
        '"' + term.replace('"', '""') + '"' for term in _fts_terms(query)
    )


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _document_dict(row: sqlite3.Row) -> dict[str, Any]:
    values = dict(row)
    return values


def _chunk_dict(row: sqlite3.Row) -> dict[str, Any]:
    values = dict(row)
    values["chunk_id"] = values["id"]
    values["section_title"] = values.get("section")
    values["block_ids"] = json.loads(values["block_ids"]) if values.get("block_ids") else []
    values["bbox_norm"] = json.loads(values["bbox_norm"]) if values.get("bbox_norm") else None
    values["oversize"] = bool(values.get("oversize"))
    return values


class KnowledgeStore:
    """Repository for the knowledge tables on top of :class:`Storage`."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    # -- folders -----------------------------------------------------------
    def create_folder(
        self, *, name: str, parent_id: str | None, created_at: str
    ) -> dict[str, Any]:
        folder_name = name.strip()
        if not folder_name:
            raise ValueError("folder name must not be empty")
        if parent_id is not None and self.get_folder(parent_id) is None:
            raise ValueError("parent folder not found")
        folder_id = uuid.uuid4().hex[:12]
        with self._storage.connect() as connection:
            position = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM kb_folders"
                " WHERE parent_id IS ?",
                (parent_id,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO kb_folders (id, name, parent_id, position, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (folder_id, folder_name, parent_id, position, created_at),
            )
        created = self.get_folder(folder_id)
        assert created is not None
        return created

    def get_folder(self, folder_id: str) -> dict[str, Any] | None:
        with self._storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM kb_folders WHERE id = ?", (folder_id,)
            ).fetchone()
        return _row(row)

    def list_folders(self) -> list[dict[str, Any]]:
        with self._storage.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM kb_folders ORDER BY parent_id IS NOT NULL,"
                " position, name"
            ).fetchall()
            counts = {
                row[0]: row[1]
                for row in connection.execute(
                    "SELECT folder_id, COUNT(*) FROM kb_documents"
                    " WHERE folder_id IS NOT NULL GROUP BY folder_id"
                )
            }
        folders = []
        for row in rows:
            values = dict(row)
            values["file_count"] = counts.get(values["id"], 0)
            folders.append(values)
        return folders

    def folder_descendants(self, folder_id: str) -> list[str]:
        with self._storage.connect() as connection:
            rows = connection.execute(
                "WITH RECURSIVE tree(id) AS ("
                "  SELECT id FROM kb_folders WHERE id = ?"
                "  UNION ALL"
                "  SELECT f.id FROM kb_folders f JOIN tree t ON f.parent_id = t.id"
                ") SELECT id FROM tree",
                (folder_id,),
            ).fetchall()
        return [row[0] for row in rows]

    def move_folder(
        self, folder_id: str, *, parent_id: str | None, name: str | None = None
    ) -> dict[str, Any]:
        folder = self.get_folder(folder_id)
        if folder is None:
            raise ValueError("folder not found")
        if parent_id is not None:
            if parent_id in self.folder_descendants(folder_id):
                raise ValueError("cannot move a folder under its own descendant")
            if self.get_folder(parent_id) is None:
                raise ValueError("parent folder not found")
        with self._storage.connect() as connection:
            if name is not None:
                connection.execute(
                    "UPDATE kb_folders SET name = ?, parent_id = ? WHERE id = ?",
                    (name.strip(), parent_id, folder_id),
                )
            else:
                connection.execute(
                    "UPDATE kb_folders SET parent_id = ? WHERE id = ?",
                    (parent_id, folder_id),
                )
        updated = self.get_folder(folder_id)
        assert updated is not None
        return updated

    def delete_folder(self, folder_id: str) -> int:
        ids = self.folder_descendants(folder_id)
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        with self._storage.connect() as connection:
            removed = connection.execute(
                f"SELECT COUNT(*) FROM kb_documents WHERE folder_id IN ({placeholders})",
                ids,
            ).fetchone()[0]
            connection.execute("DELETE FROM kb_folders WHERE id = ?", (folder_id,))
        return int(removed)

    # -- documents ---------------------------------------------------------
    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        with self._storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM kb_documents WHERE id = ?", (doc_id,)
            ).fetchone()
        return _document_dict(row) if row is not None else None

    def find_document_by_sha(self, pdf_sha256: str) -> dict[str, Any] | None:
        with self._storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM kb_documents WHERE pdf_sha256 = ?", (pdf_sha256,)
            ).fetchone()
        return _document_dict(row) if row is not None else None

    def list_documents(
        self,
        *,
        folder_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        where = "folder_id IS NULL" if folder_id is None else "folder_id = ?"
        parameters: tuple[Any, ...] = () if folder_id is None else (folder_id,)
        with self._storage.connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM kb_documents WHERE {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM kb_documents WHERE {where}"
                " ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
        return [_document_dict(row) for row in rows], int(total)

    def list_all_documents(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        with self._storage.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM kb_documents ORDER BY created_at DESC, id LIMIT ?",
                (limit,),
            ).fetchall()
        return [_document_dict(row) for row in rows]

    def list_documents_in_folders(
        self, folder_ids: Iterable[str]
    ) -> list[dict[str, Any]]:
        ids = list(folder_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._storage.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM kb_documents WHERE folder_id IN ({placeholders})",
                ids,
            ).fetchall()
        return [_document_dict(row) for row in rows]

    def upsert_document(
        self,
        document: Mapping[str, Any],
        chunks: Sequence[Mapping[str, Any]],
    ) -> None:
        """Insert or replace one document and all of its chunks."""

        status = document.get("status") or "ready"
        if status not in DOCUMENT_STATUSES:
            raise ValueError(f"unknown document status: {status!r}")
        values = {
            "id": document["id"],
            "folder_id": document.get("folder_id"),
            "title": document.get("title") or document["id"],
            "filename": document["filename"],
            "pdf_sha256": document["pdf_sha256"],
            "byte_size": document.get("byte_size"),
            "page_count": int(document.get("page_count") or 0),
            "chunk_count": len(chunks),
            "pdf_path": document["pdf_path"],
            "thumbnail_path": document.get("thumbnail_path"),
            "summary": document.get("summary"),
            "summary_model": document.get("summary_model"),
            "summary_created_at": document.get("summary_created_at"),
            "status": status,
            "status_detail": document.get("status_detail"),
            "indexed_at": document.get("indexed_at"),
            "created_at": document["created_at"],
            "updated_at": document.get("updated_at") or document["created_at"],
        }
        with self._storage.connect() as connection:
            connection.execute(
                "INSERT INTO kb_documents (id, folder_id, title, filename,"
                " pdf_sha256, byte_size, page_count, chunk_count, pdf_path,"
                " thumbnail_path, summary, summary_model, summary_created_at,"
                " status, status_detail, indexed_at, created_at, updated_at)"
                " VALUES (:id, :folder_id, :title, :filename, :pdf_sha256,"
                " :byte_size, :page_count, :chunk_count, :pdf_path,"
                " :thumbnail_path, :summary, :summary_model, :summary_created_at,"
                " :status, :status_detail, :indexed_at, :created_at, :updated_at)"
                " ON CONFLICT(id) DO UPDATE SET"
                " folder_id = excluded.folder_id, title = excluded.title,"
                " filename = excluded.filename, pdf_sha256 = excluded.pdf_sha256,"
                " byte_size = excluded.byte_size, page_count = excluded.page_count,"
                " chunk_count = excluded.chunk_count, pdf_path = excluded.pdf_path,"
                " thumbnail_path = excluded.thumbnail_path,"
                " summary = COALESCE(excluded.summary, kb_documents.summary),"
                " summary_model = COALESCE(excluded.summary_model,"
                " kb_documents.summary_model),"
                " summary_created_at = COALESCE(excluded.summary_created_at,"
                " kb_documents.summary_created_at),"
                " status = excluded.status,"
                " status_detail = excluded.status_detail,"
                " indexed_at = COALESCE(excluded.indexed_at,"
                " kb_documents.indexed_at),"
                " updated_at = excluded.updated_at",
                values,
            )
            connection.execute("DELETE FROM kb_chunks WHERE doc_id = ?", (values["id"],))
            for chunk in chunks:
                connection.execute(
                    "INSERT INTO kb_chunks (id, doc_id, page_no, chunk_index,"
                    " section, text, embed_text, block_ids, bbox_norm,"
                    " token_estimate, oversize, embedding, embedding_model,"
                    " chunker_version, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)",
                    (
                        chunk["chunk_id"],
                        values["id"],
                        int(chunk["page_no"]),
                        int(chunk["chunk_index"]),
                        chunk.get("section_title"),
                        chunk["text"],
                        chunk.get("embed_text") or chunk["text"],
                        json.dumps(chunk.get("block_ids") or []),
                        json.dumps(chunk["bbox_norm"])
                        if chunk.get("bbox_norm") is not None
                        else None,
                        chunk.get("token_estimate"),
                        1 if chunk.get("oversize") else 0,
                        chunk.get("chunker_version") or "vt-chunker/1",
                        values["created_at"],
                    ),
                )

    def set_document_folder(self, doc_id: str, folder_id: str | None) -> None:
        if folder_id is not None and self.get_folder(folder_id) is None:
            raise ValueError("folder not found")
        with self._storage.connect() as connection:
            connection.execute(
                "UPDATE kb_documents SET folder_id = ? WHERE id = ?",
                (folder_id, doc_id),
            )

    def set_document_summary(
        self,
        doc_id: str,
        *,
        summary: str,
        model: str | None,
        created_at: str,
        updated_at: str,
    ) -> None:
        with self._storage.connect() as connection:
            connection.execute(
                "UPDATE kb_documents SET summary = ?, summary_model = ?,"
                " summary_created_at = ?, updated_at = ? WHERE id = ?",
                (summary, model, created_at, updated_at, doc_id),
            )

    def set_document_status(
        self,
        doc_id: str,
        status: str,
        *,
        detail: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        if status not in DOCUMENT_STATUSES:
            raise ValueError(f"unknown document status: {status!r}")
        with self._storage.connect() as connection:
            connection.execute(
                "UPDATE kb_documents SET status = ?, status_detail = ?,"
                " updated_at = COALESCE(?, updated_at) WHERE id = ?",
                (status, detail, updated_at, doc_id),
            )

    def delete_document(self, doc_id: str) -> dict[str, Any] | None:
        document = self.get_document(doc_id)
        if document is None:
            return None
        with self._storage.connect() as connection:
            connection.execute("DELETE FROM kb_documents WHERE id = ?", (doc_id,))
        return document

    # -- chunks ------------------------------------------------------------
    def list_chunks(self, doc_id: str) -> list[dict[str, Any]]:
        with self._storage.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM kb_chunks WHERE doc_id = ?"
                " ORDER BY page_no, chunk_index",
                (doc_id,),
            ).fetchall()
        return [_chunk_dict(row) for row in rows]

    def get_chunks(self, chunk_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = list(chunk_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._storage.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM kb_chunks WHERE id IN ({placeholders})", ids
            ).fetchall()
        by_id = {row["id"]: _chunk_dict(row) for row in rows}
        return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]

    def search_chunks(
        self, query: str, *, limit: int = 20, doc_id: str | None = None
    ) -> list[dict[str, Any]]:
        terms = _fts_terms(query)
        if not terms:
            return []
        filters = " AND c.doc_id = ?" if doc_id is not None else ""
        with self._storage.connect() as connection:
            for join in (" ", " OR "):
                parameters: list[Any] = [_fts_query(query, join=join.strip() or " ")]
                if doc_id is not None:
                    parameters.append(doc_id)
                parameters.append(limit)
                rows = connection.execute(
                    "SELECT c.*, bm25(kb_chunks_fts) AS score"
                    " FROM kb_chunks_fts"
                    " JOIN kb_chunks c ON c.rowid = kb_chunks_fts.rowid"
                    f" WHERE kb_chunks_fts MATCH ?{filters}"
                    " ORDER BY score, c.id LIMIT ?",
                    parameters,
                ).fetchall()
                if rows:
                    break
        return [_chunk_dict(row) | {"score": row["score"]} for row in rows]

    def set_embeddings(
        self,
        doc_id: str,
        vectors: Mapping[str, bytes],
        *,
        model: str,
        built_at: str,
    ) -> None:
        with self._storage.connect() as connection:
            for chunk_id, vector in vectors.items():
                connection.execute(
                    "UPDATE kb_chunks SET embedding = ?, embedding_model = ?"
                    " WHERE id = ? AND doc_id = ?",
                    (sqlite3.Binary(vector), model, chunk_id, doc_id),
                )
            self._refresh_index_state(connection, built_at=built_at)

    @staticmethod
    def _refresh_index_state(
        connection: sqlite3.Connection, *, built_at: str
    ) -> None:
        row = connection.execute(
            "SELECT COUNT(*), MIN(LENGTH(embedding)), MAX(LENGTH(embedding)),"
            " MAX(embedding_model), MAX(chunker_version)"
            " FROM kb_chunks WHERE embedding IS NOT NULL"
        ).fetchone()
        count, shortest, longest, model, chunker_version = row
        dimension = None
        if shortest is not None and shortest == longest:
            dimension = int(shortest) // 4
        connection.execute(
            "UPDATE kb_index_state SET chunks = ?, dimension = ?, model = ?,"
            " chunker_version = ?, built_at = ? WHERE id = 'current'",
            (int(count), dimension, model, chunker_version, built_at),
        )

    def index_state(self) -> dict[str, Any]:
        with self._storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM kb_index_state WHERE id = 'current'"
            ).fetchone()
        assert row is not None
        return dict(row)

    # -- vectors -----------------------------------------------------------
    def stored_vectors(self) -> tuple[list[str], list[bytes]]:
        """Return embedded chunk ids and their raw ``float32`` blobs."""

        with self._storage.connect() as connection:
            rows = connection.execute(
                "SELECT id, embedding FROM kb_chunks"
                " WHERE embedding IS NOT NULL ORDER BY rowid"
            ).fetchall()
        return [row[0] for row in rows], [bytes(row[1]) for row in rows]
