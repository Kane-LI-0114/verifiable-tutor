"""Knowledge-base cards and build orchestration (FR-K1 to FR-K4, partially).

Cards are read from the validated JSONL files the local driver stores after a
Qwen build job. A build submission reuses the existing TACC driver through a
subprocess runner seam; tests replace the runner so no TACC job is submitted.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from ..settings import AppSettings
from ..storage import Storage

_MAX_ERROR_CHARS = 2000


class KnowledgeBuildError(Exception):
    """A client-visible build failure."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class BuildRunnerError(RuntimeError):
    """Raised by the subprocess runner when the driver fails."""


class BuildRunner(Protocol):
    def run(
        self, build_id: str, *, doc_id: str | None, max_chunks: int
    ) -> dict[str, Any]: ...


class DriverBuildRunner:
    """Run the existing local knowledge-base driver in a subprocess."""

    def __init__(self, *, settings: AppSettings) -> None:
        self._settings = settings

    def run(
        self, build_id: str, *, doc_id: str | None, max_chunks: int
    ) -> dict[str, Any]:
        pages = self._settings.knowledge_pages_path
        if pages is None:
            raise BuildRunnerError("knowledge.pages_path is not configured")
        command = [
            sys.executable,
            str(self._settings.knowledge_driver),
            "--pages",
            str(pages),
            "--max-chunks",
            str(max_chunks),
            "--build-id",
            build_id,
        ]
        if doc_id:
            command.extend(["--doc-id", doc_id])
        try:
            result = subprocess.run(
                command,
                cwd=self._settings.repo_root,
                capture_output=True,
                text=True,
                timeout=self._settings.knowledge_build_timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise BuildRunnerError("knowledge-base driver timed out") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise BuildRunnerError(
                f"knowledge-base driver failed: {detail[-_MAX_ERROR_CHARS:]}"
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise BuildRunnerError(
                "knowledge-base driver did not print a JSON result"
            ) from exc
        validation = payload.get("validation") or {}
        return {
            "job_id": str(payload.get("job_id") or ""),
            "records_path": payload.get("records_path"),
            "records_count": int(validation.get("records_valid") or 0),
        }


class CardStore:
    """Read validated knowledge records from the local JSONL mirror."""

    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)

    def _load(self) -> list[dict[str, Any]]:
        if not self._directory.is_dir():
            return []
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for path in sorted(self._directory.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                card = self._public(record)
                if card is None:
                    continue
                key = (card["doc_id"], card["chunk_id"])
                previous = latest.get(key)
                if previous is None or str(card["created_at"]) >= str(
                    previous["created_at"]
                ):
                    latest[key] = card
        return sorted(
            latest.values(),
            key=lambda card: (card["doc_id"], card["page_no"], card["chunk_id"]),
        )

    @staticmethod
    def _public(record: Any) -> dict[str, Any] | None:
        if not isinstance(record, dict):
            return None
        chunk_id = record.get("chunk_id")
        doc_id = record.get("doc_id")
        page_no = record.get("page_no")
        summary = record.get("summary")
        if (
            not isinstance(chunk_id, str)
            or not isinstance(doc_id, str)
            or not isinstance(page_no, int)
            or isinstance(page_no, bool)
            or not isinstance(summary, str)
        ):
            return None
        key_terms = record.get("key_terms")
        study_questions = record.get("study_questions")
        citations = record.get("citations")
        return {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "page_no": page_no,
            "section": record.get("section"),
            "summary": summary,
            "key_terms": key_terms if isinstance(key_terms, list) else [],
            "study_questions": (
                study_questions if isinstance(study_questions, list) else []
            ),
            "citations": citations if isinstance(citations, list) else [],
            "model": record.get("model"),
            "prompt_version": record.get("prompt_version"),
            "build_id": record.get("build_id"),
            "created_at": record.get("created_at"),
        }

    def search(
        self,
        *,
        doc_id: str | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Filter, sort, and paginate the cards; returns the page and total."""

        cards = self._load()
        if doc_id is not None:
            cards = [card for card in cards if card["doc_id"] == doc_id]
        if q:
            needle = q.casefold()

            def matches(card: dict[str, Any]) -> bool:
                haystack = [card["summary"], *card["key_terms"], *card["study_questions"]]
                return any(needle in str(value).casefold() for value in haystack)

            cards = [card for card in cards if matches(card)]
        total = len(cards)
        return cards[offset : offset + limit], total


class KnowledgeBuildService:
    """Queue, run, and report one knowledge-base build."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        storage: Storage,
        runner: BuildRunner,
        clock: Callable[[], datetime],
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._runner = runner
        self._clock = clock

    # -- submission --------------------------------------------------------
    def submit(
        self,
        user: dict[str, Any],
        *,
        doc_id: str | None,
        max_chunks: int | None,
        background: Any,
    ) -> dict[str, Any]:
        pages = self._settings.knowledge_pages_path
        if pages is None:
            raise KnowledgeBuildError(
                503,
                "knowledge-base build is not configured: set "
                "knowledge.pages_path in config/app.yaml",
            )
        if not Path(pages).is_file():
            raise KnowledgeBuildError(
                503, f"knowledge-base pages file does not exist: {pages}"
            )
        configured_max = self._settings.knowledge_max_chunks
        resolved_max = configured_max if max_chunks is None else max_chunks
        if resolved_max < 1 or resolved_max > configured_max:
            raise KnowledgeBuildError(
                400, f"max_chunks must be between 1 and {configured_max}"
            )
        if self._storage.active_build() is not None:
            raise KnowledgeBuildError(
                409, "a knowledge-base build is already running"
            )
        now = self._clock()
        build_id = f"kb-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self._storage.create_build(
            build_id=build_id,
            user_id=user["id"],
            request_json=json.dumps(
                {"doc_id": doc_id, "max_chunks": resolved_max},
                ensure_ascii=False,
            ),
            created_at=now,
        )
        background.add_task(self.execute, build_id, doc_id, resolved_max)
        return {"build_id": build_id, "state": "queued"}

    # -- execution ---------------------------------------------------------
    def execute(self, build_id: str, doc_id: str | None, max_chunks: int) -> None:
        self._storage.update_build(
            build_id, state="running", updated_at=self._clock()
        )
        try:
            result = self._runner.run(
                build_id, doc_id=doc_id, max_chunks=max_chunks
            )
        except Exception as exc:  # the runner boundary owns its failures
            self._storage.update_build(
                build_id,
                state="failed",
                updated_at=self._clock(),
                error=str(exc)[-_MAX_ERROR_CHARS:],
            )
            return
        self._storage.update_build(
            build_id,
            state="ready",
            updated_at=self._clock(),
            job_id=result.get("job_id") or None,
            records_path=result.get("records_path"),
            records_count=result.get("records_count"),
        )

    # -- reads -------------------------------------------------------------
    def get(self, build_id: str) -> dict[str, Any]:
        row = self._storage.find_build(build_id)
        if row is None:
            raise KnowledgeBuildError(404, "build not found")
        return self._public(row)

    def list(self) -> list[dict[str, Any]]:
        return [self._public(row) for row in self._storage.list_builds()]

    @staticmethod
    def _public(row: dict[str, Any]) -> dict[str, Any]:
        try:
            request = json.loads(row.get("request_json") or "{}")
        except json.JSONDecodeError:
            request = {}
        return {
            "id": row["id"],
            "state": row["state"],
            "job_id": row["job_id"],
            "records_path": row["records_path"],
            "records_count": row["records_count"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "request": request,
        }
