import base64
import json
from pathlib import Path

import httpx
import pytest

from verifiable_tutor.llm.adapter import CapabilityError, ModelAdapter, SpeechResult
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}

AUDIO_BYTES = b"RIFF$\x00\x00\x00WAVEfmt "


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = False
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def tts_response(audio: bytes = AUDIO_BYTES, model: str = "mimo-v2.5-tts") -> dict:
    return {
        "id": "tts-test",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "audio": {
                        "data": base64.b64encode(audio).decode("ascii"),
                        "transcript": None,
                        "expires_at": None,
                    },
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 10},
    }


def test_speak_uses_mimo_tts_and_decodes_audio() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=tts_response())

    result = make_adapter(handler).speak("Today we look at the roofline model.")

    assert isinstance(result, SpeechResult)
    assert result.audio == AUDIO_BYTES
    assert result.format == "wav"
    assert result.voice == "mimo_default"
    assert result.model == "mimo-v2.5-tts"

    request = captured[0]
    assert request.url.host == "api.xiaomimimo.com"
    assert request.url.path == "/v1/chat/completions"
    body = json.loads(request.content)
    assert body["model"] == "mimo-v2.5-tts"
    assert body["audio"] == {"format": "wav", "voice": "mimo_default"}
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1] == {"role": "assistant", "content": "Today we look at the roofline model."}


def test_speak_passes_voice_format_and_instructions() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=tts_response(model="mimo-v2.5-tts"))

    result = make_adapter(handler).speak(
        "Roofline 模型把计算和访存放在同一张图上。",
        voice="茉莉",
        format="mp3",
        instructions="Warm, clear, steady teaching pace.",
    )

    body = json.loads(captured[0].content)
    assert body["audio"] == {"format": "mp3", "voice": "茉莉"}
    assert body["messages"][0]["content"] == "Warm, clear, steady teaching pace."
    assert result.format == "mp3"
    assert result.voice == "茉莉"


def test_speak_rejects_unsupported_format() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected")

    with pytest.raises(CapabilityError, match="flac"):
        make_adapter(handler).speak("hello", format="flac")
