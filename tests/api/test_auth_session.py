"""Sign-in rules and server-side session handling."""

from __future__ import annotations

PASSWORD = "correct-horse-battery"


def test_wrong_password_is_rejected(api):
    api.create_active_account("alice@ust.hk")

    response = api.login_response("alice@ust.hk", "wrong-password")

    assert response.status_code == 401
    assert response.json() == {"detail": "incorrect email or password"}


def test_unknown_account_is_rejected(api):
    response = api.login_response("nobody@ust.hk", PASSWORD)

    assert response.status_code == 401
    assert response.json() == {"detail": "incorrect email or password"}


def test_tampered_session_cookie_is_rejected(api):
    cookies = api.create_active_account("alice@ust.hk")
    value = cookies["vt_session"]
    tampered = ("A" if value[0] != "A" else "B") + value[1:]

    api.set_cookie(tampered)
    response = api.client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "not signed in"}


def test_session_expires_after_seven_days_of_inactivity(api):
    cookies = api.create_active_account("alice@ust.hk")

    api.clock.advance(days=7, seconds=1)
    response = api.client.get("/api/auth/me")

    assert response.status_code == 401


def test_activity_extends_the_session(api):
    cookies = api.create_active_account("alice@ust.hk")

    api.clock.advance(days=6)
    assert api.client.get("/api/auth/me").status_code == 200
    api.clock.advance(days=6)
    assert api.client.get("/api/auth/me").status_code == 200


def test_logout_without_a_session_is_idempotent(api):
    response = api.client.post("/api/auth/logout")

    assert response.status_code == 204


def test_me_returns_the_public_account_fields(api):
    cookies = api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@ust.hk"
    assert body["role"] == "student"
    assert body["created_at"]
    assert "password" not in response.text
