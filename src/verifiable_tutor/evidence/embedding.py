"""Local BGE-M3 query embedding.

The dense arm needs one query vector at request time and no network call. The
model stack (torch and transformers) is an optional extra, so the encoder is
injected: production builds it lazily from ``config/models.yaml``, tests inject
a function. Without the stack the embedder reports itself unavailable and the
retriever falls back to the lexical arm.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence

Encoder = Callable[[list[str]], list[list[float]]]


class EmbeddingUnavailable(RuntimeError):
    """The local model stack or its weights are not usable."""


def _default_encoder(
    *, model_path: str, device: str, max_length: int
) -> Encoder:
    """Load BGE-M3 with transformers and run CLS pooling on the chosen device."""

    try:
        import torch  # noqa: PLC0415 - optional dependency
        from transformers import AutoModel, AutoTokenizer  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise EmbeddingUnavailable(
            "install the [embedding] extra to embed queries locally"
        ) from exc

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModel.from_pretrained(model_path).to(device).eval()
    except Exception as exc:  # missing weights or an unreachable hub
        raise EmbeddingUnavailable(str(exc)) from exc

    def encode(texts: list[str]) -> list[list[float]]:
        with torch.no_grad():
            batch = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(device)
            hidden = model(**batch).last_hidden_state[:, 0]
        return hidden.float().cpu().tolist()

    return encode


class LocalEmbedder:
    """Embed texts in batches and return L2-normalised float vectors."""

    def __init__(
        self,
        *,
        encoder: Encoder | None = None,
        model_path: str | None = None,
        device: str = "cpu",
        max_length: int = 512,
        batch_size: int = 16,
        dimension: int = 1024,
    ) -> None:
        self._encoder = encoder
        self._model_path = model_path
        self._device = device
        self._max_length = max_length
        self._batch_size = max(1, batch_size)
        self.dimension = dimension

    @property
    def available(self) -> bool:
        if self._encoder is not None:
            return True
        return self._model_path is not None

    def _resolve(self) -> Encoder:
        if self._encoder is None:
            if self._model_path is None:
                raise EmbeddingUnavailable("no embedding model is configured")
            self._encoder = _default_encoder(
                model_path=self._model_path,
                device=self._device,
                max_length=self._max_length,
            )
        return self._encoder

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        encode = self._resolve()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            if not batch:
                continue
            vectors.extend(_normalise(row) for row in encode(batch))
        return vectors


def _normalise(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) * float(value) for value in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [float(value) / norm for value in vector]
