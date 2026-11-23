"""Chunking strategy seams: page records in, page-mapped chunks out."""

from __future__ import annotations

from verifiable_tutor.corpus.chunker import chunks_from_page

from chunking_eval.strategies import (
    chunk_pages,
    cross_page,
    page_first,
    page_only,
    recursive,
    semantic,
)


def block(block_id: int, label: str, content: str, order: int) -> dict:
    return {
        "block_id": block_id,
        "block_order": order,
        "label": label,
        "content": content,
        "bbox_px": [0.0, 0.0, 100.0, 100.0],
        "bbox_norm": [0.1, 0.1, 0.9, 0.2],
    }


def page(doc_id: str, page_no: int, blocks: list[dict], text: str = "") -> dict:
    return {
        "schema": "vt-page-record/1",
        "doc_id": doc_id,
        "page_no": page_no,
        "text": text or "\n".join(item["content"] for item in blocks),
        "blocks": blocks,
    }


def test_page_only_emits_one_chunk_per_nonempty_page() -> None:
    pages = [
        page("doc", 1, [block(1, "paragraph_title", "Intro", 0), block(2, "text", "Body", 1)]),
        page("doc", 2, [], text="Only a text layer."),
        page("doc", 3, [], text=""),
    ]

    chunks = page_only(pages)

    assert [chunk["page_no"] for chunk in chunks] == [1, 2]
    assert all(chunk["page_nos"] == [chunk["page_no"]] for chunk in chunks)
    assert chunks[1]["text"] == "Only a text layer."


def test_page_first_defaults_match_the_production_chunker() -> None:
    record = page(
        "doc",
        1,
        [
            block(1, "paragraph_title", "Part one", 0),
            block(2, "text", "A" * 1000, 1),
            block(3, "paragraph_title", "Part two", 2),
            block(4, "text", "B" * 1000, 3),
        ],
    )

    produced = page_first([record])
    expected = chunks_from_page(record)

    assert [item["text"] for item in produced] == [item["text"] for item in expected]
    assert [item["block_ids"] for item in produced] == [
        item["block_ids"] for item in expected
    ]
    assert [item["section_title"] for item in produced] == [
        item["section_title"] for item in expected
    ]


def test_page_first_respects_a_small_page_budget() -> None:
    record = page(
        "doc",
        1,
        [
            block(1, "paragraph_title", "One", 0),
            block(2, "text", "A" * 600, 1),
            block(3, "paragraph_title", "Two", 2),
            block(4, "text", "B" * 600, 3),
        ],
    )

    chunks = page_first([record], max_tokens=100)

    assert len(chunks) >= 2
    assert all(
        chunk["token_estimate"] <= 100 or chunk["oversize"] for chunk in chunks
    )
    assert all(chunk["page_nos"] == [1] for chunk in chunks)


def test_recursive_keeps_a_table_whole_even_when_oversize() -> None:
    table = "| cell | value |\n" * 300
    record = page("doc", 1, [block(1, "table", table, 0)])

    chunks = recursive([record], max_tokens=100)

    assert len(chunks) == 1
    assert chunks[0]["oversize"] is True
    assert chunks[0]["text"] == table.strip()


def test_recursive_splits_long_prose_into_budget_sized_pieces() -> None:
    record = page(
        "doc",
        1,
        [block(1, "text", "A" * 800, 0), block(2, "text", "B" * 800, 1)],
    )

    chunks = recursive([record], max_tokens=100)

    assert len(chunks) >= 4
    assert all(chunk["token_estimate"] <= 100 for chunk in chunks)
    assert all(chunk["page_nos"] == [1] for chunk in chunks)


def test_semantic_starts_a_new_chunk_when_similarity_drops() -> None:
    record = page(
        "doc",
        1,
        [
            block(1, "text", "alpha topic", 0),
            block(2, "text", "alpha continuation", 1),
            block(3, "text", "beta topic", 2),
        ],
    )
    lookup = {
        "alpha topic": [1.0, 0.0],
        "alpha continuation": [1.0, 0.0],
        "beta topic": [0.0, 1.0],
    }

    chunks = semantic([record], max_tokens=100, threshold=0.5, vector_lookup=lookup)

    assert len(chunks) == 2
    assert "alpha topic" in chunks[0]["text"]
    assert "alpha continuation" in chunks[0]["text"]
    assert chunks[1]["text"] == "beta topic"


def test_cross_page_merges_a_repeated_section_and_maps_every_page() -> None:
    pages = [
        page("doc", 1, [block(1, "paragraph_title", "Tiled GEMM", 0), block(2, "text", "a", 1)]),
        page("doc", 2, [block(3, "paragraph_title", "Tiled GEMM", 0), block(4, "text", "b", 1)]),
        page("doc", 3, [block(5, "paragraph_title", "Softmax", 0), block(6, "text", "c", 1)]),
    ]

    chunks = cross_page(pages, max_tokens=1000)

    assert len(chunks) == 2
    assert chunks[0]["page_nos"] == [1, 2]
    assert chunks[0]["page_no"] == 1
    assert chunks[1]["page_nos"] == [3]


def test_page_bounded_strategies_never_cross_pages() -> None:
    pages = [
        page("doc", 1, [block(1, "text", "A" * 400, 0)]),
        page("doc", 2, [block(2, "text", "B" * 400, 1)]),
    ]
    lookup = {"A" * 400: [1.0, 0.0], "B" * 400: [1.0, 0.0]}

    for strategy in ("page_first", "recursive"):
        chunks = chunk_pages(pages, strategy, max_tokens=100)
        assert all(len(chunk["page_nos"]) == 1 for chunk in chunks)
    chunks = chunk_pages(
        pages, "semantic", max_tokens=100, threshold=0.5, vector_lookup=lookup
    )
    assert all(len(chunk["page_nos"]) == 1 for chunk in chunks)
