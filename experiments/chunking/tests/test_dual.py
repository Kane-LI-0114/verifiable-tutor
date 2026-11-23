"""Page-level fusion for the dual-granularity index."""

from __future__ import annotations

from chunking_eval.dual import (
    fuse_page_rankings,
    page_chunks,
    page_ranking_from_chunks,
)

A = ("doc", 1)
B = ("doc", 2)
C = ("doc", 3)


def chunk(chunk_id: str, page_no: int) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": "doc",
        "page_no": page_no,
        "page_nos": [page_no],
    }


def test_page_ranking_deduplicates_pages_and_keeps_first_rank() -> None:
    pages = page_ranking_from_chunks(
        [chunk("a", 1), chunk("b", 1), chunk("c", 2), chunk("d", 1)]
    )

    assert pages == [A, B]


def test_page_fusion_rewards_a_page_found_by_both_arms() -> None:
    fused = fuse_page_rankings([A, B], [B, C], k=60)

    assert fused[0] == B


def test_page_fusion_accepts_weights() -> None:
    dense_heavy = fuse_page_rankings([A], [B], k=60, weights=(1.0, 10.0))
    lexical_heavy = fuse_page_rankings([A], [B], k=60, weights=(10.0, 1.0))

    assert dense_heavy[0] == B
    assert lexical_heavy[0] == A


def test_page_chunks_carry_the_full_page_token_cost() -> None:
    chunks, page_map = page_chunks([A, B], {A: 100, B: 200})

    assert [item["token_estimate"] for item in chunks] == [100, 200]
    assert page_map[chunks[0]["chunk_id"]] == [A]
