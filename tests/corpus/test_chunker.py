"""Chunker seam: page records in, ``vt-chunk-record/1`` chunks out.

Expected values are built from hand-written block texts so the token estimates
and the box unions are known independently of the implementation.
"""

from __future__ import annotations

import pytest

from verifiable_tutor.corpus.chunker import CHUNKER_VERSION, chunks_from_page


def block(
    block_id: int,
    label: str,
    content: str,
    order: int,
    bbox=(0.1, 0.1, 0.9, 0.2),
) -> dict:
    return {
        "block_id": block_id,
        "block_order": order,
        "label": label,
        "content": content,
        "bbox_px": [10.0, 10.0, 100.0, 100.0],
        "bbox_norm": list(bbox),
    }


def page(blocks: list[dict], *, doc_id: str = "ACS_Lecture_1_2026F", page_no: int = 1):
    return {
        "schema": "vt-page-record/1",
        "doc_id": doc_id,
        "page_no": page_no,
        "width_px": 1600,
        "height_px": 900,
        "text": "\n".join(str(item["content"]) for item in blocks),
        "blocks": blocks,
    }


def test_a_short_page_becomes_one_chunk_that_keeps_its_boxes() -> None:
    record = page(
        [
            block(1, "paragraph_title", "Retrieval basics", 0, (0.1, 0.1, 0.9, 0.2)),
            block(2, "text", "Dense retrieval maps queries to vectors.", 1, (0.1, 0.2, 0.9, 0.4)),
            block(3, "text", "BM25 ranks by term overlap.", 2, (0.1, 0.4, 0.9, 0.6)),
        ]
    )

    chunks = chunks_from_page(record)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["schema"] == "vt-chunk-record/1"
    assert chunk["chunker_version"] == CHUNKER_VERSION
    assert chunk["chunk_id"] == "ACS_Lecture_1_2026F:p001:c00"
    assert chunk["chunk_index"] == 0
    assert chunk["page_no"] == 1
    assert chunk["section_title"] == "Retrieval basics"
    assert chunk["text"] == (
        "Retrieval basics\n\n"
        "Dense retrieval maps queries to vectors.\n\n"
        "BM25 ranks by term overlap."
    )
    assert chunk["block_ids"] == [1, 2, 3]
    assert chunk["label_types"] == ["paragraph_title", "text"]
    assert chunk["bbox_norm"] == [0.1, 0.1, 0.9, 0.6]
    assert chunk["oversize"] is False
    assert chunk["embed_text"].startswith("Section: Retrieval basics\n\n")
    assert chunk["token_estimate"] == len(chunk["text"]) // 4


def test_a_long_page_splits_at_a_paragraph_title() -> None:
    first = "A" * 1000
    second = "B" * 1000
    record = page(
        [
            block(1, "paragraph_title", "Part one", 0),
            block(2, "text", first, 1),
            block(3, "paragraph_title", "Part two", 2),
            block(4, "text", second, 3),
        ]
    )

    chunks = chunks_from_page(record)

    assert len(chunks) == 2
    assert chunks[0]["section_title"] == "Part one"
    assert chunks[0]["text"].startswith("Part one")
    assert chunks[1]["section_title"] == "Part two"
    assert chunks[1]["text"].startswith("Part two")
    assert chunks[1]["chunk_id"] == "ACS_Lecture_1_2026F:p001:c01"
    assert {chunk["page_no"] for chunk in chunks} == {1}


def test_a_table_block_is_kept_whole_and_marked_oversize() -> None:
    table = "| col | value |\n" * 300
    record = page([block(7, "table", table, 0)])

    chunks = chunks_from_page(record)

    assert len(chunks) == 1
    assert chunks[0]["oversize"] is True
    assert chunks[0]["text"] == table.strip()
    assert chunks[0]["label_types"] == ["table"]


def test_headers_and_footers_are_left_out_of_the_chunk() -> None:
    record = page(
        [
            block(1, "header", "CSIT6000V", 0),
            block(2, "text", "Kernel launch latency dominates.", 1),
            block(3, "page_number", "12", 2),
            block(4, "footer", "HKUST", 3),
        ]
    )

    chunks = chunks_from_page(record)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Kernel launch latency dominates."
    assert chunks[0]["block_ids"] == [2]


def test_a_page_without_usable_blocks_produces_no_chunks() -> None:
    record = page([], doc_id="course_project", page_no=3)
    record["text"] = ""

    assert chunks_from_page(record) == []


def test_a_page_without_blocks_falls_back_to_its_plain_text() -> None:
    record = page([], doc_id="course_project", page_no=4)
    record["text"] = "Only a text layer is available on this page."

    chunks = chunks_from_page(record)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Only a text layer is available on this page."
    assert chunks[0]["block_ids"] == []


def test_an_unknown_page_schema_is_rejected() -> None:
    record = page([block(1, "text", "body", 0)])
    record["schema"] = "vt-page-record/9"

    with pytest.raises(ValueError, match="unsupported page schema"):
        chunks_from_page(record)


def test_the_request_prefix_is_stripped_from_the_document_id() -> None:
    record = page(
        [block(1, "text", "body", 0)], doc_id="20261029-204346-556-course_project"
    )

    chunks = chunks_from_page(record)

    assert chunks[0]["chunk_id"] == "course_project:p001:c00"
    assert chunks[0]["doc_id"] == "course_project"
