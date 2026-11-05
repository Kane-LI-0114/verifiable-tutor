"""Reciprocal rank fusion seam: two rankings in, one fused ranking out."""

from __future__ import annotations

from verifiable_tutor.evidence.rrf import reciprocal_rank_fusion


def test_fusion_rewards_a_chunk_ranked_by_both_arms() -> None:
    # Hand-computed at k=60: a = 1/61 + 1/63, b = 1/62 + 1/61, c = 1/63 + 1/62,
    # so b (0.032522) beats a (0.032266) beats c (0.032002).
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "a"]])

    assert [item.chunk_id for item in fused] == ["b", "a", "c"]
    assert fused[0].score == 0.032522  # rounded to six places


def test_weights_move_the_order_towards_one_arm() -> None:
    fused = reciprocal_rank_fusion(
        [["a", "b"], ["b", "a"]], weights=[0.1, 1.0]
    )

    assert fused[0].chunk_id == "b"


def test_an_empty_ranking_contributes_nothing() -> None:
    fused = reciprocal_rank_fusion([[], ["a", "b"]])

    assert [item.chunk_id for item in fused] == ["a", "b"]
    assert fused[0].score == 0.016393  # 1 / (60 + 1)
