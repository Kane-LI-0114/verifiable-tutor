import json
from pathlib import Path

import httpx

from verifiable_tutor.llm.adapter import ModelAdapter
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}

ANSWER = "MPI_Allreduce combines values from all ranks."

# Known-good base64 literals for 2-sample PCM16 chunks (little endian).
FRAMES = ["AAABAA==", "AgADAA==", "BAAFAA=="]


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = False
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def sse_response(frames: list[str]) -> httpx.Response:
    chunks = []
    for index, frame in enumerate(frames):
        chunks.append(
            {
                "id": "tts-stream",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "mimo-v2.5-tts",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "audio": {
                                "id": "audio-1",
                                "data": frame,
                                "expires_at": None,
                                "transcript": None,
                            }
                        },
                        "finish_reason": "stop" if index == len(frames) - 1 else None,
                    }
                ],
            }
        )
    body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        text=body + "data: [DONE]\n\n",
    )


def test_speak_stream_decodes_pcm16_chunks_from_the_mimo_stream() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return sse_response(FRAMES)

    result = list(make_adapter(handler).speak_stream(ANSWER))

    assert result == FRAMES
    body = json.loads(captured[0].content)
    assert body["stream"] is True
    assert body["model"] == "mimo-v2.5-tts"
    assert body["audio"] == {"format": "pcm16", "voice": "mimo_default"}
    assert body["messages"][1] == {"role": "assistant", "content": ANSWER}
