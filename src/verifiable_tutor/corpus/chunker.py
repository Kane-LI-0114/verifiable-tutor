"""Turn OCR page records into ``vt-chunk-record/1`` chunks.

Chunking is page-first ([ADR-0015](../../../docs/adr/0015-local-knowledge-store-and-chunking.md)):
a chunk never spans pages, the text is rebuilt from the blocks so headers and
footers drop out, and a page at or under the token budget stays one chunk. A
longer page splits at its ``paragraph_title`` sections first, then between
blocks. ``table``, ``display_formula`` and ``image`` blocks are never split, so
a single block above the oversize threshold becomes its own chunk.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping, Sequence

CHUNKER_VERSION = "vt-chunker/1"
CHUNK_SCHEMA = "vt-chunk-record/1"
PAGE_SCHEMA = "vt-page-record/1"

#: A page at or below this estimated token count becomes one chunk.
MAX_PAGE_TOKENS = 450
#: A single block above this count becomes its own chunk instead of splitting.
OVERSIZE_BLOCK_TOKENS = 500

_SKIPPED_LABELS = {
    "footer",
    "footer_image",
    "header",
    "header_image",
    "page_number",
}

_REQUEST_PREFIX = re.compile(r"^\d{8}-\d{6}-\d{3}-")
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def estimate_tokens(text: str) -> int:
    """Estimate tokens without a tokenizer: one per CJK character, four per other.

    The corpus is English with occasional Chinese, so this stays within a
    useful range of the model tokenizer without pulling one into the backend.
    """

    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    others = len(text) - cjk
    return max(1, cjk + others // 4)


def normalize_doc_id(doc_id: str) -> str:
    """Strip the OCR request prefix from a document id."""

    return _REQUEST_PREFIX.sub("", doc_id)


def _usable_blocks(page: Mapping) -> list[Mapping]:
    blocks = [
        block
        for block in page.get("blocks") or []
        if isinstance(block, Mapping)
        and block.get("label") not in _SKIPPED_LABELS
        and str(block.get("content") or "").strip()
    ]
    return sorted(
        blocks,
        key=lambda block: (
            block.get("block_order") is None,
            block.get("block_order") or 0,
        ),
    )


def _text_of(blocks: Sequence[Mapping]) -> str:
    return "\n\n".join(str(block.get("content") or "").strip() for block in blocks)


def _union_bbox(blocks: Sequence[Mapping]) -> list[float] | None:
    boxes = [
        block.get("bbox_norm")
        for block in blocks
        if isinstance(block.get("bbox_norm"), (list, tuple))
        and len(block["bbox_norm"]) == 4
    ]
    if not boxes:
        return None
    return [
        min(float(box[0]) for box in boxes),
        min(float(box[1]) for box in boxes),
        max(float(box[2]) for box in boxes),
        max(float(box[3]) for box in boxes),
    ]


def _label_types(blocks: Sequence[Mapping]) -> list[str]:
    return sorted({str(block.get("label")) for block in blocks if block.get("label")})


def _section_title(blocks: Sequence[Mapping]) -> str | None:
    for block in blocks:
        if block.get("label") == "paragraph_title":
            content = str(block.get("content") or "").strip()
            if content:
                return content
    return None


def _sections(blocks: Sequence[Mapping]) -> list[list[Mapping]]:
    """Group blocks so each ``paragraph_title`` starts a section."""

    sections: list[list[Mapping]] = []
    for block in blocks:
        if block.get("label") == "paragraph_title" and sections and sections[-1]:
            sections.append([block])
        elif sections:
            sections[-1].append(block)
        else:
            sections.append([block])
    return sections


def _pack(blocks: Sequence[Mapping]) -> list[list[Mapping]]:
    """Greedily pack blocks into groups under the page budget, keeping each whole."""

    groups: list[list[Mapping]] = []
    current: list[Mapping] = []
    current_tokens = 0
    for block in blocks:
        tokens = estimate_tokens(str(block.get("content") or ""))
        if tokens > OVERSIZE_BLOCK_TOKENS:
            if current:
                groups.append(current)
                current, current_tokens = [], 0
            groups.append([block])
            continue
        if current and current_tokens + tokens > MAX_PAGE_TOKENS:
            groups.append(current)
            current, current_tokens = [], 0
        current.append(block)
        current_tokens += tokens
    if current:
        groups.append(current)
    return groups


def _page_groups(blocks: Sequence[Mapping]) -> list[list[Mapping]]:
    total = sum(estimate_tokens(str(block.get("content") or "")) for block in blocks)
    if total <= MAX_PAGE_TOKENS:
        return [list(blocks)]

    groups: list[list[Mapping]] = []
    current: list[Mapping] = []
    current_tokens = 0
    for section in _sections(blocks):
        section_tokens = sum(
            estimate_tokens(str(block.get("content") or "")) for block in section
        )
        if section_tokens > MAX_PAGE_TOKENS:
            if current:
                groups.append(current)
                current, current_tokens = [], 0
            groups.extend(_pack(section))
            continue
        if current and current_tokens + section_tokens > MAX_PAGE_TOKENS:
            groups.append(current)
            current, current_tokens = [], 0
        current.extend(section)
        current_tokens += section_tokens
    if current:
        groups.append(current)
    return groups


def _record(
    *,
    doc_id: str,
    page_no: int,
    index: int,
    blocks: Sequence[Mapping],
    section_title: str | None,
    text: str,
) -> dict:
    tokens = estimate_tokens(text)
    oversize = any(
        estimate_tokens(str(block.get("content") or "")) > OVERSIZE_BLOCK_TOKENS
        for block in blocks
    )
    embed_text = f"Section: {section_title}\n\n{text}" if section_title else text
    return {
        "schema": CHUNK_SCHEMA,
        "chunker_version": CHUNKER_VERSION,
        "chunk_id": f"{doc_id}:p{page_no:03d}:c{index:02d}",
        "doc_id": doc_id,
        "page_no": page_no,
        "chunk_index": index,
        "section_title": section_title,
        "text": text,
        "embed_text": embed_text,
        "block_ids": [
            int(block["block_id"])
            for block in blocks
            if isinstance(block.get("block_id"), int)
        ],
        "label_types": _label_types(blocks),
        "bbox_norm": _union_bbox(blocks),
        "token_estimate": tokens,
        "oversize": oversize,
    }


def chunks_from_page(page: Mapping) -> list[dict]:
    """Build the chunks of one page record, in page order."""

    schema = page.get("schema")
    if schema not in (None, PAGE_SCHEMA):
        raise ValueError(f"unsupported page schema: {schema!r}")
    doc_id = normalize_doc_id(str(page.get("doc_id") or ""))
    if not doc_id:
        raise ValueError("page record has no doc_id")
    page_no = page.get("page_no")
    if not isinstance(page_no, int) or isinstance(page_no, bool):
        raise ValueError(f"page record has no integer page_no: {page!r}")

    blocks = _usable_blocks(page)
    if not blocks:
        text = str(page.get("text") or "").strip()
        if not text:
            return []
        return [
            _record(
                doc_id=doc_id,
                page_no=page_no,
                index=0,
                blocks=[],
                section_title=None,
                text=text,
            )
        ]

    records: list[dict] = []
    running_section: str | None = None
    for index, group in enumerate(_page_groups(blocks)):
        leading_title = _section_title(group)
        if leading_title is not None:
            running_section = leading_title
        records.append(
            _record(
                doc_id=doc_id,
                page_no=page_no,
                index=index,
                blocks=group,
                section_title=leading_title or running_section,
                text=_text_of(group),
            )
        )
    return records


def chunks_from_pages(pages: Iterable[Mapping]) -> list[dict]:
    """Build the chunks of many pages, preserving their order."""

    chunks: list[dict] = []
    for page in pages:
        chunks.extend(chunks_from_page(page))
    return chunks
