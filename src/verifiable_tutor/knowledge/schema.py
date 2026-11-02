"""Validate the records and progress a knowledge-base job returns.

The TACC job writes what the model produced; the local driver applies the
contract. Record validation follows ``docs/knowledge-schema.md`` and the same
span rule as the evidence verifier: a quoted span is accepted only if it occurs
on the cited page after whitespace and case normalization.
"""

from __future__ import annotations

import re
from typing import Mapping

RECORD_SCHEMA = "vt-kb-record/1"
PROGRESS_SCHEMA = "vt-kb-progress/1"
_PROGRESS_STATUSES = {"running", "done", "failed"}
_REQUIRED_RECORD_STRINGS = (
    "build_id",
    "job_id",
    "chunk_id",
    "doc_id",
    "model",
    "prompt_version",
    "corpus_hash",
    "created_at",
)
_REQUIRED_PROGRESS_STRINGS = ("build_id", "job_id", "updated_at")

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse whitespace and case for quote matching."""

    return _WHITESPACE.sub(" ", text or "").strip().casefold()


def quote_on_page(quote: str, page_text: str) -> bool:
    normalized_quote = normalize_text(quote)
    return bool(normalized_quote) and normalized_quote in normalize_text(page_text)


def _check_string(
    record: Mapping, field: str, issues: list[str], *, min_length: int = 1
) -> None:
    value = record.get(field)
    if not isinstance(value, str) or len(value.strip()) < min_length:
        issues.append(f"{field} must be a non-empty string")


def _check_string_list(
    record: Mapping,
    field: str,
    issues: list[str],
    *,
    minimum: int,
    maximum: int | None = None,
) -> None:
    value = record.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        issues.append(f"{field} must be a list of strings")
        return
    if len(value) < minimum:
        issues.append(f"{field} needs at least {minimum} items")
    if maximum is not None and len(value) > maximum:
        issues.append(f"{field} allows at most {maximum} items")


def validate_record(
    record: Mapping, pages: Mapping[tuple[str, int], str]
) -> list[str]:
    """Return the list of contract violations for one record (empty is valid)."""

    issues: list[str] = []
    if not isinstance(record, Mapping):
        return ["record must be a JSON object"]
    if record.get("schema") != RECORD_SCHEMA:
        issues.append(f"schema must be {RECORD_SCHEMA}")
    for field in _REQUIRED_RECORD_STRINGS:
        _check_string(record, field, issues)

    page_no = record.get("page_no")
    if not isinstance(page_no, int) or isinstance(page_no, bool):
        issues.append("page_no must be an integer")
    section = record.get("section")
    if section is not None and not isinstance(section, str):
        issues.append("section must be a string or null")

    source_block_ids = record.get("source_block_ids")
    if not isinstance(source_block_ids, list) or not all(
        isinstance(item, str) for item in source_block_ids
    ):
        issues.append("source_block_ids must be a list of strings")

    _check_string(record, "summary", issues)
    _check_string_list(record, "key_terms", issues, minimum=1, maximum=8)
    _check_string_list(record, "study_questions", issues, minimum=2, maximum=5)

    citations = record.get("citations")
    if not isinstance(citations, list) or not citations:
        issues.append("citations must be a non-empty list")
        return issues
    for index, citation in enumerate(citations):
        if not isinstance(citation, Mapping):
            issues.append(f"citations[{index}] must be an object")
            continue
        doc_id = citation.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            issues.append(f"citations[{index}].doc_id must be a non-empty string")
            continue
        cited_page = citation.get("page_no")
        if not isinstance(cited_page, int) or isinstance(cited_page, bool):
            issues.append(f"citations[{index}].page_no must be an integer")
            continue
        quote = citation.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            issues.append(f"citations[{index}].quote must be a non-empty string")
            continue
        page_text = pages.get((doc_id, cited_page))
        if page_text is None:
            issues.append(
                f"citations[{index}] cites page {doc_id} page {cited_page}, "
                "which is not in the corpus"
            )
            continue
        if not quote_on_page(quote, page_text):
            issues.append(
                f"citations[{index}].quote is not found on "
                f"{doc_id} page {cited_page}"
            )
    return issues


def validate_progress(progress: Mapping) -> list[str]:
    """Return the contract violations for one progress object."""

    issues: list[str] = []
    if not isinstance(progress, Mapping):
        return ["progress must be a JSON object"]
    if progress.get("schema") != PROGRESS_SCHEMA:
        issues.append(f"schema must be {PROGRESS_SCHEMA}")
    for field in _REQUIRED_PROGRESS_STRINGS:
        _check_string(progress, field, issues)
    status = progress.get("status")
    if status not in _PROGRESS_STATUSES:
        issues.append(f"status must be one of {sorted(_PROGRESS_STATUSES)}")
    done = progress.get("done_chunks")
    total = progress.get("total_chunks")
    if not isinstance(done, int) or isinstance(done, bool):
        issues.append("done_chunks must be an integer")
    if not isinstance(total, int) or isinstance(total, bool):
        issues.append("total_chunks must be an integer")
    if isinstance(done, int) and isinstance(total, int) and done > total:
        issues.append("done_chunks must not exceed total_chunks")
    error = progress.get("error")
    if error is not None and not isinstance(error, str):
        issues.append("error must be a string or null")
    return issues
