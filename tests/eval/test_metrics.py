import pytest

from verifiable_tutor.eval import metrics


def test_question_validity_rate() -> None:
    annotations = [
        {"valid": True},
        {"valid": True},
        {"valid": False},
        {"valid": True},
    ]
    assert metrics.question_validity_rate(annotations) == 0.75


def test_question_validity_rate_empty() -> None:
    assert metrics.question_validity_rate([]) == 0.0


def test_knowledge_point_coverage() -> None:
    annotations = [
        {"knowledge_points": ["a", "b"]},
        {"knowledge_points": ["b", "c"]},
        {"knowledge_points": ["a"]},
    ]
    # distinct covered = {a, b, c} = 3, expected = 4
    assert metrics.knowledge_point_coverage(annotations, 4) == 0.75


def test_knowledge_point_coverage_zero_expected() -> None:
    assert metrics.knowledge_point_coverage([], 0) == 0.0


def test_reference_answer_verifiability() -> None:
    questions = [
        {"reference_verified": True},
        {"reference_verified": True},
        {"reference_verified": False},
        {"reference_verified": None},
    ]
    # applicable = 3, verified = 2
    assert metrics.reference_answer_verifiability(questions) == pytest.approx(2 / 3)


def test_citation_validity() -> None:
    questions = [
        {"citation_verified": True},
        {"citation_verified": True},
        {"citation_verified": False},
        {"citation_verified": None},
    ]
    assert metrics.citation_validity(questions) == pytest.approx(2 / 3)


def test_citation_validity_undefined_when_no_citations() -> None:
    assert metrics.citation_validity([{"citation_verified": None}]) is None


def test_rq2b_agreement_metrics() -> None:
    ground_truth = [
        {"question_id": "q1", "variant": "correct", "score": 5},
        {"question_id": "q1", "variant": "wrong", "score": 0},
        {"question_id": "q2", "variant": "partial", "score": 2},
        {"question_id": "q2", "variant": "correct", "score": 3},
    ]
    grades = [
        {"question_id": "q1", "variant": "correct", "score": 5},
        {"question_id": "q1", "variant": "wrong", "score": 5},
        {"question_id": "q2", "variant": "partial", "score": 1},
        {"question_id": "q2", "variant": "correct", "score": 0},
    ]
    max_scores = {"q1": 5, "q2": 3}

    assert metrics.exact_match_rate(grades, ground_truth) == 0.25
    assert metrics.within_one_point_agreement(grades, ground_truth) == 0.5
    # (0 + 1 + 1/3 + 1) / 4
    assert metrics.normalized_mae(grades, ground_truth, max_scores) == pytest.approx(
        (0 + 1 + 1 / 3 + 1) / 4
    )
    # wrong answers: only q1/wrong; its grade == max (5) -> false pass
    assert metrics.false_pass_rate(grades, ground_truth, max_scores) == 1.0
    # correct answers: q1/correct and q2/correct; q2/correct grade == 0 -> 1 of 2
    assert metrics.false_fail_rate(grades, ground_truth, max_scores) == 0.5
