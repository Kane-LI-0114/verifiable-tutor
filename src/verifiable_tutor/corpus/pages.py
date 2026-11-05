"""Read the per-document page records the TACC OCR job writes.

The OCR batch job writes one ``pages/<doc_id>.jsonl`` per PDF, one
``vt-page-record/1`` object per page (docs/corpus-schema.md). This module is the
local reader: it validates the record envelope, normalizes the document id (the
parse prototype prefixes it with the request id), and returns pages in page
order for chunking and summaries.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PAGE_SCHEMA = "vt-page-record/1"

#: The parse prototype names documents ``<request-id>-<pdf-stem>``.
_REQUEST_PREFIX = re.compile(r"^\d{8}-\d{6}-\d{3}-")


def normalize_doc_id(doc_id: str) -> str:
    """Strip the OCR request prefix from a document id."""

    return _REQUEST_PREFIX.sub("", doc_id or "")


def read_pages(path: Path) -> list[dict]:
    """Read one page-record JSONL file, in page order."""

    pages: list[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path} line {line_number}: page record is not an object")
            if record.get("schema") != PAGE_SCHEMA:
                raise ValueError(
                    f"{path} line {line_number}: expected {PAGE_SCHEMA}, "
                    f"got {record.get('schema')!r}"
                )
            page_no = record.get("page_no")
            if not isinstance(page_no, int) or isinstance(page_no, bool):
                raise ValueError(f"{path} line {line_number}: page_no must be an integer")
            doc_id = normalize_doc_id(str(record.get("doc_id") or ""))
            if not doc_id:
                raise ValueError(f"{path} line {line_number}: page record has no doc_id")
            record["doc_id"] = doc_id
            pages.append(record)
    pages.sort(key=lambda page: int(page["page_no"]))
    return pages
