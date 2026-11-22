from verifiable_tutor.practice.grading import (
    grade_multiple_choice,
    grade_single_choice,
    grade_true_false,
)


def test_grade_single_choice_correct() -> None:
    assert grade_single_choice("B", "B") is True


def test_grade_single_choice_wrong() -> None:
    assert grade_single_choice("A", "B") is False


def test_grade_single_choice_ignores_case_and_whitespace() -> None:
    assert grade_single_choice("  b ", "B") is True


def test_grade_multiple_choice_exact_set() -> None:
    assert grade_multiple_choice(["A", "B"], ["B", "A"]) is True


def test_grade_multiple_choice_wrong_subset() -> None:
    assert grade_multiple_choice(["A"], ["A", "B"]) is False


def test_grade_multiple_choice_extra_selection() -> None:
    assert grade_multiple_choice(["A", "B", "C"], ["A", "B"]) is False


def test_grade_true_false_correct() -> None:
    assert grade_true_false(True, True) is True


def test_grade_true_false_wrong() -> None:
    assert grade_true_false(False, True) is False
