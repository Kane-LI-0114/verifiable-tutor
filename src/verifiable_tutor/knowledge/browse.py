"""Browsing, organizing, and searching the local course archive.

The browser sits on :class:`~verifiable_tutor.corpus.store.KnowledgeStore` and
shapes the rows the knowledge-base page renders: the folder tree, one folder's
files, file details, and a lexical search over file names, folder names, page
text, and the Qwen summary. Search returns the reason a document matched and
the highlight ranges it found, so the page never has to re-match the query.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..corpus.store import KnowledgeStore
from ..settings import AppSettings
from ..storage import iso

#: Characters of context kept around a content hit in a search snippet.
SNIPPET_WINDOW = 120
#: Content matches reported per document.
MAX_CONTENT_MATCHES_PER_DOCUMENT = 3

_KIND_PRIORITY = {"filename": 3, "folder": 2, "summary": 1, "content": 1}
_DOC_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_SEARCH_FIELDS = {
    "filename": "filename",
    "folder": "folder path",
    "summary": "summary",
}


def terms_of(query: str) -> list[str]:
    """Split a query into the terms the page marks, keeping CJK runs whole."""

    return [term for term in re.split(r"\s+", (query or "").strip()) if term]


def highlight_ranges(text: str, terms: Iterable[str]) -> list[list[int]]:
    """Return sorted ``[start, end)`` ranges of every term occurrence in ``text``."""

    ranges: list[list[int]] = []
    for term in terms:
        if not term:
            continue
        for match in re.finditer(re.escape(term), text, re.IGNORECASE):
            if match.end() > match.start():
                ranges.append([match.start(), match.end()])
    return sorted(ranges, key=lambda item: (item[0], item[1]))


def snippet(text: str, terms: Iterable[str]) -> str:
    """Take the text, or a window of it around the first match."""

    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= 2 * SNIPPET_WINDOW:
        return clean
    first = None
    for term in terms:
        match = re.search(re.escape(term), clean, re.IGNORECASE)
        if match is not None and (first is None or match.start() < first):
            first = match.start()
    if first is None:
        return clean[: 2 * SNIPPET_WINDOW]
    start = max(0, first - SNIPPET_WINDOW)
    end = min(len(clean), first + SNIPPET_WINDOW)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean) else ""
    return f"{prefix}{clean[start:end]}{suffix}"


class KnowledgeBrowser:
    """The knowledge-base page's read and organize service."""

    def __init__(
        self,
        *,
        store: KnowledgeStore,
        settings: AppSettings,
        clock: Any,
    ) -> None:
        self._store = store
        self._settings = settings
        self._clock = clock

    # -- folders -----------------------------------------------------------
    def folder_tree(self) -> dict[str, Any]:
        folders = self._store.list_folders()
        by_id = {folder["id"]: folder for folder in folders}

        def path_of(folder: Mapping[str, Any]) -> list[dict[str, str]]:
            path: list[dict[str, str]] = []
            current: Mapping[str, Any] | None = folder
            seen: set[str] = set()
            while current is not None and current["id"] not in seen:
                seen.add(current["id"])
                path.append({"id": current["id"], "name": current["name"]})
                parent_id = current.get("parent_id")
                current = by_id.get(parent_id) if parent_id else None
            return list(reversed(path))

        items = [{**folder, "path": path_of(folder)} for folder in folders]
        documents, total = self._store.list_documents(limit=1)
        return {"folders": items, "total_files": total}

    def create_folder(self, *, name: str, parent_id: str | None) -> dict[str, Any]:
        created = self._store.create_folder(
            name=name,
            parent_id=parent_id,
            created_at=self._stamp(),
        )
        return self._folder_public(created["id"])

    def update_folder(
        self,
        folder_id: str,
        *,
        name: str | None,
        parent_id: str | None,
        parent_given: bool,
    ) -> dict[str, Any]:
        folder = self._store.get_folder(folder_id)
        if folder is None:
            raise _Missing("folder not found")
        resolved_parent = parent_id if parent_given else folder["parent_id"]
        self._store.move_folder(folder_id, parent_id=resolved_parent, name=name)
        return self._folder_public(folder_id)

    def _folder_public(self, folder_id: str) -> dict[str, Any]:
        for folder in self.folder_tree()["folders"]:
            if folder["id"] == folder_id:
                return folder
        raise _Missing("folder not found")

    def delete_folder(self, folder_id: str) -> dict[str, int]:
        if self._store.get_folder(folder_id) is None:
            raise _Missing("folder not found")
        documents = self._documents_under(folder_id)
        removed = self._store.delete_folder(folder_id)
        for document in documents:
            self._unlink_document(document)
        return {"deleted_documents": removed}

    def _documents_under(self, folder_id: str) -> list[dict[str, Any]]:
        return self._store.list_documents_in_folders(
            self._store.folder_descendants(folder_id)
        )

    # -- documents ---------------------------------------------------------
    def list_documents(
        self, *, folder_id: str | None, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        documents, total = self._store.list_documents(
            folder_id=folder_id, limit=limit, offset=offset
        )
        return [self._public(document) for document in documents], total

    def document(self, doc_id: str) -> dict[str, Any]:
        document = self._store.get_document(doc_id)
        if document is None:
            raise _Missing("document not found")
        return self._public(document)

    def move_document(self, doc_id: str, *, folder_id: str | None) -> dict[str, Any]:
        if self._store.get_document(doc_id) is None:
            raise _Missing("document not found")
        try:
            self._store.set_document_folder(doc_id, folder_id)
        except ValueError as exc:
            raise _Invalid(str(exc)) from exc
        return self.document(doc_id)

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        document = self._store.delete_document(doc_id)
        if document is None:
            raise _Missing("document not found")
        self._unlink_document(document)
        return self._public(document)

    def pdf_path(self, doc_id: str) -> Path:
        if not _DOC_ID.fullmatch(doc_id):
            raise _Invalid("invalid document id")
        document = self._store.get_document(doc_id)
        if document is None:
            raise _Missing("document not found")
        path = Path(document["pdf_path"]).resolve()
        if not path.is_file():
            raise _Missing("document file not found")
        return path

    # -- search ------------------------------------------------------------
    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        terms = terms_of(query)
        if not terms:
            return {"query": query, "documents": []}
        folders = {folder["id"]: folder for folder in self._store.list_folders()}
        documents = self._store.list_all_documents()
        content: dict[str, list[dict[str, Any]]] = {}
        for hit in self._store.search_chunks(query, limit=limit * 4):
            content.setdefault(hit["doc_id"], []).append(
                {
                    "kind": "content",
                    "page_no": hit["page_no"],
                    "snippet": snippet(hit["text"], terms),
                    "highlights": highlight_ranges(snippet(hit["text"], terms), terms),
                }
            )

        results: list[dict[str, Any]] = []
        for document in documents:
            matches: list[dict[str, Any]] = []
            for kind, value in (
                ("filename", document["filename"]),
                ("folder", self._folder_path_text(document, folders)),
                ("summary", document.get("summary") or ""),
            ):
                if value and any(
                    term.casefold() in value.casefold() for term in terms
                ):
                    text = snippet(value, terms)
                    matches.append(
                        {
                            "kind": kind,
                            "page_no": None,
                            "snippet": text,
                            "highlights": highlight_ranges(text, terms),
                        }
                    )
            matches.extend(content.get(document["id"], [])[:MAX_CONTENT_MATCHES_PER_DOCUMENT])
            if not matches:
                continue
            best = max(_KIND_PRIORITY[match["kind"]] for match in matches)
            results.append(
                {
                    **self._public(document),
                    "matches": sorted(
                        matches,
                        key=lambda match: (
                            -_KIND_PRIORITY[match["kind"]],
                            match["page_no"] or 0,
                        ),
                    ),
                    "_rank": best,
                }
            )
        results.sort(key=lambda item: (-item["_rank"], item["title"]))
        for item in results:
            item.pop("_rank", None)
        return {"query": query, "documents": results}

    @staticmethod
    def _folder_path_text(
        document: Mapping[str, Any], folders: Mapping[str, Mapping[str, Any]]
    ) -> str:
        names: list[str] = []
        folder_id = document.get("folder_id")
        seen: set[str] = set()
        while folder_id and folder_id in folders and folder_id not in seen:
            seen.add(folder_id)
            folder = folders[folder_id]
            names.append(folder["name"])
            folder_id = folder.get("parent_id")
        return " / ".join(reversed(names))

    # -- helpers -----------------------------------------------------------
    def _public(self, document: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": document["id"],
            "title": document["title"],
            "filename": document["filename"],
            "folder_id": document.get("folder_id"),
            "page_count": document.get("page_count") or 0,
            "chunk_count": document.get("chunk_count") or 0,
            "byte_size": document.get("byte_size"),
            "status": document["status"],
            "status_detail": document.get("status_detail"),
            "summary": document.get("summary"),
            "summary_model": document.get("summary_model"),
            "created_at": document["created_at"],
            "indexed_at": document.get("indexed_at"),
            "pdf_url": f"/api/knowledge/documents/{document['id']}/file",
            "thumbnail_url": f"/api/corpus/{document['id']}/pages/1.webp",
        }

    def _unlink_document(self, document: Mapping[str, Any]) -> None:
        candidates: list[Path] = []
        for key in ("pdf_path", "thumbnail_path"):
            value = document.get(key)
            if value:
                candidates.append(Path(value))
        images = self._settings.corpus_images_dir / f"{document['id']}.p*.webp"
        try:
            candidates.extend(images.parent.glob(images.name))
        except OSError:
            pass
        for path in candidates:
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                continue

    def _stamp(self) -> str:
        moment = self._clock()
        return iso(moment) if isinstance(moment, datetime) else str(moment)


class _Missing(Exception):
    """The requested row does not exist."""


class _Invalid(Exception):
    """The request is valid HTTP but breaks a domain rule."""
