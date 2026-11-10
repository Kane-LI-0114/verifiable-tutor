"""Streaming TTS endpoint contract."""

import pytest

from verifiable_tutor.llm.adapter import ModelResponseError

from helpers import parse_sse

ANSWER = "MPI_Allreduce combines values from all ranks."
FRAMES = ["AAABAA==", "AgADAA=="]


def test_voice_stream_endpoint_emits_pcm16_frames_and_the_done_marker(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.speech_stream_frames = FRAMES

    response = api.client.post("/api/voice/speech/stream", json={"text": ANSWER})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "x-vercel-ai-ui-message-stream" not in response.headers
    assert parse_sse(response.text) == [
        {"audio": FRAMES[0]},
        {"audio": FRAMES[1]},
        "[DONE]",
    ]
    call = api.adapter.calls[-1]
    assert call["text"] == ANSWER
    assert call["kwargs"] == {"voice": None}


def test_voice_stream_endpoint_requires_a_signed_in_account(api):
    response = api.client.post("/api/voice/speech/stream", json={"text": ANSWER})

    assert response.status_code == 401
    assert api.adapter.calls == []


def test_voice_stream_endpoint_rejects_blank_answer_text(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/voice/speech/stream", json={"text": "   \n  "}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "text must not be empty"}
    assert api.adapter.calls == []


def test_voice_stream_endpoint_reports_pre_stream_model_failure_as_unavailable(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.speak_stream_fail_before_first = ModelResponseError(
        "unavailable", 3, "fake pre-stream failure"
    )

    try:
        response = api.client.post(
            "/api/voice/speech/stream", json={"text": ANSWER}
        )
    except Exception as exc:
        pytest.fail(f"pre-stream failure surfaced as {type(exc).__name__}, not 503")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The model is temporarily unavailable. Please try again."
    }
