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
