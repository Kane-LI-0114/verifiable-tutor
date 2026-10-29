import json
from pathlib import Path

import httpx

from verifiable_tutor.llm.adapter import ModelAdapter, StreamEvent, ToolCallDelta
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = False
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def sse_response(chunks: list[dict]) -> httpx.Response:
    body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)


def chunk(
    *,
    model: str,
    choices: list[dict],
    usage: dict | None = None,
) -> dict:
    payload = {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": model,
        "choices": choices,
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


def delta(**kwargs) -> dict:
    return {"index": 0, "delta": kwargs, "finish_reason": None}


def test_deepseek_stream_emits_reasoning_text_finish_and_usage() -> None:
    captured: list[httpx.Request] = []
    chunks = [
        chunk(model="deepseek-flash", choices=[delta(reasoning_content="think ")]),
        chunk(model="deepseek-flash", choices=[delta(content="hello")]),
        chunk(model="deepseek-flash", choices=[delta(content="!")]),
        chunk(
            model="deepseek-flash",
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return sse_response(chunks)

    events = list(make_adapter(handler).chat_stream([{"role": "user", "content": "ping"}]))

    assert [event.kind for event in events] == ["reasoning", "text", "text", "finish", "usage"]
    assert events[0].text == "think "
    assert events[1].text + events[2].text == "hello!"
    assert events[3].finish_reason == "stop"
    assert events[4].usage["total_tokens"] == 8

    body = json.loads(captured[0].content)
    assert body["stream"] is True
    assert body["model"] == "deepseek-flash"
    assert body["reasoning_effort"] == "none"


def test_mimo_stream_handles_empty_choices_usage_chunk() -> None:
    chunks = [
        chunk(model="mimo-v2.6-flash", choices=[delta(content="hi")]),
        chunk(
            model="mimo-v2.6-flash",
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
        ),
        chunk(
            model="mimo-v2.6-flash",
            choices=[],
            usage={"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return sse_response(chunks)

    events = list(
        make_adapter(handler).chat_stream(
            [{"role": "user", "content": "ping"}], provider="mimo", tier="flash"
        )
    )

    assert [event.kind for event in events] == ["text", "finish", "usage"]
    assert events[0].text == "hi"
    assert events[2].usage["total_tokens"] == 3


def test_tool_call_fragments_are_streamed() -> None:
    chunks = [
        chunk(
            model="mimo-v2.6-flash",
            choices=[
                delta(
                    tool_calls=[
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "search_course", "arguments": '{"query":'},
                        }
                    ]
                )
            ],
        ),
        chunk(
            model="mimo-v2.6-flash",
            choices=[
                delta(tool_calls=[{"index": 0, "function": {"arguments": '"roofline"}'}}])
            ],
        ),
        chunk(
            model="mimo-v2.6-flash",
            choices=[{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return sse_response(chunks)

    events = list(
        make_adapter(handler).chat_stream(
            [{"role": "user", "content": "find roofline"}], provider="mimo", tier="flash"
        )
    )

    tool_events = [event for event in events if event.kind == "tool_call"]
    assert len(tool_events) == 2
    assert isinstance(tool_events[0].tool_call, ToolCallDelta)
    assert tool_events[0].tool_call.id == "call_1"
    assert tool_events[0].tool_call.name == "search_course"
    arguments = "".join(
        event.tool_call.arguments_delta for event in tool_events if event.tool_call is not None
    )
    assert arguments == '{"query":"roofline"}'
    assert events[-1].kind == "finish"
    assert events[-1].finish_reason == "tool_calls"


def test_stream_retryable_error_retries_same_model() -> None:
    calls: list[httpx.Request] = []
    chunks = [
        chunk(model="deepseek-flash", choices=[delta(content="hello")]),
        chunk(
            model="deepseek-flash",
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, json={"error": {"message": "busy"}})
        return sse_response(chunks)

    events = list(
        make_adapter(handler).chat_stream(
            [{"role": "user", "content": "ping"}], max_output_tokens=16
        )
    )

    assert [event.kind for event in events] == ["text", "finish"]
    assert len(calls) == 2
