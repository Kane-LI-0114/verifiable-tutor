from verifiable_tutor.orchestrator.runner import AgentEvent
from verifiable_tutor.practice.generate import generate_practice


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


def test_generate_practice_uses_the_practice_prompt_and_topic() -> None:
    runner = FakeRunner(text="Q1: ...", sources=[{"marker": 1}])

    text, sources = generate_practice("FlashAttention", runner, adapter=None)

    assert text == "Q1: ..."
    assert sources == [{"marker": 1}]
    assert runner.messages[0]["role"] == "system"
    assert "self-test generator for the CSIT6000V course" in runner.messages[0]["content"]
    assert runner.messages[1]["role"] == "user"
    assert runner.messages[1]["content"] == (
        "Generate self-test questions on the topic: FlashAttention"
    )


def test_generate_practice_returns_empty_when_the_runner_has_no_turn_end() -> None:
    class EmptyRunner:
        def run(self, messages, **kwargs):
            return iter(())

    text, sources = generate_practice("FlashAttention", EmptyRunner(), adapter=None)

    assert text == ""
    assert sources == []
