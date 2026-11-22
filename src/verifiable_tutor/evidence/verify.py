"""Deterministic span verification for citations.

A quoted span is valid only when it occurs on the cited page after whitespace
and case normalization. This is a pure string check, not a model call: the span
must be a literal substring of the page text once both are normalized.
"""

from __future__ import annotations


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
