"""Group the summarised documents into revision themes (the outline).

One DeepSeek call reads every document summary and returns six to eight
themes. The model is not trusted to follow the constraint, so the parser
checks that every document appears exactly once before anything is stored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..prompts import load_prompt
from .category import document_category

__all__ = ["OutlineError", "RevisionTheme", "build_outline"]

PROMPT_VERSION = "revision-outline/2"
PROMPT = load_prompt("revision_outline")


class OutlineError(ValueError):
    """The model output cannot be used as a revision outline."""


@dataclass(frozen=True)
class RevisionTheme:
    id: str
    title: str
    summary: str
    position: int
    doc_ids: tuple[str, ...]


def _json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[: -3]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise OutlineError("the outline is not a JSON object")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise OutlineError(f"the outline is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise OutlineError("the outline is not a JSON object")
    return data


def build_outline(
    documents: Sequence[Mapping[str, Any]], adapter: Any
) -> list[RevisionTheme]:
    """Ask the model for themes and validate the document mapping."""

    if not documents:
        raise OutlineError("there are no summarised documents to group")
    payload = [
        {
            "doc_id": document["doc_id"],
            "title": document.get("title"),
            "category": document_category(
                document.get("filename") or document["doc_id"]
            ),
            "summary": document["summary"],
        }
        for document in documents
    ]
    known = {item["doc_id"] for item in payload}
    prompt = PROMPT.replace(
        "%%DOCUMENTS%%", json.dumps(payload, ensure_ascii=False, indent=2)
    )
    result = adapter.chat([{"role": "user", "content": prompt}], role="chat")
    data = _json_object(getattr(result, "text", "") or "")
    raw_themes = data.get("themes")
    if not isinstance(raw_themes, list) or not raw_themes:
        raise OutlineError("the outline has no themes")

    themes: list[RevisionTheme] = []
    seen: list[str] = []
    for index, raw in enumerate(raw_themes, start=1):
        if not isinstance(raw, dict):
            raise OutlineError("a theme is not a JSON object")
        title = str(raw.get("title") or "").strip()
        summary = str(raw.get("summary") or "").strip()
        doc_ids = raw.get("doc_ids")
        if not title or not summary:
            raise OutlineError("a theme is missing its title or summary")
        if not isinstance(doc_ids, list) or not doc_ids:
            raise OutlineError(f"theme {title!r} lists no documents")
        normalised = [str(doc_id) for doc_id in doc_ids]
        unknown = [doc_id for doc_id in normalised if doc_id not in known]
        if unknown:
            raise OutlineError(
                f"theme {title!r} names unknown documents: {', '.join(unknown)}"
            )
        seen.extend(normalised)
        themes.append(
            RevisionTheme(
                id=f"t{index}",
                title=title,
                summary=summary,
                position=index - 1,
                doc_ids=tuple(normalised),
            )
        )

    duplicates = sorted({doc_id for doc_id in seen if seen.count(doc_id) > 1})
    if duplicates:
        raise OutlineError(
            "documents appear in more than one theme: " + ", ".join(duplicates)
        )
    missing = sorted(known - set(seen))
    if missing:
        raise OutlineError(
            "documents are missing from the outline: " + ", ".join(missing)
        )
    return themes
