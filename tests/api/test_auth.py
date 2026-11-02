"""Account lifecycle: registration, verification, sign-in, and sign-out."""

from __future__ import annotations

import re

PASSWORD = "correct-horse-battery"


def test_register_creates_pending_account_and_logs_the_verification_code(api):
    response = api.register("alice@ust.hk")

    assert response.status_code == 201
    assert response.json() == {
        "email": "alice@ust.hk",
        "role": "student",
        "verification": "pending",
        "email_delivery": "log",
    }
    assert api.email.last_message.to == "alice@ust.hk"
    assert re.search(r"\b\d{6}\b", api.email.last_message.body)


def test_unverified_account_cannot_sign_in(api):
    api.register("alice@ust.hk")

    response = api.login_response("alice@ust.hk")

    assert response.status_code == 403
    assert response.json() == {"detail": "account is not verified"}


def test_verify_activates_the_account(api):
    api.register("alice@ust.hk")

    response = api.verify("alice@ust.hk")

    assert response.status_code == 200
    assert response.json() == {"email": "alice@ust.hk", "status": "active"}


def test_login_sets_a_signed_session_cookie_and_me_reads_it(api):
    cookies = api.create_active_account("alice@ust.hk")

    login_response = api.login_response("alice@ust.hk")
    assert login_response.status_code == 200
    assert login_response.json()["user"] == {
        "id": login_response.json()["user"]["id"],
        "email": "alice@ust.hk",
        "role": "student",
    }

    me = api.client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "alice@ust.hk"
    assert me.json()["role"] == "student"
    assert "password" not in me.text


def test_login_cookie_is_http_only_same_site_and_has_a_seven_day_lifetime(api):
    api.create_active_account("alice@ust.hk")

    response = api.login_response("alice@ust.hk")
    cookie = response.headers["set-cookie"]

    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Max-Age=604800" in cookie


def test_logout_invalidates_the_session(api):
    cookies = api.create_active_account("alice@ust.hk")

    logout = api.client.post("/api/auth/logout")
    assert logout.status_code == 204

    me = api.client.get("/api/auth/me")
    assert me.status_code == 401
    assert me.json() == {"detail": "not signed in"}


def test_me_without_a_session_is_unauthorized(api):
    response = api.client.get("/api/auth/me")

    assert response.status_code == 401
