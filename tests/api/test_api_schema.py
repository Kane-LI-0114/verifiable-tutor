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


RESPONSE_MODELS = {
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
}

REQUEST_BODY_MODELS = {
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


def test_response_models_carry_swagger_examples(api):
    schema = _schema(api)
    components = schema["components"]["schemas"]

    missing = [
        name
        for name in sorted(RESPONSE_MODELS)
        if "example" not in components[name] and "examples" not in components[name]
    ]
    assert missing == []


def test_request_body_schemas_do_not_prefill_the_edit_value(api):
    schema = _schema(api)
    components = schema["components"]["schemas"]

    for name in sorted(REQUEST_BODY_MODELS):
        model = components[name]
        assert "example" not in model and "examples" not in model, name
        for field_name, field in model["properties"].items():
            assert "example" not in field, f"{name}.{field_name}"
            assert "enum" not in field, f"{name}.{field_name}"
            assert field.get("description"), f"{name}.{field_name}"


def test_request_body_descriptions_list_examples_and_options(api):
    schema = _schema(api)
    components = schema["components"]["schemas"]

    chat = components["ChatBody"]["properties"]
    assert "What is MPI_Allreduce?" in chat["message"]["description"]
    assert "deepseek" in chat["provider"]["description"]
    assert "mimo" in chat["provider"]["description"]
    assert "flash" in chat["tier"]["description"]
    assert "pro" in chat["tier"]["description"]

    speech = components["SpeechBody"]["properties"]
    assert "MPI_Allreduce combines values from all ranks." in speech["text"]["description"]
    for option in ("wav", "mp3", "pcm", "pcm16"):
        assert option in speech["format"]["description"]
    assert "Mia" in speech["voice"]["description"]
    for alias in ("default", "voiceclone", "voicedesign"):
        assert alias in speech["model_alias"]["description"]

    register = components["RegisterBody"]["properties"]
    assert "student@ust.hk" in register["email"]["description"]


def test_response_fields_keep_examples_and_enums(api):
    schema = _schema(api)
    schemas = schema["components"]["schemas"]

    login_user = schemas["LoginUser"]["properties"]
    assert login_user["role"]["enum"] == ["student", "instructor"]
    assert login_user["email"]["example"] == "student@ust.hk"

    build = schemas["BuildRecord"]["properties"]
    assert build["state"]["enum"] == ["queued", "running", "ready", "failed"]
    assert build["job_id"]["example"] == "28067"

    register_response = schemas["RegisterResponse"]["properties"]
    assert register_response["email_delivery"]["enum"] == ["log", "smtp"]

    message = schemas["MessageRecord"]["properties"]
    assert message["content"]["example"] == "What is MPI_Allreduce?"
    assert message["role"]["enum"] == ["user", "assistant"]


def test_get_speech_query_parameters_carry_examples(api):
    schema = _schema(api)
    parameters = schema["paths"]["/api/voice/speech"]["get"]["parameters"]
    by_name = {parameter["name"]: parameter for parameter in parameters}

    assert (
        by_name["text"]["schema"]["example"]
        == "MPI_Allreduce combines values from all ranks."
    )
    assert (
        by_name["text"]["examples"]["default"]["value"]
        == "MPI_Allreduce combines values from all ranks."
    )
    assert by_name["voice"]["schema"]["example"] == "Mia"
    assert by_name["voice"]["examples"]["default"]["value"] == "Mia"
    assert by_name["format"]["schema"]["enum"] == ["wav", "mp3", "pcm", "pcm16"]
    assert by_name["model_alias"]["schema"]["enum"] == [
        "default",
        "voiceclone",
        "voicedesign",
    ]
