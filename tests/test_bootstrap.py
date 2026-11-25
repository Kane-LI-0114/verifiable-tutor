"""First-run bootstrap loads the tracked revision snapshot without a model call."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from verifiable_tutor.bootstrap import bootstrap_content
from verifiable_tutor.storage import Storage


def _storage(tmp_path) -> Storage:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    with storage.connect() as connection:
        connection.execute(
            "INSERT INTO kb_documents"
            " (id, title, filename, pdf_sha256, page_count, pdf_path, status,"
            "  created_at, updated_at, summary)"
            " VALUES ('Tutorial_4', 'Tutorial 4', 'Tutorial_4.pdf', 'sha', 5,"
            " 'data/Tutorial_4.pdf', 'ready', ?, ?, 'Summary')",
            (
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return storage


def _snapshot() -> dict:
    return {
        "schema": "vt-revision/1",
        "themes": [
            {
                "id": "t1",
                "title": "Attention",
                "summary": "Tiling and softmax.",
                "position": 0,
                "created_at": "2026-11-25T09:00:00+00:00",
                "model": "deepseek-flash",
                "prompt_version": "revision-outline/2",
            }
        ],
        "documents": [
            {
                "doc_id": "Tutorial_4",
                "theme_id": "t1",
                "category": "tutorial",
                "markdown": "# Tutorial 4\n\n## A point\n\nBody.\n",
                "intro_markdown": "# Tutorial 4",
                "model": "deepseek-flash",
                "prompt_version": "revision-document/2",
                "generated_at": "2026-11-25T09:00:00+00:00",
                "title": "Tutorial 4",
                "filename": "Tutorial_4.pdf",
                "points": [
                    {
                        "title": "A point",
                        "body_markdown": "Body.",
                        "position": 0,
                        "page_no": 3,
                    }
                ],
            }
        ],
    }


def test_bootstrap_imports_the_revision_snapshot(tmp_path):
    storage = _storage(tmp_path)
    snapshot = tmp_path / "data" / "revision" / "guide.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(json.dumps(_snapshot()), encoding="utf-8")

    bootstrap_content(storage, tmp_path, storage.path)

    themes = storage.list_revision_tree("nobody@ust.hk")
    assert [theme["title"] for theme in themes] == ["Attention"]
    detail = storage.revision_document_detail("Tutorial_4", "nobody@ust.hk")
    assert detail is not None
    assert detail["total"] == 1


def test_bootstrap_is_a_no_op_without_a_snapshot(tmp_path):
    storage = _storage(tmp_path)

    bootstrap_content(storage, tmp_path, storage.path)

    assert storage.list_revision_tree("nobody@ust.hk") == []
