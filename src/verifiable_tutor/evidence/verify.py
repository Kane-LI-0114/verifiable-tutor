"""Deterministic span verification for citations.

A quoted span is valid only when it occurs on the cited page after whitespace
and case normalization. This is a pure string check, not a model call: the span
must be a literal substring of the page text once both are normalized.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def normalize(text: str) -> str:
    """Collapse all whitespace runs to a single space and lowercase."""

    return " ".join((text or "").split()).lower()


def verify_span(span: str, text: str) -> bool:
    """Return True when the normalized span is a substring of the text.

    An empty span is not a citation, so it never verifies.
    """

    normalized_span = normalize(span)
    if not normalized_span:
        return False
    return normalized_span in normalize(text)


@dataclass(frozen=True)
class CitationVerdict:
    """One span verification verdict for a single citation."""

    verified: bool
    in_chunk: bool
    in_page: bool
    normalized_span: str


def verify_citation(span: str, chunk_text: str, page_text: str) -> CitationVerdict:
    """Verify a quoted span against the chunk the model saw and the full page.

    ``verified`` means the span occurs on the cited page (VT-05: a passing span
    is necessary for grounding). ``in_chunk`` records whether the span was also
    in the chunk the model was shown. Empty spans never pass.
    """

    normalized_span = normalize(span)
    if not normalized_span:
        return CitationVerdict(
            verified=False, in_chunk=False, in_page=False, normalized_span=""
        )
    in_chunk = normalized_span in normalize(chunk_text)
    in_page = normalized_span in normalize(page_text)
    return CitationVerdict(
        verified=in_page,
        in_chunk=in_chunk,
        in_page=in_page,
        normalized_span=normalized_span,
    )


def _review_prompt(span: str, text: str) -> str:
    return (
        "You are a strict citation reviewer. Decide whether the quoted span is "
        "supported by the reference text.\n\n"
        "Quoted span:\n" + span + "\n\n"
        "Reference text:\n" + text + "\n\n"
        "The span is supported when it appears in the reference text verbatim, "
        "or is a faithful near-verbatim copy of a passage there (minor "
        "punctuation or whitespace differences allowed). Return exactly "
        '"match" or "no_match" and nothing else.'
    )


def verify_span_llm(
    span: str,
    text: str,
    adapter: Any,
    *,
    provider: str = "mimo",
    tier: str = "flash",
) -> bool:
    """Use a reviewer LLM to judge whether the span is supported by the text.

    This is the flexible second level: unlike ``verify_span`` it accepts a
    near-verbatim span, not only an exact substring. The adapter is a seam;
    production passes the project model adapter, tests pass a fake. The
    reviewer must return exactly "match" or "no_match". An empty span never
    calls the reviewer.
    """

    if not span or not span.strip():
        return False
    result = adapter.chat(
        [{"role": "user", "content": _review_prompt(span, text)}],
        provider=provider,
        tier=tier,
        temperature=0.0,
    )
    return (result.text or "").strip().lower() == "match"
