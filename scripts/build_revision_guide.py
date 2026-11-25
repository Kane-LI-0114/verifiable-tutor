#!/usr/bin/env python3
"""Build the revision guide outline and its per-document review chapters.

Usage:
    python scripts/build_revision_guide.py status
    python scripts/build_revision_guide.py outline [--dry-run]
    python scripts/build_revision_guide.py docs --doc <id> [--doc <id>] [--dry-run]

The outline groups every summarised document into one theme. The docs command
writes the review chapter for one or more documents from their OCR chunks. Both
are offline steps: the model is called once per build and the app only reads
the stored result.
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
from verifiable_tutor.revision.document import DocumentError  # noqa: E402
from verifiable_tutor.revision.generate import (  # noqa: E402
    PROMPT_VERSION as DOCUMENT_PROMPT_VERSION,
    build_document,
)
from verifiable_tutor.revision.outline import (  # noqa: E402
    PROMPT_VERSION as OUTLINE_PROMPT_VERSION,
    OutlineError,
    build_outline,
)
from verifiable_tutor.settings import load_settings  # noqa: E402
from verifiable_tutor.storage import Storage  # noqa: E402


def _model() -> tuple[ModelAdapter, str]:
    resolved = load_model_config(
        ROOT / "config" / "models.yaml",
        env_file=ROOT / ".env",
        base_dir=ROOT,
    )
    role = resolved.config.roles["chat"]
    model_id = resolved.config.providers[role.provider].models[role.model]
    return ModelAdapter(resolved), model_id


def _status(storage: Storage) -> int:
    status = storage.revision_outline_status()
    print(
        f"themes={len(status['themes'])} documents={status['documents']}"
        f" generated={status['generated']} points={status['points']}"
    )
    for theme in status["themes"]:
        print(f"- {theme['title']}: {theme['documents']} documents")
    return 0


def _outline(storage: Storage, *, dry_run: bool) -> int:
    candidates = storage.list_revision_candidates()
    if not candidates:
        print(
            "no summarised documents; import the corpus first",
            file=sys.stderr,
        )
        return 1
    adapter, model_id = _model()
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
        prompt_version=OUTLINE_PROMPT_VERSION,
    )
    print(f"wrote {len(themes)} themes and {len(documents)} document mappings")
    return 0


def _documents(storage: Storage, doc_ids: list[str], *, dry_run: bool) -> int:
    adapter: ModelAdapter | None = None
    model_id = ""
    for doc_id in doc_ids:
        document = storage.find_revision_document(doc_id)
        if document is None:
            print(f"unknown document: {doc_id}", file=sys.stderr)
            return 1
        chunks = storage.list_revision_chunks(doc_id)
        if not chunks:
            print(f"no OCR chunks for {doc_id}", file=sys.stderr)
            return 1
        title = document.get("title") or doc_id
        filename = document.get("filename") or doc_id
        if dry_run:
            pages = sorted({chunk["page_no"] for chunk in chunks})
            print(
                f"{doc_id}: {len(chunks)} chunks, pages {pages[0]} to {pages[-1]}"
            )
            continue
        if adapter is None:
            adapter, model_id = _model()
        try:
            generated = build_document(
                title=title,
                filename=filename,
                chunks=chunks,
                adapter=adapter,
                overview=document.get("summary"),
            )
        except DocumentError as exc:
            print(f"{doc_id}: rejected: {exc}", file=sys.stderr)
            return 1
        count = storage.save_revision_document(
            doc_id=doc_id,
            markdown=generated.markdown,
            intro_markdown=generated.intro_markdown,
            points=[
                {
                    "title": point.title,
                    "body_markdown": point.body_markdown,
                    "page_no": point.page_no,
                }
                for point in generated.points
            ],
            model=model_id,
            prompt_version=DOCUMENT_PROMPT_VERSION,
            generated_at=datetime.now(timezone.utc),
        )
        print(
            f"{doc_id}: {count} knowledge points in"
            f" {generated.batches} model calls"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show the stored outline")
    outline = sub.add_parser("outline", help="generate and store the outline")
    outline.add_argument(
        "--dry-run", action="store_true", help="print the outline, store nothing"
    )
    documents = sub.add_parser("docs", help="generate review chapters")
    documents.add_argument(
        "--doc", action="append", required=True, help="document id; repeatable"
    )
    documents.add_argument(
        "--dry-run", action="store_true", help="list the chunks, call no model"
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    storage = Storage(settings.database_path)
    storage.initialize()
    if args.command == "status":
        return _status(storage)
    if args.command == "outline":
        return _outline(storage, dry_run=args.dry_run)
    return _documents(storage, args.doc, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
