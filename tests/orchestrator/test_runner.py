"""The LangGraph tool loop: dispatch, budget, events, and failure behavior."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from verifiable_tutor.llm.adapter import StreamEvent, ToolCallDelta
from verifiable_tutor.orchestrator.builtin_tools import build_tool_registry
from verifiable_tutor.orchestrator.runner import (
    AgentRunner,
    FALLBACK_TEXT,
)


class FakeSettings:
    agent_web_tools_enabled = True
    agent_max_model_calls = 5
    agent_max_tool_calls = 8
    agent_recursion_limit = 16
    agent_max_tool_output_chars = 4000


class FakeRetriever:
    def __init__(self, chunks=None):
        self.chunks = chunks or []

    def search(self, plan, *, k=8):
        return SimpleNamespace(chunks=self.chunks[:k], lexical=True, dense=False, plan=plan)


class FakeStore:
    def page_chunks(self, doc_id: str, page_no: int):
        return []


def chunk():
    return {
        "id": "Tutorial_2:p008:c00",
        "doc_id": "Tutorial_2",
        "page_no": 8,
        "section": "Collectives",
        "text": "MPI_Allreduce reduces a value across all ranks.",
    }


class ScriptAdapter:
    """A model adapter fake scripted per call."""

    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls: list[dict] = []

    def chat_stream(self, messages, **kwargs):
        self.calls.append({"messages": [dict(message) for message in messages], "kwargs": kwargs})
        events = self.scripts.pop(0) if self.scripts else _text_script("done")
        for event in events:
            yield event


def _text_script(text: str):
    return [StreamEvent(kind="text", text=text), StreamEvent(kind="finish", finish_reason="stop")]


def _tool_script(name="search_course", arguments='{"query":"MPI_Allreduce","k":2}', call_id="call_1"):
    return [
        StreamEvent(
            kind="tool_call",
            tool_call=ToolCallDelta(
                index=0, id=call_id, name=name, arguments_delta=arguments
            ),
        ),
        StreamEvent(kind="finish", finish_reason="tool_calls"),
    ]


def runner(settings=None, retriever=None):
    settings = settings or FakeSettings()
    return AgentRunner(
        settings=settings,
        registry=build_tool_registry(settings=settings),
        retriever=retriever or FakeRetriever([chunk()]),
        store=FakeStore(),
    )


def _run(adapter, *, settings=None, retriever=None, messages=None, provider="deepseek"):
    return list(
        runner(settings=settings, retriever=retriever).run(
            messages or [{"role": "user", "content": "What is MPI_Allreduce?"}],
            adapter=adapter,
            provider=provider,
            tier="flash",
        )
    )


def test_agent_executes_a_tool_and_feeds_the_result_back():
    adapter = ScriptAdapter([_tool_script(), _text_script("Allreduce sums across ranks.")])

    events = _run(adapter)

    kinds = [event.kind for event in events]
    assert kinds[0] == "model_start"
    assert "tool_start" in kinds
    assert "tool_end" in kinds
    assert kinds[-1] == "turn_end"

    assert len(adapter.calls) == 2
    assert adapter.calls[0]["kwargs"]["tools"]
    assert adapter.calls[1]["kwargs"]["tools"]
    second_messages = adapter.calls[1]["messages"]
    tool_messages = [message for message in second_messages if message["role"] == "tool"]
    assert len(tool_messages) == 1
    payload = json.loads(tool_messages[0]["content"])
    assert payload["source"] == "course"
    assert payload["chunks"][0]["doc_id"] == "Tutorial_2"

    turn = events[-1].data
    assert turn["text"] == "Allreduce sums across ranks."
    assert turn["tool_calls"][0]["name"] == "search_course"
    assert turn["tool_calls"][0]["arguments"] == {"query": "MPI_Allreduce", "k": 2}
    assert turn["tool_calls"][0]["status"] == "done"
    assert turn["tool_calls"][0]["tool_call_id"] == "call_1"
    assert turn["model_calls"] == 2


def test_tool_events_name_their_work_chain_step():
    adapter = ScriptAdapter([_tool_script(), _text_script("Answer.")])

    events = _run(adapter)

    tool_start = next(event for event in events if event.kind == "tool_start")
    tool_end = next(event for event in events if event.kind == "tool_end")
    assert tool_start.data["step"] == "retrieve"
    assert tool_end.data["step"] == "retrieve"


def test_both_providers_replay_reasoning_content_before_the_tool_result():
    for provider in ("deepseek", "mimo"):
        first = [
            StreamEvent(kind="reasoning", text="I should search the course."),
            *_tool_script(),
        ]
        adapter = ScriptAdapter([first, _text_script("Answer.")])

        _run(adapter, provider=provider)

        assistant = adapter.calls[1]["messages"][-2]
        assert assistant["role"] == "assistant"
        assert assistant["reasoning_content"] == "I should search the course."
        tool = adapter.calls[1]["messages"][-1]
        assert tool["role"] == "tool"


def test_unknown_tool_is_reported_to_the_model_and_the_loop_continues():
    adapter = ScriptAdapter(
        [
            _tool_script(name="delete_everything", arguments="{}", call_id="call_x"),
            _text_script("I cannot do that."),
        ]
    )

    events = _run(adapter)

    tool_messages = [
        message for message in adapter.calls[1]["messages"] if message["role"] == "tool"
    ]
    assert tool_messages and "unknown tool" in tool_messages[0]["content"]
    turn = events[-1].data
    assert turn["tool_calls"][0]["status"] == "failed"
    assert turn["text"] == "I cannot do that."


def test_invalid_arguments_become_a_failed_tool_result():
    adapter = ScriptAdapter(
        [
            _tool_script(arguments="{not json"),
            _text_script("Let me answer from the course material."),
        ]
    )

    events = _run(adapter)

    turn = events[-1].data
    assert turn["tool_calls"][0]["status"] == "failed"
    tool_message = [
        message for message in adapter.calls[1]["messages"] if message["role"] == "tool"
    ][0]
    assert "invalid arguments" in tool_message["content"]


def test_the_last_allowed_call_has_no_tools():
    class TwoCalls(FakeSettings):
        agent_max_model_calls = 2

    adapter = ScriptAdapter([_tool_script(), _text_script("final answer")])

    events = _run(adapter, settings=TwoCalls())

    assert len(adapter.calls) == 2
    assert adapter.calls[0]["kwargs"]["tools"]
    assert adapter.calls[1]["kwargs"]["tools"] is None
    assert events[-1].data["text"] == "final answer"
    assert events[-1].data["model_calls"] == 2


def test_the_tool_budget_fails_extra_calls_and_forces_the_final_answer():
    class OneTool(FakeSettings):
        agent_max_model_calls = 3
        agent_max_tool_calls = 1

    two_calls = [
        StreamEvent(
            kind="tool_call",
            tool_call=ToolCallDelta(
                index=0, id="call_1", name="search_course", arguments_delta='{"query":"MPI"}'
            ),
        ),
        StreamEvent(
            kind="tool_call",
            tool_call=ToolCallDelta(
                index=1, id="call_2", name="search_course", arguments_delta='{"query":"CUDA"}'
            ),
        ),
        StreamEvent(kind="finish", finish_reason="tool_calls"),
    ]
    adapter = ScriptAdapter([two_calls, _text_script("final")])

    events = _run(adapter, settings=OneTool())

    turn = events[-1].data
    statuses = [call["status"] for call in turn["tool_calls"]]
    assert statuses == ["done", "failed"]
    assert adapter.calls[-1]["kwargs"]["tools"] is None


def test_usage_is_accumulated_across_calls():
    adapter = ScriptAdapter(
        [
            [
                StreamEvent(kind="text", text="a"),
                StreamEvent(
                    kind="usage",
                    usage={"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
                ),
                StreamEvent(kind="finish", finish_reason="stop"),
            ]
        ]
    )

    events = _run(adapter)

    assert events[-1].data["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 4,
        "total_tokens": 14,
    }


def test_mid_stream_failure_propagates_to_the_caller():
    class Boom:
        def __init__(self):
            self.calls = 0

        def chat_stream(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                yield StreamEvent(kind="text", text="partial")
                raise RuntimeError("provider died")
            yield StreamEvent(kind="finish", finish_reason="stop")

    with pytest.raises(RuntimeError, match="provider died"):
        _run(Boom())


def test_turn_end_carries_the_turn_sources():
    adapter = ScriptAdapter([_tool_script(), _text_script("Answer.")])

    events = _run(adapter)

    turn = events[-1].data
    assert turn["sources"] == [
        {
            "marker": 1,
            "kind": "course",
            "title": "Tutorial_2",
            "summary": "MPI_Allreduce reduces a value across all ranks.",
            "doc_id": "Tutorial_2",
            "page_no": 8,
            "url": None,
            "chunk_id": "Tutorial_2:p008:c00",
        }
    ]


def test_sources_event_follows_the_tool_result():
    adapter = ScriptAdapter([_tool_script(), _text_script("Answer.")])

    events = _run(adapter)

    kinds = [event.kind for event in events]
    assert kinds.index("tool_end") < kinds.index("sources")
    sources = [event for event in events if event.kind == "sources"]
    assert len(sources) == 1
    assert sources[0].data["sources"][0]["marker"] == 1


def test_an_empty_final_answer_uses_the_fallback_copy():
    adapter = ScriptAdapter(
        [[StreamEvent(kind="finish", finish_reason="stop")]]
    )

    events = _run(adapter)

    assert events[-1].data["text"] == FALLBACK_TEXT
