"""The OpenAPI schema is useful documentation, not just a path list."""

from __future__ import annotations

EXPECTED_TAGS = [
    "health",
    "auth",
    "chat",
    "sessions",
    "voice",
    "knowledge",
    "corpus",
    "practice",
]

EXPECTED_RESPONSE_MODELS = {
    "HealthResponse",
    "RegisterResponse",
    "VerifyResponse",
    "LoginResponse",
    "MeResponse",
    "ResetRequestResponse",
    "ResetResponse",
    "SessionListResponse",
    "SessionMessagesResponse",
    "TranscriptionResponse",
    "CardsResponse",
    "BuildAcceptedResponse",
    "BuildListResponse",
    "BuildRecord",
}


def _schema(api):
    response = api.client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_tags_are_documented_and_ordered(api):
    schema = _schema(api)

    assert [tag["name"] for tag in schema.get("tags", [])] == EXPECTED_TAGS
    assert all(tag.get("description") for tag in schema["tags"])


def test_every_operation_has_a_summary(api):
    schema = _schema(api)
    operations = {
        f"{method.upper()} {path}": operation
        for path, item in schema["paths"].items()
        for method, operation in item.items()
    }

    missing = [
        name for name, operation in operations.items() if not operation.get("summary")
    ]
    assert missing == []


def test_json_routes_declare_response_models(api):
    schema = _schema(api)
    components = schema["components"]["schemas"]

    missing = EXPECTED_RESPONSE_MODELS - set(components)
    assert missing == set()

    health = schema["paths"]["/api/health"]["get"]["responses"]["200"]["content"]
    assert health["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    login = schema["paths"]["/api/auth/login"]["post"]["responses"]["200"]["content"]
    assert login["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LoginResponse"
    }
    sessions = schema["paths"]["/api/sessions"]["get"]["responses"]["200"]["content"]
    assert sessions["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SessionListResponse"
    }


def test_streaming_routes_document_text_event_stream(api):
    schema = _schema(api)

    chat = schema["paths"]["/api/chat"]["post"]["responses"]["200"]["content"]
    replay = schema["paths"]["/api/sessions/{session_id}/replay"]["get"]["responses"][
        "200"
    ]["content"]
    assert "text/event-stream" in chat
    assert "text/event-stream" in replay


def test_key_error_responses_are_documented(api):
    schema = _schema(api)

    chat = schema["paths"]["/api/chat"]["post"]["responses"]
    assert "503" in chat
    assert "400" in chat
    practice = schema["paths"]["/api/practice/runs"]["post"]["responses"]
    assert "503" in practice
    transcription = schema["paths"]["/api/voice/transcriptions"]["post"]["responses"]
    assert "413" in transcription
    assert "415" in transcription
    build = schema["paths"]["/api/knowledge/builds"]["post"]["responses"]
    assert "403" in build
    assert "409" in build
    assert "503" in build


def test_audio_response_documents_binary_content_only(api):
    schema = _schema(api)

    content = schema["paths"]["/api/voice/speech"]["post"]["responses"]["200"]["content"]
    assert set(content) == {"audio/wav", "audio/mpeg", "audio/pcm"}
    assert "application/json" not in content


def test_models_carry_swagger_examples(api):
    schema = _schema(api)
    components = schema["components"]["schemas"]
    expected = {
        "HealthResponse",
        "RegisterResponse",
        "VerifyResponse",
        "LoginUser",
        "LoginResponse",
        "MeResponse",
        "ResetRequestResponse",
        "ResetResponse",
        "SessionSummary",
        "SessionListResponse",
        "MessageRecord",
        "SessionMessagesResponse",
        "TranscriptionResponse",
        "CitationRecord",
        "CardRecord",
        "CardsResponse",
        "BuildAcceptedResponse",
        "BuildRecord",
        "BuildListResponse",
        "RegisterBody",
        "VerifyBody",
        "LoginBody",
        "ResetRequestBody",
        "ResetBody",
        "ChatBody",
        "BuildBody",
        "SpeechBody",
        "PracticeRunBody",
    }
    assert expected <= set(components)

    missing = [
        name
        for name in sorted(expected)
        if "example" not in components[name] and "examples" not in components[name]
    ]
    assert missing == []
