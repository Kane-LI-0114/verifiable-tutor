"""Chunking strategies compared by the experiment.

Every strategy returns chunk dictionaries with the production fields plus two
experiment fields: ``strategy`` and ``page_nos``. ``page_nos`` is the list of
pages a chunk covers; it is a singleton for every page-bounded strategy and a
contiguous span for the cross-page strategy.

The production chunker is imported only for its token estimator and document id
normalisation. The page-first rules are copied here with a configurable budget
so the experiment does not modify production code.
"""

from __future__ import annotations

import math
import re
from typing import Callable, Iterable, Mapping, Sequence

from verifiable_tutor.corpus.chunker import (
    OVERSIZE_BLOCK_TOKENS,
    estimate_tokens,
    normalize_doc_id,
)

PROTECTED_LABELS = {"table", "display_formula", "image", "chart"}
SKIPPED_LABELS = {
    "footer",
    "footer_image",
    "header",
    "header_image",
    "page_number",
}

EmbeddingLookup = Mapping[str, Sequence[float]]


# --------------------------------------------------------------------- helpers
def usable_blocks(page: Mapping) -> list[Mapping]:
    blocks = [
        block
        for block in page.get("blocks") or []
        if isinstance(block, Mapping)
        and block.get("label") not in SKIPPED_LABELS
        and str(block.get("content") or "").strip()
    ]
    return sorted(
        blocks,
        key=lambda block: (
            block.get("block_order") is None,
            block.get("block_order") or 0,
        ),
    )


def text_of(blocks: Sequence[Mapping]) -> str:
    return "\n\n".join(str(block.get("content") or "").strip() for block in blocks)


def union_bbox(blocks: Sequence[Mapping]) -> list[float] | None:
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


def label_types(blocks: Sequence[Mapping]) -> list[str]:
    return sorted({str(block.get("label")) for block in blocks if block.get("label")})


def section_title_of(blocks: Sequence[Mapping]) -> str | None:
    for block in blocks:
        if block.get("label") == "paragraph_title":
            content = str(block.get("content") or "").strip()
            if content:
                return content
    return None


def _record(
    *,
    doc_id: str,
    page_no: int,
    page_nos: Sequence[int],
    index: int,
    blocks: Sequence[Mapping],
    section_title: str | None,
    text: str,
    strategy: str,
    budget: int | None,
    oversize: bool | None = None,
    chunk_id: str | None = None,
) -> dict:
    tokens = estimate_tokens(text)
    return {
        "schema": "vt-chunk-record/1",
        "chunk_id": chunk_id or f"{doc_id}:p{page_no:03d}:c{index:02d}",
        "doc_id": doc_id,
        "page_no": page_no,
        "page_nos": sorted({int(page) for page in page_nos}),
        "chunk_index": index,
        "section_title": section_title,
        "text": text,
        "embed_text": f"Section: {section_title}\n\n{text}" if section_title else text,
        "block_ids": [
            int(block["block_id"])
            for block in blocks
            if isinstance(block.get("block_id"), int)
        ],
        "label_types": label_types(blocks),
        "bbox_norm": union_bbox(blocks),
        "token_estimate": tokens,
        "oversize": (
            bool(oversize)
            if oversize is not None
            else any(
                estimate_tokens(str(block.get("content") or "")) > OVERSIZE_BLOCK_TOKENS
                for block in blocks
            )
        ),
        "chunker_version": f"eval/{strategy}/{budget}" if budget else f"eval/{strategy}",
        "strategy": strategy,
        "budget": budget,
    }


def _page_doc_id(page: Mapping) -> str:
    doc_id = normalize_doc_id(str(page.get("doc_id") or ""))
    if not doc_id:
        raise ValueError("page record has no doc_id")
    return doc_id


def _page_no(page: Mapping) -> int:
    page_no = page.get("page_no")
    if not isinstance(page_no, int) or isinstance(page_no, bool):
        raise ValueError(f"page record has no integer page_no: {page!r}")
    return page_no


