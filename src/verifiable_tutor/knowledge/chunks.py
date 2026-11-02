"""Turn OCR page records into knowledge-base input chunks.

The knowledge-base request contract in ``docs/knowledge-schema.md`` defines one
input line per source chunk with ``chunk_id``, ``doc_id``, ``page_no``,
``section``, ``source_block_ids`` and ``text``. For the Qwen spike this module
emits one chunk per non-empty page, which keeps every citation traceable to a
page the local driver can validate against. The product chunker will replace it
under ``src/verifiable_tutor/corpus/``.

The OCR prototype names documents ``<request-id>-<pdf-stem>``; a knowledge-base
record cites the logical document, so the request prefix is stripped.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

_PAGE_SCHEMA = "vt-page-record/1"
_REQUEST_PREFIX = re.compile(r"^\d{8}-\d{6}-\d{3}-")
_SKIPPED_LABELS = {
    "footer",
    "footer_image",
    "header",
    "header_image",
    "page_number",
}


def normalize_doc_id(doc_id: str) -> str:
    """Strip the OCR request prefix from a document id."""

    return _REQUEST_PREFIX.sub("", doc_id)


def _blocks_in_reading_order(page: Mapping) -> list[Mapping]:
    blocks = [block for block in page.get("blocks") or [] if isinstance(block, Mapping)]
    return sorted(
        blocks,
        key=lambda block: (
            block.get("block_order") is None,
            block.get("block_order") or 0,
        ),
    )


def _section_title(blocks: list[Mapping]) -> str | None:
    for block in blocks:
        if block.get("label") == "paragraph_title":
            content = str(block.get("content") or "").strip()
            if content:
                return content
    return None


def _source_block_ids(blocks: list[Mapping]) -> list[str]:
    ids: list[str] = []
    for block in blocks:
        if block.get("label") in _SKIPPED_LABELS:
            continue
        if not str(block.get("content") or "").strip():
            continue
        block_id = block.get("block_id")
        if block_id is None:
            continue
        ids.append(str(block_id))
    return ids


def _page_text(page: Mapping) -> str:
    return str(page.get("text") or "").strip()


def chunks_from_pages(
    pages: Iterable[Mapping],
    *,
    doc_id: str | None = None,
    max_chunks: int | None = None,
) -> list[dict]:
    """Build knowledge-base input chunks from page records.

    Pages with an empty text layer are skipped. ``max_chunks`` caps the result
    after skipping, preserving page order. All chunks of one call share one
    document id: the explicit one, or the first page's normalised id.
    """

    if max_chunks is not None and max_chunks <= 0:
        raise ValueError("max_chunks must be a positive integer")

    resolved_doc_id = normalize_doc_id(doc_id) if doc_id else None
    chunks: list[dict] = []
    for page in pages:
        if page.get("schema") not in (None, _PAGE_SCHEMA):
            raise ValueError(f"unsupported page schema: {page.get('schema')!r}")
        text = _page_text(page)
        if not text:
            continue
        page_doc_id = resolved_doc_id or normalize_doc_id(str(page.get("doc_id") or ""))
        if not page_doc_id:
            raise ValueError("page record has no doc_id")
        page_no = page.get("page_no")
        if not isinstance(page_no, int) or isinstance(page_no, bool):
            raise ValueError(f"page record has no integer page_no: {page!r}")
        blocks = _blocks_in_reading_order(page)
        chunks.append(
            {
                "chunk_id": f"{page_doc_id}:p{page_no:03d}:c00",
                "doc_id": page_doc_id,
                "page_no": page_no,
                "section": _section_title(blocks),
                "source_block_ids": _source_block_ids(blocks),
                "text": text,
            }
        )
        if max_chunks is not None and len(chunks) >= max_chunks:
            break
    return chunks
