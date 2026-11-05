"""Query-plan seam: the model writes the retrieval queries, or we fall back."""

from __future__ import annotations

from types import SimpleNamespace

from verifiable_tutor.evidence.query import fallback_plan, plan_query


class FakeModel:
    def __init__(self, text: str | None = None, *, error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.calls: list[dict] = []

    def chat(self, messages, **kwargs):  # noqa: ANN001 - mirrors the adapter
        self.calls.append({"messages": messages, **kwargs})
        if self._error is not None:
            raise self._error
        return SimpleNamespace(text=self._text)


def test_the_plan_carries_the_english_variant_and_the_keywords() -> None:
    model = FakeModel(
        '```json\n{"need_retrieval": true, "english_query": "allreduce gradient",'
        ' "keywords": ["allreduce", "gradient"]}\n```'
    )

    plan = plan_query(model, "梯度是怎么聚合的？")

    assert plan.need_retrieval is True
    assert plan.keyword_query == "allreduce gradient"
    assert plan.semantic_queries == ("梯度是怎么聚合的？", "allreduce gradient")
    assert model.calls[0]["role"] == "translate_query"


def test_a_failing_rewrite_falls_back_to_the_raw_question() -> None:
    plan = plan_query(FakeModel(error=RuntimeError("model down")), "MPI_Allreduce")

    assert plan == fallback_plan("MPI_Allreduce")


def test_a_missing_model_uses_the_fallback_plan() -> None:
    assert plan_query(None, "shared memory") == fallback_plan("shared memory")
