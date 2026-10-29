"""File-backed cache for external model responses.

Cache keys are content addressed: a namespace plus a canonical JSON key hashed
with SHA-256. Values are JSON. The cache is optional, so read and write errors
degrade to a miss instead of failing the request. Writes are atomic.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

CACHE_SCHEMA_VERSION = 1


class ResponseCache:
    def __init__(self, root: str | Path, *, enabled: bool = True) -> None:
        self.root = Path(root)
        self.enabled = enabled

    def _path(self, namespace: str, key: Mapping[str, Any]) -> Path | None:
        try:
            raw = json.dumps(
                {"schema": CACHE_SCHEMA_VERSION, "key": key},
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            return None
        digest = hashlib.sha256(raw).hexdigest()
        return self.root / namespace / f"{digest}.json"

    def get(self, namespace: str, key: Mapping[str, Any]) -> Any | None:
        if not self.enabled:
            return None
        path = self._path(namespace, key)
        if path is None:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def set(self, namespace: str, key: Mapping[str, Any], payload: Any) -> None:
        if not self.enabled:
            return
        path = self._path(namespace, key)
        if path is None:
            return
        try:
            data = json.dumps(payload, ensure_ascii=False)
        except (TypeError, ValueError):
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(
                dir=path.parent, prefix=f"{path.name}-", suffix=".tmp"
            )
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as stream:
                    stream.write(data)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        except OSError:
            return
