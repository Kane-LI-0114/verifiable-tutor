"""Chat streaming, persistence, trace recording, and failure behavior."""

from __future__ import annotations

import json
from pathlib import Path

from verifiable_tutor.llm.adapter import (
    ModelResponseError,
    ModelSelectionError,
    StreamEvent,
)

from helpers import parse_sse

PASSWORD = "correct-horse-battery"


def _text_events(*chunks: str) -> list[StreamEvent]:
    events = [StreamEvent(kind="text", text=chunk) for chunk in chunks]
    return [*events, StreamEvent(kind="finish", finish_reason="stop")]


def test_chat_requires_sign_in(api):
    response = api.client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 401
    assert api.adapter.calls == []


def test_chat_streams_the_ai_sdk_message_stream(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.events = _text_events("Hel", "lo")

    response = api.client.post("/api/chat", json={"message": "What is MPI?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert response.headers["x-conversation-id"]
    parts = parse_sse(response.text)
    types = [part if part == "[DONE]" else part["type"] for part in parts]
    assert types == [
        "start",
        "data-step",
        "text-start",
        "text-delta",
        "text-delta",
        "text-end",
        "data-step",
        "finish",
        "[DONE]",
    ]
    deltas = "".join(
        part["delta"]
        for part in parts
        if isinstance(part, dict) and part["type"] == "text-delta"
    )
    assert deltas == "Hello"
    assert parts[0]["messageId"]
    text_part = parts[2]["id"]
    assert {part["id"] for part in parts[3:6]} == {text_part}


def test_chat_persists_both_messages_and_hides_them_behind_the_session(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post("/api/chat", json={"message": "What is MPI?"})
    session_id = response.headers["x-conversation-id"]

    history = api.client.get(f"/api/sessions/{session_id}/messages")
    assert history.status_code == 200
    body = history.json()
    assert body["session_id"] == session_id
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "What is MPI?"
    assert body["messages"][1]["content"] == "Hello"
    assert api.adapter.calls[0]["messages"][0]["role"] == "system"


def test_chat_resumes_a_conversation_and_sends_its_history(api):
    api.create_active_account("alice@ust.hk")
    first = api.client.post("/api/chat", json={"message": "first question"})
    session_id = first.headers["x-conversation-id"]

    second = api.client.post(
        "/api/chat", json={"message": "second question", "session_id": session_id}
    )

    assert second.headers["x-conversation-id"] == session_id
    sent = api.adapter.calls[1]["messages"]
    assert [message["role"] for message in sent[:3]] == ["system", "user", "assistant"]
    assert sent[-1] == {"role": "user", "content": "second question"}
    history = api.client.get(f"/api/sessions/{session_id}/messages").json()["messages"]
    assert len(history) == 4
    sessions = api.client.get("/api/sessions").json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["message_count"] == 4


def test_chat_rejects_a_foreign_conversation(api):
    api.create_active_account("alice@ust.hk")
    created = api.client.post("/api/chat", json={"message": "alice question"})
    session_id = created.headers["x-conversation-id"]

    api.clear_cookies()
    api.register("bob@ust.hk")
    api.verify("bob@ust.hk")
    api.login("bob@ust.hk")
    response = api.client.post(
        "/api/chat", json={"message": "bob question", "session_id": session_id}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "conversation not found"}


def test_chat_model_failure_before_the_first_byte_returns_503(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.fail_before_first = ModelResponseError("unavailable", 3, "down")

    response = api.client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The model is temporarily unavailable. Please try again."
    }


def test_chat_mid_stream_failure_emits_the_error_part_and_keeps_no_partial_answer(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.events = _text_events("Par")
    api.adapter.fail_after = 1

    response = api.client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    parts = parse_sse(response.text)
    types = [part if part == "[DONE]" else part["type"] for part in parts]
    assert types == ["start", "data-step", "text-start", "text-delta", "error", "[DONE]"]
    session_id = response.headers["x-conversation-id"]
    history = api.client.get(f"/api/sessions/{session_id}/messages").json()["messages"]
    assert [message["role"] for message in history] == ["user"]


def test_chat_records_the_session_trace_without_the_email(api):
    api.create_active_account("alice@ust.hk")
    user_id = api.client.get("/api/auth/me").json()["id"]

    response = api.client.post("/api/chat", json={"message": "What is MPI?"})
    session_id = response.headers["x-conversation-id"]
    trace_path = (
        api.settings.trace_dir / user_id / f"{session_id}.jsonl"
    )

    assert trace_path.is_file()
    text = trace_path.read_text(encoding="utf-8")
    assert "alice@ust.hk" not in text
    records = [json.loads(line) for line in text.splitlines()]
    kinds = [record["kind"] for record in records]
    assert kinds[0] == "meta"
    assert kinds.count("frame") == 7
    assert "event" in kinds


def test_chat_invalid_model_selection_is_a_bad_request(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.fail_before_first = ModelSelectionError("unknown model profile")

    response = api.client.post(
        "/api/chat", json={"message": "hello", "provider": "mimo", "tier": "pro"}
    )

    assert response.status_code == 400
