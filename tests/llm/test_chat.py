import json
from pathlib import Path

import httpx
import pytest

from verifiable_tutor.llm.adapter import (
    CapabilityError,
    ChatResult,
    ModelAdapter,
    ModelSelectionError,
    ProviderAPIError,
)
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"

ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def completion_json(
    *,
    content: str | None = "hello",
    reasoning: str | None = None,
    tool_calls: list[dict] | None = None,
    finish_reason: str = "stop",
    model: str = "deepseek-flash",
) -> dict:
    message: dict = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def error_json(message: str = "bad key") -> dict:
    return {"error": {"message": message, "type": "authentication_error", "code": "auth"}}


def test_deepseek_chat_uses_flash_and_normalizes_response() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json(content="pong"))

    result = make_adapter(handler).chat(
        [{"role": "user", "content": "ping"}], max_output_tokens=128
    )

    assert isinstance(result, ChatResult)
    assert result.provider == "deepseek"
    assert result.model == "deepseek-flash"
    assert result.text == "pong"
    assert result.finish_reason == "stop"
    assert result.usage["total_tokens"] == 15

    body = json.loads(captured[0].content)
    assert captured[0].url.path == "/chat/completions"
    assert captured[0].headers["authorization"] == "Bearer sk-deepseek-test"
    assert body["model"] == "deepseek-flash"
    assert body["max_tokens"] == 128
    assert body["reasoning_effort"] == "none"
    assert body["temperature"] == 0.0
    assert body["top_p"] == 1.0


def test_deepseek_high_thinking_omits_sampling_knobs() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json(reasoning="thinking hard"))

    result = make_adapter(handler).chat(
        [{"role": "user", "content": "hard question"}], thinking="high"
    )

    body = json.loads(captured[0].content)
    assert body["reasoning_effort"] == "high"
    assert "temperature" not in body
    assert "top_p" not in body
    assert result.reasoning == "thinking hard"


def test_mimo_chat_uses_max_completion_tokens_and_disabled_thinking() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json(model="mimo-v2.6-flash"))

    result = make_adapter(handler).chat(
        [{"role": "user", "content": "ping"}], provider="mimo", tier="flash", max_output_tokens=64
    )

    assert result.provider == "mimo"
    assert result.model == "mimo-v2.6-flash"
    body = json.loads(captured[0].content)
    assert body["max_completion_tokens"] == 64
    assert "max_tokens" not in body
    assert body["thinking"] == {"type": "disabled"}
    assert body["temperature"] == 0.0


def test_mimo_pro_with_thinking_enabled_ignores_sampling() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json(model="mimo-v2.6-pro", reasoning="why"))

    result = make_adapter(handler).chat(
        [{"role": "user", "content": "hard"}], provider="mimo", tier="pro", thinking="high"
    )

    body = json.loads(captured[0].content)
    assert result.model == "mimo-v2.6-pro"
    assert body["thinking"] == {"type": "enabled"}
    assert "temperature" not in body
    assert "top_p" not in body


def test_tool_call_is_normalized_and_thinking_forced_off() -> None:
    captured: list[httpx.Request] = []
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "search_course", "arguments": '{"query": "roofline"}'},
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=completion_json(
                content="",
                reasoning="need a tool",
                tool_calls=tool_calls,
                finish_reason="tool_calls",
                model="mimo-v2.6-flash",
            ),
        )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_course",
                "description": "Search the course corpus",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]
    result = make_adapter(handler).chat(
        [{"role": "user", "content": "find roofline"}],
        provider="mimo",
        tier="flash",
        thinking="high",
        tools=tools,
    )

    body = json.loads(captured[0].content)
    assert body["thinking"] == {"type": "disabled"}
    assert body["tool_choice"] == "auto"
    assert body["tools"] == tools
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[0].name == "search_course"
    assert json.loads(result.tool_calls[0].arguments) == {"query": "roofline"}
    assert result.finish_reason == "tool_calls"


def test_fallback_provider_used_after_retryable_error() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        if request.url.host == "api.deepseek.com":
            return httpx.Response(429, json=error_json("rate limited"))
        return httpx.Response(200, json=completion_json(model="mimo-v2.6-flash"))

    result = make_adapter(handler).chat([{"role": "user", "content": "ping"}])

    assert result.provider == "mimo"
    assert result.model == "mimo-v2.6-flash"
    assert seen == ["api.deepseek.com", "api.xiaomimimo.com"]


def test_non_retryable_api_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json=error_json("bad key"))

    with pytest.raises(ProviderAPIError) as excinfo:
        make_adapter(handler).chat([{"role": "user", "content": "ping"}])

    assert excinfo.value.status == 401


def test_unknown_tier_raises_model_selection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json=completion_json())

    with pytest.raises(ModelSelectionError):
        make_adapter(handler).chat(
            [{"role": "user", "content": "ping"}], provider="deepseek", tier="pro"
        )


def test_image_block_is_kept_for_vision_provider() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json(content="a red square"))

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "what color"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
            ],
        }
    ]
    result = make_adapter(handler).chat(messages)

    body = json.loads(captured[0].content)
    assert isinstance(body["messages"][0]["content"], list)
    assert body["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png")
    assert result.text == "a red square"


def test_image_block_is_rejected_when_provider_lacks_vision() -> None:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.providers["deepseek"].supports.image = False
    adapter = ModelAdapter(resolved, transport=httpx.MockTransport(lambda r: httpx.Response(200)))

    with pytest.raises(CapabilityError):
        adapter.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}
                    ],
                }
            ]
        )