# ---------------------------------------------------------------- page only
def page_only(pages: Iterable[Mapping]) -> list[dict]:
    """One chunk per page, never split."""

    chunks: list[dict] = []
    for page in pages:
        doc_id = _page_doc_id(page)
        page_no = _page_no(page)
        blocks = usable_blocks(page)
        if blocks:
            text = text_of(blocks)
            section = section_title_of(blocks)
        else:
            text = str(page.get("text") or "").strip()
            section = None
        if not text:
            continue
        tokens = estimate_tokens(text)
        chunks.append(
            _record(
                doc_id=doc_id,
                page_no=page_no,
                page_nos=[page_no],
                index=0,
                blocks=blocks,
                section_title=section,
                text=text,
                strategy="page_only",
                budget=None,
                oversize=tokens > 512,
            )
        )
    return chunks


# --------------------------------------------------------------- page first
def _sections(blocks: Sequence[Mapping]) -> list[list[Mapping]]:
    sections: list[list[Mapping]] = []
    for block in blocks:
        if block.get("label") == "paragraph_title" and sections and sections[-1]:
            sections.append([block])
        elif sections:
            sections[-1].append(block)
        else:
            sections.append([block])
    return sections


def _pack(
    blocks: Sequence[Mapping], budget: int, oversize_tokens: int
) -> list[list[Mapping]]:
    groups: list[list[Mapping]] = []
    current: list[Mapping] = []
    current_tokens = 0
    for block in blocks:
        tokens = estimate_tokens(str(block.get("content") or ""))
        if tokens > oversize_tokens:
            if current:
                groups.append(current)
                current, current_tokens = [], 0
            groups.append([block])
            continue
        if current and current_tokens + tokens > budget:
            groups.append(current)
            current, current_tokens = [], 0
        current.append(block)
        current_tokens += tokens
    if current:
        groups.append(current)
    return groups


def _page_groups(
    blocks: Sequence[Mapping], budget: int, oversize_tokens: int
) -> list[list[Mapping]]:
    total = sum(estimate_tokens(str(block.get("content") or "")) for block in blocks)
    if total <= budget:
        return [list(blocks)]

    groups: list[list[Mapping]] = []
    current: list[Mapping] = []
    current_tokens = 0
    for section in _sections(blocks):
        section_tokens = sum(
            estimate_tokens(str(block.get("content") or "")) for block in section
        )
        if section_tokens > budget:
            if current:
                groups.append(current)
                current, current_tokens = [], 0
            groups.extend(_pack(section, budget, oversize_tokens))
            continue
        if current and current_tokens + section_tokens > budget:
            groups.append(current)
            current, current_tokens = [], 0
        current.extend(section)
        current_tokens += section_tokens
    if current:
        groups.append(current)
    return groups


def page_first(
    pages: Iterable[Mapping],
    *,
    max_tokens: int = 450,
    oversize_tokens: int = OVERSIZE_BLOCK_TOKENS,
) -> list[dict]:
    """The production rules with a configurable page budget."""

    chunks: list[dict] = []
    for page in pages:
        doc_id = _page_doc_id(page)
        page_no = _page_no(page)
        blocks = usable_blocks(page)
        if not blocks:
            text = str(page.get("text") or "").strip()
            if text:
                chunks.append(
                    _record(
                        doc_id=doc_id,
                        page_no=page_no,
                        page_nos=[page_no],
                        index=0,
                        blocks=[],
                        section_title=None,
                        text=text,
                        strategy="page_first",
                        budget=max_tokens,
                    )
                )
            continue
        running_section: str | None = None
        for index, group in enumerate(_page_groups(blocks, max_tokens, oversize_tokens)):
            leading = section_title_of(group)
            if leading is not None:
                running_section = leading
            group_tokens = sum(
                estimate_tokens(str(block.get("content") or "")) for block in group
            )
            chunks.append(
                _record(
                    doc_id=doc_id,
                    page_no=page_no,
                    page_nos=[page_no],
                    index=index,
                    blocks=group,
                    section_title=leading or running_section,
                    text=text_of(group),
                    strategy="page_first",
                    budget=max_tokens,
                    oversize=group_tokens > max_tokens,
                )
            )
    return chunks


