import json
from pathlib import Path

import httpx
import pytest

from verifiable_tutor.llm.adapter import ModelAdapter
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


def make_adapter(handler, cache_root: Path, *, enabled: bool = True) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = enabled
    return ModelAdapter(
        resolved, transport=httpx.MockTransport(handler), cache_root=cache_root
    )


def completion_json(content: str = "pong") -> dict:
    return {
        "id": "chatcmpl-cache",
        "object": "chat.completion",
        "created": 1,
        "model": "deepseek-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
    }


def test_chat_second_identical_request_uses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=completion_json())

    adapter = make_adapter(handler, tmp_path)
    first = adapter.chat([{"role": "user", "content": "ping"}], max_output_tokens=16)
    second = adapter.chat([{"role": "user", "content": "ping"}], max_output_tokens=16)

    assert first == second
    assert len(calls) == 1
    assert any(tmp_path.rglob("*.json"))


def test_chat_different_messages_miss_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=completion_json())

    adapter = make_adapter(handler, tmp_path)
    adapter.chat([{"role": "user", "content": "ping"}], max_output_tokens=16)
    adapter.chat([{"role": "user", "content": "pong"}], max_output_tokens=16)

    assert len(calls) == 2


def test_chat_use_cache_false_bypasses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=completion_json())

    adapter = make_adapter(handler, tmp_path)
    adapter.chat([{"role": "user", "content": "ping"}], max_output_tokens=16)
    adapter.chat(
        [{"role": "user", "content": "ping"}], max_output_tokens=16, use_cache=False
    )

    assert len(calls) == 2


def test_cache_disabled_writes_nothing(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=completion_json())

    adapter = make_adapter(handler, tmp_path, enabled=False)
    adapter.chat([{"role": "user", "content": "ping"}], max_output_tokens=16)
    adapter.chat([{"role": "user", "content": "ping"}], max_output_tokens=16)

    assert len(calls) == 2
    assert not list(tmp_path.rglob("*.json"))


def test_cache_dir_is_resolved_from_base_dir(tmp_path: Path) -> None:
    resolved = load_model_config(REAL_CONFIG, env=ENV, base_dir=tmp_path)

    assert resolved.cache_dir == tmp_path / "data" / "caches" / "model"
    assert resolved.cache_dir.is_absolute()


def asr_response(transcript: str = "hello") -> dict:
    return {
        "id": "asr-cache",
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
        "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4, "seconds": 1},
    }


def tts_response() -> dict:
    import base64

    return {
        "id": "tts-cache",
        "object": "chat.completion",
        "created": 1,
        "model": "mimo-v2.5-tts",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "audio": {"data": base64.b64encode(b"RIFF-audio").decode("ascii")},
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 0, "total_tokens": 3},
    }


def search_response() -> dict:
    return {"results": [{"title": "A", "url": "https://example.com/a", "content": "body"}]}


def test_transcribe_second_identical_audio_uses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=asr_response())

    adapter = make_adapter(handler, tmp_path)
    first = adapter.transcribe(b"RIFF-audio", language="auto")
    second = adapter.transcribe(b"RIFF-audio", language="auto")

    assert first == second
    assert len(calls) == 1


def test_transcribe_different_language_misses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=asr_response())

    adapter = make_adapter(handler, tmp_path)
    adapter.transcribe(b"RIFF-audio", language="auto")
    adapter.transcribe(b"RIFF-audio", language="zh")

    assert len(calls) == 2


def test_speak_second_identical_request_uses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=tts_response())

    adapter = make_adapter(handler, tmp_path)
    first = adapter.speak("hello", voice="mimo_default", format="wav")
    second = adapter.speak("hello", voice="mimo_default", format="wav")

    assert first == second
    assert first.audio == b"RIFF-audio"
    assert len(calls) == 1


def test_speak_different_voice_misses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=tts_response())

    adapter = make_adapter(handler, tmp_path)
    adapter.speak("hello", voice="mimo_default")
    adapter.speak("hello", voice="茉莉")

    assert len(calls) == 2


def test_search_second_identical_query_uses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=search_response())

    adapter = make_adapter(handler, tmp_path)
    first = adapter.search("roofline", count=3, need_content=False)
    second = adapter.search("roofline", count=3, need_content=False)

    assert first == second
    assert len(calls) == 1
    assert adapter.search("roofline", count=3, need_content=False, use_cache=False)


def test_fetch_second_identical_url_uses_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"title": "Example", "content": "Body."})

    adapter = make_adapter(handler, tmp_path)
    first = adapter.fetch("https://example.com")
    second = adapter.fetch("https://example.com")

    assert first == second
    assert len(calls) == 1


def test_chat_stream_second_identical_request_replays_cache(tmp_path: Path) -> None:
    calls: list[httpx.Request] = []
    chunks = [
        {
            "id": "chunk",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "deepseek-flash",
            "choices": [{"index": 0, "delta": {"content": "hello"}, "finish_reason": None}],
        },
        {
            "id": "chunk",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "deepseek-flash",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)

    adapter = make_adapter(handler, tmp_path)
    first = list(adapter.chat_stream([{"role": "user", "content": "ping"}], max_output_tokens=16))
    second = list(adapter.chat_stream([{"role": "user", "content": "ping"}], max_output_tokens=16))

    assert first == second
    assert [event.kind for event in second] == ["text", "finish", "usage"]
    assert len(calls) == 1
