from types import SimpleNamespace

from verifiable_tutor.practice.grading import (
    grade_answer,
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


class FakeAdapter:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[list[dict]] = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return SimpleNamespace(text=self._text)


def test_grade_answer_parses_the_model_json() -> None:
    adapter = FakeAdapter(
        '{"score": 2, "max_score": 3, "explanation": "two of three points"}'
    )

    result = grade_answer(
        "Q", "A", "R", ["p1", "p2", "p3"], 3.0, [], adapter
    )

    assert result.score == 2.0
    assert result.max_score == 3.0
    assert result.explanation == "two of three points"


def test_grade_answer_strips_markdown_fences() -> None:
    adapter = FakeAdapter(
        '```json\n{"score": 1, "max_score": 1, "explanation": "ok"}\n```'
    )

    result = grade_answer("Q", "A", "R", ["p1"], 1.0, [], adapter)

    assert result.score == 1.0


def test_grade_answer_sends_question_answer_and_points() -> None:
    adapter = FakeAdapter('{"score": 0, "max_score": 1, "explanation": "no"}')

    grade_answer(
        "What is MPI?", "OpenMP", "MPI is message passing", ["define MPI"], 1.0, [], adapter
    )

    user = adapter.calls[0][1]["content"]
    assert "What is MPI?" in user
    assert "OpenMP" in user
    assert "MPI is message passing" in user
    assert "define MPI" in user


def test_grade_answer_sends_course_sources() -> None:
    adapter = FakeAdapter('{"score": 1, "max_score": 1, "explanation": "ok [ref_1]"}')

    grade_answer(
        "Q",
        "A",
        "R",
        ["p1"],
        1.0,
        [{"marker": 1, "summary": "Tutorial 4 page 39"}],
        adapter,
    )

    user = adapter.calls[0][1]["content"]
    assert "[ref_1]" in user
    assert "Tutorial 4 page 39" in user