# ----------------------------------------------------------------- recursive
_SEPARATORS = ("\n\n", "\n", ". ", " ")


def _char_cost(char: str) -> float:
    return 1.0 if "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff" else 0.25


def _hard_split(text: str, budget: int) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    cost = 0.0
    for char in text:
        step = _char_cost(char)
        if current and cost + step > budget:
            pieces.append("".join(current))
            current, cost = [], 0.0
        current.append(char)
        cost += step
    if current:
        pieces.append("".join(current))
    return pieces


def _split_text(text: str, budget: int, separators: Sequence[str]) -> list[str]:
    if estimate_tokens(text) <= budget:
        return [text]
    if not separators:
        return _hard_split(text, budget)
    separator = separators[0]
    if separator not in text:
        return _split_text(text, budget, separators[1:])
    raw = text.split(separator)
    parts: list[str] = []
    for position, part in enumerate(raw):
        if position < len(raw) - 1:
            part = part + separator
        if not part:
            continue
        if estimate_tokens(part) > budget:
            parts.extend(_split_text(part, budget, separators[1:]))
        else:
            parts.append(part)
    merged: list[str] = []
    current = ""
    for part in parts:
        candidate = current + part
        if current and estimate_tokens(candidate) > budget:
            merged.append(current)
            current = part
        else:
            current = candidate
    if current:
        merged.append(current)
    return merged


def _units_from_blocks(
    blocks: Sequence[Mapping], budget: int
) -> list[dict]:
    units: list[dict] = []
    for block in blocks:
        label = str(block.get("label") or "")
        content = str(block.get("content") or "").strip()
        if not content:
            continue
        if label in PROTECTED_LABELS or estimate_tokens(content) <= budget:
            units.append(
                {"text": content, "block": block, "label": label, "tokens": estimate_tokens(content)}
            )
            continue
        for piece in _split_text(content, budget, _SEPARATORS):
            units.append(
                {
                    "text": piece,
                    "block": block,
                    "label": label,
                    "tokens": estimate_tokens(piece),
                }
            )
    return units


def _pack_units(units: Sequence[dict], budget: int) -> list[list[dict]]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_tokens = 0
    for unit in units:
        if unit["tokens"] > budget:
            if current:
                groups.append(current)
                current, current_tokens = [], 0
            groups.append([unit])
            continue
        if current and current_tokens + unit["tokens"] > budget:
            groups.append(current)
            current, current_tokens = [], 0
        current.append(unit)
        current_tokens += unit["tokens"]
    if current:
        groups.append(current)
    return groups


def recursive(pages: Iterable[Mapping], *, max_tokens: int = 450) -> list[dict]:
    """Split long text at paragraph, sentence, and word boundaries, then pack."""

    chunks: list[dict] = []
    for page in pages:
        doc_id = _page_doc_id(page)
        page_no = _page_no(page)
        blocks = usable_blocks(page)
        units = _units_from_blocks(blocks, max_tokens)
        if not units:
            text = str(page.get("text") or "").strip()
            if text:
                chunks.append(
                    _record(
                        doc_id=doc_id,
                        page_no=page_no,
                        page_nos=[page_no],
                        index=0,
                        blocks=[],
                        section_title=None,
                        text=text,
                        strategy="recursive",
                        budget=max_tokens,
                    )
                )
            continue
        running_section: str | None = None
        for index, group in enumerate(_pack_units(units, max_tokens)):
            section = section_title_of([unit["block"] for unit in group])
            if section is not None:
                running_section = section
            chunks.append(
                _record(
                    doc_id=doc_id,
                    page_no=page_no,
                    page_nos=[page_no],
                    index=index,
                    blocks=[unit["block"] for unit in group],
                    section_title=section or running_section,
                    text="\n\n".join(unit["text"].strip() for unit in group),
                    strategy="recursive",
                    budget=max_tokens,
                    oversize=any(unit["tokens"] > max_tokens for unit in group),
                )
            )
    return chunks


