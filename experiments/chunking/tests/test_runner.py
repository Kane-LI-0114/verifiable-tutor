"""Runner seams that can be tested without a model: validation and summary."""

from __future__ import annotations

from chunking_eval.runner import (
    bootstrap_ci,
    mcnemar_p,
    summarise,
    validate_questions,
)


def page(doc_id: str, page_no: int) -> dict:
    return {"doc_id": doc_id, "page_no": page_no, "blocks": []}


def question(qid: str, doc_id: str, page_no: int) -> dict:
    return {
        "qid": qid,
        "split": "T",
        "category": "concept",
        "stratum": "short",
        "question": "q?",
        "gold_pages": [(doc_id, page_no)],
    }


def test_validation_reports_unknown_pages() -> None:
    errors = validate_questions(
        [question("q1", "doc", 2)], [page("doc", 1)]
    )

    assert any("unknown page" in error for error in errors)


def test_summary_pairs_each_cell_with_the_baseline() -> None:
    rows = []
    for qid, baseline, cell in (("q1", 0.0, 1.0), ("q2", 0.0, 0.0)):
        for name, score in (("page_only", baseline), ("cell", cell)):
            rows.append(
                {
                    "cell": name,
                    "qid": qid,
                    "split": "T",
                    "mode": "hybrid",
                    "category": "concept",
                    "stratum": "short",
                    "mrr": score,
                    "hit@3": bool(score),
                    "hit@5": bool(score),
                    "ndcg@5": score,
                    "context_tokens@5": 10,
                }
            )

    summary = summarise(
        rows,
        {"page_only": {"chunks": 10}, "cell": {"chunks": 5}},
        ks=(5,),
        modes=("hybrid",),
    )

    comparison = summary["comparisons"][0]
    assert comparison["cell"] == "cell"
    assert comparison["metrics"]["ndcg@5"]["mean_delta"] == 0.5
    assert comparison["metrics"]["ndcg@5"]["wins"] == 1
    assert comparison["metrics"]["ndcg@5"]["ties"] == 1


def test_mcnemar_matches_the_exact_binomial_example() -> None:
    assert mcnemar_p(0, 5) == 0.0625
    assert mcnemar_p(0, 0) == 1.0


def test_bootstrap_interval_contains_the_sample_mean() -> None:
    values = [0.0, 0.5, 1.0, 1.0, 0.0]
    low, high = bootstrap_ci(values, samples=500, seed=1)

    assert low <= sum(values) / len(values) <= high
