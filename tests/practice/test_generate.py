from verifiable_tutor.orchestrator.runner import AgentEvent
from verifiable_tutor.practice.generate import generate_practice

JSON_QUESTIONS = (
    '[{"type": "single-choice", "question": "What is MPI? [ref_1]", '
    '"choices": ["A. X", "B. Y"], "reference_answer": "B", '
    '"scoring_points": ["defines MPI"], "max_score": 1}]'
)


class FakeRunner:
    def __init__(self, text: str = "", sources: list[dict] | None = None) -> None:
        self._text = text
        self._sources = sources or []
        self.messages: list[dict] | None = None

    def run(self, messages, **kwargs):
        self.messages = messages
        yield AgentEvent(
            kind="turn_end",
            data={"text": self._text, "sources": self._sources},
        )


def test_generate_practice_parses_structured_questions() -> None:
    runner = FakeRunner(text=JSON_QUESTIONS, sources=[{"marker": 1}])

    questions, sources = generate_practice("FlashAttention", runner, adapter=None)

    assert len(questions) == 1
    question = questions[0]
    assert question.type == "single-choice"
    assert question.question == "What is MPI? [ref_1]"
    assert question.choices == ["A. X", "B. Y"]
    assert question.reference_answer == "B"
    assert question.scoring_points == ["defines MPI"]
    assert question.max_score == 1.0
    assert sources == [{"marker": 1}]


def test_generate_practice_strips_reasoning_before_the_json() -> None:
    runner = FakeRunner(text="I'll search the corpus.\n\n" + JSON_QUESTIONS)

    questions, _ = generate_practice("FlashAttention", runner, adapter=None)

    assert len(questions) == 1


def test_generate_practice_returns_empty_when_no_json() -> None:
    runner = FakeRunner(text="no questions here")

    questions, _ = generate_practice("FlashAttention", runner, adapter=None)

    assert questions == []


def test_generate_practice_uses_the_practice_prompt_and_topic() -> None:
    runner = FakeRunner(text=JSON_QUESTIONS)

    generate_practice("FlashAttention", runner, adapter=None)

    assert runner.messages[0]["role"] == "system"
    assert "self-test generator for the CSIT6000V course" in runner.messages[0]["content"]
    assert runner.messages[1]["role"] == "user"
    assert runner.messages[1]["content"] == (
        "Generate self-test questions on the topic: FlashAttention"
    )

JSON_WITH_ANSWER = (
    '[{"type": "single-choice", "answer": "B. Y", "question": "What is MPI? [ref_1]", '
    '"choices": ["A. X", "B. Y"], "reference_answer": "The second option, B. Y, is right.", '
    '"scoring_points": ["defines MPI"], "max_score": 1}]'
)


def test_generate_practice_keeps_the_exact_choice_answer() -> None:
    runner = FakeRunner(text=JSON_WITH_ANSWER)

    questions, _ = generate_practice("FlashAttention", runner, adapter=None)

    assert questions[0].answer == "B. Y"