# --------------------------------------------------------- long page hybrid
def long_page_hybrid(
    pages: Iterable[Mapping], *, keep_tokens: int = 256, split_tokens: int = 128
) -> list[dict]:
    """Keep pages up to a threshold whole and split only the longer ones.

    A naive ``recursive`` run already keeps a page whole when it fits the
    budget, so "split only long pages" is only a distinct strategy when the
    split budget is smaller than the keep threshold. This rule protects medium
    pages from fragmentation and applies the fine-grained split only where the
    512-token embedding window would otherwise truncate content.
    """

    chunks: list[dict] = []
    for page in pages:
        blocks = usable_blocks(page)
        total = sum(
            estimate_tokens(str(block.get("content") or "")) for block in blocks
        )
        if total <= keep_tokens:
            produced = page_only([page])
        else:
            produced = recursive([page], max_tokens=split_tokens)
        version = f"eval/long_hybrid/{keep_tokens}_{split_tokens}"
        for chunk in produced:
            chunk["strategy"] = "long_hybrid"
            chunk["chunker_version"] = version
            chunk["budget"] = split_tokens
            chunks.append(chunk)
    return chunks


# ------------------------------------------------------------------ semantic
def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return float(sum(float(a) * float(b) for a, b in zip(left, right)))


def semantic(
    pages: Iterable[Mapping],
    *,
    max_tokens: int = 450,
    threshold: float = 0.6,
    vector_lookup: EmbeddingLookup,
) -> list[dict]:
    """Start a new chunk when adjacent blocks stop being similar."""

    chunks: list[dict] = []
    for page in pages:
        doc_id = _page_doc_id(page)
        page_no = _page_no(page)
        blocks = usable_blocks(page)
        if not blocks:
            continue
        groups: list[list[Mapping]] = []
        current: list[Mapping] = []
        current_tokens = 0
        previous_vector: Sequence[float] | None = None
        for block in blocks:
            content = str(block.get("content") or "").strip()
            tokens = estimate_tokens(content)
            vector = vector_lookup.get(content)
            split = bool(current) and (
                current_tokens + tokens > max_tokens
                or (
                    vector is not None
                    and previous_vector is not None
                    and _dot(previous_vector, vector) < threshold
                )
                or tokens > max_tokens
            )
            if split:
                groups.append(current)
                current, current_tokens = [], 0
            current.append(block)
            current_tokens += tokens
            previous_vector = vector
            if tokens > max_tokens:
                groups.append(current)
                current, current_tokens = [], 0
                previous_vector = None
        if current:
            groups.append(current)

        running_section: str | None = None
        for index, group in enumerate(groups):
            section = section_title_of(group)
            if section is not None:
                running_section = section
            chunks.append(
                _record(
                    doc_id=doc_id,
                    page_no=page_no,
                    page_nos=[page_no],
                    index=index,
                    blocks=group,
                    section_title=section or running_section,
                    text=text_of(group),
                    strategy="semantic",
                    budget=max_tokens,
                    oversize=any(
                        estimate_tokens(str(block.get("content") or "")) > max_tokens
                        for block in group
                    ),
                )
            )
    return chunks


# --------------------------------------------------------------- cross page
def _norm_title(title: str | None) -> str:
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip().lower())


