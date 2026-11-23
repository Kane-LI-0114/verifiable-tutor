"""Page-level retrieval metrics, with expected values computed by hand."""

from __future__ import annotations

import math

from chunking_eval.metrics import (
    context_tokens_at_k,
    evaluate_rankings,
    mrr,
    ndcg_at_k,
    page_hit_at_k,
    page_sequence,
)

P1 = ("doc_a", 1)
P2 = ("doc_a", 2)
P3 = ("doc_a", 3)


def chunk(chunk_id: str, tokens: int = 10) -> dict:
    return {"chunk_id": chunk_id, "token_estimate": tokens}


def test_pages_are_expanded_and_deduplicated_in_rank_order() -> None:
    chunks = [chunk("c1"), chunk("c2"), chunk("c3")]
    page_map = {
        "c1": [P1, P2],
        "c2": [P1, P3],
        "c3": [P3],
    }

    assert page_sequence(chunks, page_map) == [P1, P2, P3]


def test_hit_at_k_counts_the_first_occurrence_of_a_gold_page() -> None:
    chunks = [chunk("c1"), chunk("c2"), chunk("c3")]
    page_map = {"c1": [P1], "c2": [P2], "c3": [P3]}
    gold = {P2}

    assert page_hit_at_k(chunks, page_map, gold, 1) is False
    assert page_hit_at_k(chunks, page_map, gold, 2) is True


def test_ndcg_and_mrr_use_the_page_rank_not_the_chunk_rank() -> None:
    chunks = [chunk("c1"), chunk("c2"), chunk("c3")]
    page_map = {"c1": [P1], "c2": [P2], "c3": [P3]}
    gold = {P2}

    assert ndcg_at_k(chunks, page_map, gold, 3) == 1.0 / math.log2(3)
    assert mrr(chunks, page_map, gold) == 0.5


def test_ndcg_idcg_accounts_for_two_gold_pages() -> None:
    chunks = [chunk("c1"), chunk("c2"), chunk("c3")]
    page_map = {"c1": [P1], "c2": [P2], "c3": [P3]}
    gold = {P1, P3}

    dcg = 1.0 + 1.0 / math.log2(4)
    idcg = 1.0 + 1.0 / math.log2(3)
    assert ndcg_at_k(chunks, page_map, gold, 3) == dcg / idcg


def test_context_tokens_stop_when_k_pages_have_been_seen() -> None:
    chunks = [chunk("c1", 10), chunk("c2", 20), chunk("c3", 40)]
    page_map = {"c1": [P1, P2], "c2": [P3], "c3": [("doc_a", 4)]}

    assert context_tokens_at_k(chunks, page_map, 2) == 10
    assert context_tokens_at_k(chunks, page_map, 3) == 30
    assert context_tokens_at_k(chunks, page_map, 5) == 70


def test_evaluate_rankings_returns_all_requested_k_values() -> None:
    chunks = [chunk("c1"), chunk("c2")]
    page_map = {"c1": [P1], "c2": [P2]}
    gold = {P2}

    result = evaluate_rankings(chunks, page_map, gold, ks=(1, 2))

    assert result["hit@1"] is False
    assert result["hit@2"] is True
    assert result["ndcg@2"] == 1.0 / math.log2(3)
    assert result["mrr"] == 0.5
    assert result["context_tokens@2"] == 20


def test_an_empty_gold_set_scores_zero() -> None:
    chunks = [chunk("c1")]
    page_map = {"c1": [P1]}

    assert ndcg_at_k(chunks, page_map, set(), 5) == 0.0
    assert page_hit_at_k(chunks, page_map, set(), 5) is False
