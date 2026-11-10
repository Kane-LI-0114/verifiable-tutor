"""Streaming TTS endpoint contract."""

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
