"""Conversation listing and history endpoints."""

from __future__ import annotations


def test_session_endpoints_require_sign_in(api):
    assert api.client.get("/api/sessions").status_code == 401
    assert api.client.get("/api/sessions/abc/messages").status_code == 401


def test_new_account_has_no_sessions(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/sessions")

    assert response.status_code == 200
    assert response.json() == {"sessions": []}


def test_unknown_session_history_is_not_found(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/sessions/does-not-exist/messages")

    assert response.status_code == 404
    assert response.json() == {"detail": "conversation not found"}


def test_foreign_session_history_is_not_found(api):
    api.create_active_account("alice@ust.hk")
    created = api.client.post("/api/chat", json={"message": "alice question"})
    session_id = created.headers["x-conversation-id"]

    api.clear_cookies()
    api.register("bob@ust.hk")
    api.verify("bob@ust.hk")
    api.login("bob@ust.hk")
    response = api.client.get(f"/api/sessions/{session_id}/messages")

    assert response.status_code == 404


def test_sessions_list_only_the_current_user(api):
    api.create_active_account("alice@ust.hk")
    api.client.post("/api/chat", json={"message": "alice question"})

    api.clear_cookies()
    api.register("bob@ust.hk")
    api.verify("bob@ust.hk")
    api.login("bob@ust.hk")
    response = api.client.get("/api/sessions")

    assert response.status_code == 200
    assert response.json() == {"sessions": []}


def test_history_returns_empty_turn_metadata_for_a_legacy_answer(api):
    """Rows written before turn metadata existed stay readable and unadorned."""

    api.create_active_account("alice@ust.hk")
    user_id = api.client.get("/api/auth/me").json()["id"]
    storage = api.app.state.storage
    storage.create_conversation(
        conversation_id="legacy-conversation",
        user_id=user_id,
        title="Legacy question",
        created_at=api.clock(),
    )
    storage.add_message(
        message_id="legacy-question",
        conversation_id="legacy-conversation",
        sequence=1,
        role="user",
        content="old question",
        created_at=api.clock(),
    )
    storage.add_message(
        message_id="legacy-answer",
        conversation_id="legacy-conversation",
        sequence=2,
        role="assistant",
        content="old answer",
        provider="deepseek",
        tier="flash",
        created_at=api.clock(),
    )

    response = api.client.get("/api/sessions/legacy-conversation/messages")

    assert response.status_code == 200
    question, answer = response.json()["messages"]
    for message in (question, answer):
        assert message["reasoning"] is None
        assert message["model"] is None
        assert message["thinking"] is None
        assert message["work_steps"] == []
        assert message["citations"] == []
        assert message["tool_calls"] == []
    assert answer["content"] == "old answer"
