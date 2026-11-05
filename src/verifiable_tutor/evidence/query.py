"""Turn a student question into the queries the two retrieval arms run.

The model writes one English keyword query (so BM25 reaches English course text
from a Chinese question) and may decline retrieval for a message that carries no
course content. Any failure falls back to the raw question, so retrieval never
depends on a model call succeeding.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ..prompts import load_prompt

PROMPT_NAME = "search_query"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass(frozen=True)
class QueryPlan:
    question: str
    keyword_query: str
    semantic_queries: tuple[str, ...]
    need_retrieval: bool


def fallback_plan(question: str) -> QueryPlan:
    """Use the raw question for both arms."""

    text = (question or "").strip()
    return QueryPlan(
        question=text,
        keyword_query=text,
        semantic_queries=(text,) if text else (),
        need_retrieval=bool(text),
    )


def _parse(text: str) -> dict[str, Any] | None:
    cleaned = _FENCE.sub("", (text or "").strip()).strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def plan_query(model: Any | None, question: str) -> QueryPlan:
    """Ask the model for the retrieval plan; fall back on any failure."""

    question = (question or "").strip()
    if not question:
        return fallback_plan(question)
    if model is None:
        return fallback_plan(question)
    prompt = load_prompt(PROMPT_NAME).replace("%%QUESTION%%", question)
    try:
        result = model.chat(
            [{"role": "user", "content": prompt}],
            role="translate_query",
            temperature=0.0,
        )
        payload = _parse(getattr(result, "text", ""))
    except Exception:  # the rewrite is best effort, never fatal
        return fallback_plan(question)
    if payload is None:
        return fallback_plan(question)

    english = str(payload.get("english_query") or "").strip()
    keywords = payload.get("keywords")
    keyword_list = [str(item).strip() for item in keywords] if isinstance(keywords, list) else []
    # The English query already carries the terms; the keyword list is the
    # fallback when the model returns no English sentence.
    keyword_query = english or " ".join(term for term in keyword_list if term).strip()
    semantic = (question, english) if english else (question,)
    return QueryPlan(
        question=question,
        keyword_query=keyword_query or question,
        semantic_queries=semantic,
        need_retrieval=bool(payload.get("need_retrieval", True)),
    )
