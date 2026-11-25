#!/usr/bin/env python3
"""Build the revision guide outline from the stored document summaries.

Usage:
    python scripts/build_revision_guide.py status
    python scripts/build_revision_guide.py outline
    python scripts/build_revision_guide.py outline --dry-run

The outline groups every summarised document into one revision theme. It is an
offline step: the model is called once, the result is stored in SQLite, and the
app only reads it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from verifiable_tutor.llm.adapter import ModelAdapter  # noqa: E402
from verifiable_tutor.llm.config import load_model_config  # noqa: E402
from verifiable_tutor.revision.category import document_category  # noqa: E402
from verifiable_tutor.revision.outline import (  # noqa: E402
    PROMPT_VERSION,
    OutlineError,
    build_outline,
)
from verifiable_tutor.settings import load_settings  # noqa: E402
from verifiable_tutor.storage import Storage  # noqa: E402


def _status(storage: Storage) -> int:
    themes = storage.list_revision_tree()
    documents = sum(len(theme["documents"]) for theme in themes)
    print(f"themes={len(themes)} documents={documents}")
    for theme in themes:
        print(f"- {theme['title']}: {len(theme['documents'])} documents")
    return 0


def _outline(storage: Storage, *, dry_run: bool) -> int:
    candidates = storage.list_revision_candidates()
    if not candidates:
        print(
            "no summarised documents; import the corpus first",
            file=sys.stderr,
        )
        return 1
    resolved = load_model_config(
        ROOT / "config" / "models.yaml",
        env_file=ROOT / ".env",
        base_dir=ROOT,
    )
    adapter = ModelAdapter(resolved)
    try:
        themes = build_outline(candidates, adapter)
    except OutlineError as exc:
        print(f"outline rejected: {exc}", file=sys.stderr)
        return 1

    by_id = {document["doc_id"]: document for document in candidates}
    documents = [
        {
            "doc_id": doc_id,
            "theme_id": theme.id,
            "category": document_category(
                by_id[doc_id].get("filename") or doc_id
            ),
        }
        for theme in themes
        for doc_id in theme.doc_ids
    ]
    if dry_run:
        print(
            json.dumps(
                {
                    "themes": [
                        {
                            "id": theme.id,
                            "title": theme.title,
                            "summary": theme.summary,
                            "position": theme.position,
                            "doc_ids": list(theme.doc_ids),
                        }
                        for theme in themes
                    ]
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    role = resolved.config.roles["chat"]
    model_id = resolved.config.providers[role.provider].models[role.model]
    storage.replace_revision_outline(
        themes=[
            {
                "id": theme.id,
                "title": theme.title,
                "summary": theme.summary,
                "position": theme.position,
            }
            for theme in themes
        ],
        documents=documents,
        created_at=datetime.now(timezone.utc),
        model=model_id,
        prompt_version=PROMPT_VERSION,
    )
    print(f"wrote {len(themes)} themes and {len(documents)} document mappings")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show the stored outline")
    outline = sub.add_parser("outline", help="generate and store the outline")
    outline.add_argument(
        "--dry-run", action="store_true", help="print the outline, store nothing"
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    storage = Storage(settings.database_path)
    storage.initialize()
    if args.command == "status":
        return _status(storage)
    return _outline(storage, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