def cross_page(
    pages: Iterable[Mapping], *, max_tokens: int = 450
) -> list[dict]:
    """Merge consecutive pages that carry the same leading page title.

    A lecture deck repeats its main title on every slide of a topic. This
    strategy treats the whole page as the unit and merges pages with the same
    normalized leading title until the budget is reached. It is the only
    strategy that can return a chunk covering more than one page.
    """

    by_doc: dict[str, list[Mapping]] = {}
    for page in pages:
        by_doc.setdefault(_page_doc_id(page), []).append(page)

    chunks: list[dict] = []
    for doc_id, doc_pages in by_doc.items():
        doc_pages.sort(key=_page_no)
        current_blocks: list[Mapping] = []
        current_pages: list[int] = []
        current_title: str | None = None
        current_tokens = 0
        index = 0

        def emit(blocks, page_nos, title, tokens):
            nonlocal index
            chunks.append(
                _record(
                    doc_id=doc_id,
                    page_no=min(page_nos),
                    page_nos=page_nos,
                    index=index,
                    blocks=blocks,
                    section_title=title,
                    text=text_of(blocks),
                    strategy="cross_page",
                    budget=max_tokens,
                    oversize=tokens > max_tokens,
                    chunk_id=f"{doc_id}:x{index:03d}",
                )
            )
            index += 1

        def flush() -> None:
            nonlocal current_blocks, current_pages, current_title, current_tokens
            if current_blocks:
                emit(current_blocks, current_pages, current_title, current_tokens)
            current_blocks, current_pages, current_title, current_tokens = [], [], None, 0

        for page in doc_pages:
            page_no = _page_no(page)
            blocks = usable_blocks(page)
            if not blocks:
                continue
            title = section_title_of(blocks)
            page_tokens = sum(
                estimate_tokens(str(block.get("content") or "")) for block in blocks
            )
            same_title = bool(
                title and current_title and _norm_title(title) == _norm_title(current_title)
            )
            if same_title and current_tokens + page_tokens <= max_tokens:
                current_blocks.extend(blocks)
                current_pages.append(page_no)
                current_tokens += page_tokens
                continue

            flush()
            if page_tokens <= max_tokens:
                current_blocks = list(blocks)
                current_pages = [page_no]
                current_title = title
                current_tokens = page_tokens
            else:
                for group in _page_groups(blocks, max_tokens, OVERSIZE_BLOCK_TOKENS):
                    group_tokens = sum(
                        estimate_tokens(str(block.get("content") or "")) for block in group
                    )
                    emit(group, [page_no], title, group_tokens)
        flush()
    return chunks


# ---------------------------------------------------------------- dispatcher
def chunk_pages(
    pages: Iterable[Mapping],
    strategy: str,
    *,
    max_tokens: int | None = None,
    threshold: float = 0.6,
    split_tokens: int = 128,
    vector_lookup: EmbeddingLookup | None = None,
) -> list[dict]:
    page_list = list(pages)
    if strategy == "page_only":
        return page_only(page_list)
    if strategy == "page_first":
        return page_first(page_list, max_tokens=max_tokens or 450)
    if strategy == "recursive":
        return recursive(page_list, max_tokens=max_tokens or 450)
    if strategy == "long_hybrid":
        return long_page_hybrid(
            page_list,
            keep_tokens=max_tokens or 256,
            split_tokens=split_tokens,
        )
    if strategy == "semantic":
        if vector_lookup is None:
            raise ValueError("semantic chunking needs a vector_lookup")
        return semantic(
            page_list,
            max_tokens=max_tokens or 450,
            threshold=threshold,
            vector_lookup=vector_lookup,
        )
    if strategy == "cross_page":
        return cross_page(page_list, max_tokens=max_tokens or 450)
    raise ValueError(f"unknown strategy: {strategy!r}")


def chunk_stats(chunks: Sequence[Mapping]) -> dict:
    tokens = [int(chunk.get("token_estimate") or 0) for chunk in chunks]
    if not tokens:
        return {"chunks": 0}
    return {
        "chunks": len(tokens),
        "mean_tokens": round(sum(tokens) / len(tokens), 1),
        "median_tokens": sorted(tokens)[len(tokens) // 2],
        "max_tokens": max(tokens),
        "oversize": sum(1 for chunk in chunks if chunk.get("oversize")),
        "multi_page": sum(1 for chunk in chunks if len(chunk.get("page_nos") or []) > 1),
    }
