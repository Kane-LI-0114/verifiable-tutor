import base64
import json
from pathlib import Path

import httpx
import pytest

from verifiable_tutor.llm.adapter import (
    CapabilityError,
    ModelAdapter,
    TranscriptResult,
)
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = False
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def asr_response(transcript: str = "hello world", seconds: int = 2) -> dict:
    return {
        "id": "asr-test",
        "object": "chat.completion",
        "created": 1,
        "model": "mimo-v2.5-asr",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": transcript},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 3,
            "total_tokens": 13,
            "seconds": seconds,
            "prompt_tokens_details": {"audio_tokens": 5},
        },
    }


def test_transcribe_uses_mimo_asr_and_data_url() -> None:
    captured: list[httpx.Request] = []
    audio = b"RIFF....WAVEfmt "

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=asr_response())

    result = make_adapter(handler).transcribe(audio)

    assert isinstance(result, TranscriptResult)
    assert result.text == "hello world"
    assert result.model == "mimo-v2.5-asr"
    assert result.seconds == 2

    body = json.loads(captured[0].content)
    assert captured[0].url.host == "api.xiaomimimo.com"
    assert captured[0].url.path == "/v1/chat/completions"
    assert body["model"] == "mimo-v2.5-asr"
    part = body["messages"][0]["content"][0]
    assert part["type"] == "input_audio"
    expected = base64.b64encode(audio).decode("ascii")
    assert part["input_audio"]["data"] == f"data:audio/wav;base64,{expected}"
    assert body["asr_options"] == {"language": "auto"}


def test_transcribe_passes_language_to_asr_options() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=asr_response(transcript="你好"))

    result = make_adapter(handler).transcribe(b"abc", mime="audio/mpeg", language="zh")

    body = json.loads(captured[0].content)
    assert body["asr_options"] == {"language": "zh"}
    assert body["messages"][0]["content"][0]["input_audio"]["data"].startswith(
        "data:audio/mpeg;base64,"
    )
    assert result.text == "你好"


def test_transcribe_rejects_unsupported_mime() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected")

    with pytest.raises(CapabilityError, match="audio/webm"):
        make_adapter(handler).transcribe(b"abc", mime="audio/webm")


def test_transcribe_rejects_audio_above_base64_limit() -> None:
    # base64 length is 4 * ceil(n / 3); pick n so that the encoded string
    # exceeds the 10 MiB ASR limit.
    audio = b"\x00" * 7_900_000

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected")

    with pytest.raises(CapabilityError, match="10"):
        make_adapter(handler).transcribe(audio)
