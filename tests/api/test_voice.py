"""Voice routes: MiMo ASR transcription and TTS speech."""

from __future__ import annotations

from verifiable_tutor.llm.adapter import CapabilityError

PASSWORD = "correct-horse-battery"


def test_voice_requires_sign_in(api):
    assert api.client.post("/api/voice/speech", json={"text": "hi"}).status_code == 401
    assert (
        api.client.post(
            "/api/voice/transcriptions",
            files={"audio": ("clip.wav", b"RIFFdata", "audio/wav")},
        ).status_code
        == 401
    )


def test_transcription_returns_the_adapter_result(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/voice/transcriptions",
        files={"audio": ("clip.wav", b"RIFF-data", "audio/wav")},
        data={"language": "en"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "hello world",
        "language": "en",
        "seconds": 1.5,
        "model": "mimo-v2.5-asr",
    }
    call = api.adapter.calls[0]
    assert call["audio"] == b"RIFF-data"
    assert call["kwargs"]["mime"] == "audio/wav"
    assert call["kwargs"]["language"] == "en"


def test_transcription_rejects_an_unsupported_audio_type(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/voice/transcriptions",
        files={"audio": ("clip.ogg", b"OggS", "audio/ogg")},
    )

    assert response.status_code == 415
    assert response.json() == {
        "detail": "unsupported audio type; MiMo ASR accepts audio/wav or audio/mpeg"
    }


def test_transcription_rejects_an_oversized_file(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/voice/transcriptions",
        files={"audio": ("clip.wav", b"x" * 7_000_001, "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "audio file is too large"}


def test_transcription_maps_a_capability_error_to_400(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.transcribe_error = CapabilityError("ASR audio exceeds the limit")

    response = api.client.post(
        "/api/voice/transcriptions",
        files={"audio": ("clip.wav", b"RIFF", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "ASR audio exceeds the limit"}


def test_transcription_without_a_model_layer_returns_503(api):
    api.create_active_account("alice@ust.hk")
    api.app.state.adapter_factory = lambda: _raise_missing_key()

    response = api.client.post(
        "/api/voice/transcriptions",
        files={"audio": ("clip.wav", b"RIFF", "audio/wav")},
    )

    assert response.status_code == 503
    assert response.json()["detail"].startswith("model layer is not configured")


def _raise_missing_key():
    raise RuntimeError("missing API key")


def test_speech_returns_audio_bytes_with_the_right_media_type(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/voice/speech", json={"text": "hello", "voice": "Mia", "format": "wav"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"RIFFfake"
    call = api.adapter.calls[0]
    assert call["text"] == "hello"
    assert call["kwargs"] == {"voice": "Mia", "format": "wav", "model_alias": "default"}


def test_speech_rejects_blank_text(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post("/api/voice/speech", json={"text": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "text must not be empty"}


def test_speech_maps_capability_errors_to_400(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.speak_error = CapabilityError("unsupported TTS format 'ogg'")

    response = api.client.post(
        "/api/voice/speech", json={"text": "hello", "format": "ogg"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "unsupported TTS format 'ogg'"}


def test_speech_without_a_model_layer_returns_503(api):
    api.create_active_account("alice@ust.hk")
    api.app.state.adapter_factory = lambda: _raise_missing_key()

    response = api.client.post("/api/voice/speech", json={"text": "hello"})

    assert response.status_code == 503


def test_tts_player_page_is_served_for_manual_auditioning(api):
    response = api.client.get("/api/voice/speech/player")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<audio" in response.text
    assert "/api/voice/speech" in response.text
    assert "Play" in response.text

    schema = api.client.get("/openapi.json").json()
    assert "/api/voice/speech/player" not in schema["paths"]
