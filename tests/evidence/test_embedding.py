"""Local embedding seam: batching and normalisation, without loading a model."""

from __future__ import annotations

import math

import pytest

from verifiable_tutor.evidence.embedding import EmbeddingUnavailable, LocalEmbedder


def test_the_embedder_normalises_each_vector() -> None:
    seen: list[list[str]] = []

    def encoder(texts: list[str]) -> list[list[float]]:
        seen.append(texts)
        return [[3.0, 4.0], [0.0, 2.0]]

    embedder = LocalEmbedder(encoder=encoder, batch_size=8, dimension=2)

    vectors = embedder.embed(["first", "second"])

    assert seen == [["first", "second"]]
    assert vectors[0] == pytest.approx([0.6, 0.8])
    assert vectors[1] == pytest.approx([0.0, 1.0])
    assert math.isclose(sum(value * value for value in vectors[0]), 1.0)


def test_the_embedder_batches_long_inputs() -> None:
    calls: list[list[str]] = []

    def encoder(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

    LocalEmbedder(encoder=encoder, batch_size=2, dimension=2).embed(["a", "b", "c"])

    assert [len(batch) for batch in calls] == [2, 1]


def test_an_unavailable_model_raises_a_typed_error() -> None:
    def encoder(_: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailable("no weights")

    with pytest.raises(EmbeddingUnavailable):
        LocalEmbedder(encoder=encoder, batch_size=2, dimension=2).embed(["x"])
