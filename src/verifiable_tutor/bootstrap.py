"""First-run bootstrap from the tracked corpus and revision snapshots.

A fresh checkout has no runtime database. Copying the corpus through the
existing import driver and loading the revision snapshot makes the demo usable
without a TACC job or a paid model call. Both steps are skipped when the
database already has rows, so they run once.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .storage import Storage

__all__ = ["bootstrap_content"]

logger = logging.getLogger(__name__)


def _corpus_rows(storage: Storage) -> int:
    return int(storage.scalar("SELECT COUNT(*) FROM kb_documents") or 0)


def _theme_rows(storage: Storage) -> int:
    return int(storage.scalar("SELECT COUNT(*) FROM revision_themes") or 0)


def bootstrap_content(
    storage: Storage, repo_root: Path, database_path: Path
) -> None:
    """Load the tracked corpus and revision guide when the database is empty."""

    if _corpus_rows(storage) == 0:
        script = Path(repo_root) / "scripts" / "ingest_corpus.py"
        state = Path(repo_root) / "data" / "index" / "ingest.json"
        if script.is_file() and state.is_file():
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "import",
                        "--db",
                        str(database_path),
                    ],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode != 0:
                    logger.warning(
                        "corpus bootstrap failed: %s",
                        (result.stderr or result.stdout).strip()[-500:],
                    )
            except Exception:
                logger.exception("corpus bootstrap failed")

    if _theme_rows(storage) == 0:
        snapshot = Path(repo_root) / "data" / "revision" / "guide.json"
        if snapshot.is_file():
            try:
                payload = json.loads(snapshot.read_text(encoding="utf-8"))
                storage.import_revision_snapshot(
                    payload, imported_at=datetime.now(timezone.utc)
                )
            except Exception:
                logger.exception("revision bootstrap failed")
