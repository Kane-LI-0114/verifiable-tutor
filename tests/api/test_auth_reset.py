"""Password reset: one-time token, expiry, and session invalidation."""

from __future__ import annotations

PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "new-password-123"


def _request_reset(api, email: str = "alice@ust.hk"):
    return api.client.post("/api/auth/reset/request", json={"email": email})


def test_reset_request_sends_a_one_time_link(api):
    api.create_active_account("alice@ust.hk")

    response = _request_reset(api)

    assert response.status_code == 202
    assert response.json() == {"email": "alice@ust.hk", "email_delivery": "log"}
    assert "token=" in api.email.last_message.body


def test_reset_request_does_not_reveal_unknown_accounts(api):
    response = _request_reset(api, "nobody@ust.hk")

    assert response.status_code == 202
    assert response.json() == {"email": "nobody@ust.hk", "email_delivery": "log"}
    assert api.email.sent == []


def test_reset_changes_the_password_and_invalidates_sessions(api):
    cookies = api.create_active_account("alice@ust.hk")
    _request_reset(api)
    token = api.reset_token()

    response = api.client.post(
        "/api/auth/reset", json={"token": token, "new_password": NEW_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {
        "email": "alice@ust.hk",
        "sessions_invalidated": 1,
    }
    assert api.client.get("/api/auth/me").status_code == 401
    assert api.login_response("alice@ust.hk", PASSWORD).status_code == 401
    assert api.login_response("alice@ust.hk", NEW_PASSWORD).status_code == 200


def test_reset_token_is_single_use(api):
    api.create_active_account("alice@ust.hk")
    _request_reset(api)
    token = api.reset_token()
    first = api.client.post(
        "/api/auth/reset", json={"token": token, "new_password": NEW_PASSWORD}
    )
    assert first.status_code == 200

    second = api.client.post(
        "/api/auth/reset",
        json={"token": token, "new_password": "another-password-456"},
    )

    assert second.status_code == 400
    assert second.json() == {"detail": "invalid or expired reset token"}


def test_reset_token_expires_after_thirty_minutes(api):
    api.create_active_account("alice@ust.hk")
    _request_reset(api)
    token = api.reset_token()

    api.clock.advance(minutes=30, seconds=1)
    response = api.client.post(
        "/api/auth/reset", json={"token": token, "new_password": NEW_PASSWORD}
    )

    assert response.status_code == 400


def test_reset_enforces_the_password_policy(api):
    api.create_active_account("alice@ust.hk")
    _request_reset(api)
    token = api.reset_token()

    response = api.client.post(
        "/api/auth/reset", json={"token": token, "new_password": "short"}
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "password must be at least 8 characters"
    }
