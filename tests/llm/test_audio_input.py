import json
from pathlib import Path

import httpx
import pytest

from verifiable_tutor.llm.adapter import CapabilityError, ModelAdapter
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = False
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def completion_json(model: str = "mimo-v2.6-flash") -> dict:
    return {
        "id": "chatcmpl-audio",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "a short tone"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 3, "total_tokens": 23},
    }


def audio_messages() -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": {"data": "data:audio/wav;base64,AAAA"}},
                {"type": "text", "text": "What is in this audio?"},
            ],
        }
    ]


def test_audio_input_is_rejected_when_selected_provider_is_deepseek() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected for a DeepSeek audio request")

    with pytest.raises(CapabilityError, match="audio"):
        make_adapter(handler).chat(audio_messages())


def test_audio_input_uses_selected_mimo_flash_model() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json("mimo-v2.6-flash"))

    result = make_adapter(handler).chat(
        audio_messages(), provider="mimo", tier="flash"
    )

    assert result.provider == "mimo"
    assert result.model == "mimo-v2.6-flash"
    assert result.text == "a short tone"

    body = json.loads(captured[0].content)
    assert captured[0].url.host == "api.xiaomimimo.com"
    assert captured[0].url.path == "/v1/chat/completions"
    assert body["model"] == "mimo-v2.6-flash"
    content = body["messages"][0]["content"]
    assert content[0]["type"] == "input_audio"
    assert content[0]["input_audio"]["data"].startswith("data:audio/wav;base64,")


def test_audio_input_uses_selected_mimo_pro_model() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completion_json("mimo-v2.6-pro"))

    result = make_adapter(handler).chat(audio_messages(), provider="mimo", tier="pro")

    assert result.model == "mimo-v2.6-pro"
    body = json.loads(captured[0].content)
    assert body["model"] == "mimo-v2.6-pro"
