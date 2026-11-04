"""Registration rules: domains, passwords, duplicate accounts, and codes."""

from __future__ import annotations

PASSWORD = "correct-horse-battery"


def test_register_rejects_a_foreign_email_domain(api):
    response = api.register("alice@gmail.com")

    assert response.status_code == 400
    assert response.json() == {"detail": "email domain is not allowed"}
    assert api.email.sent == []


def test_allowed_domains_are_public_configuration(api):
    response = api.client.get("/api/auth/domains")

    assert response.status_code == 200
    assert response.json() == {"domains": ["ust.hk"]}


def test_allowed_domains_keep_the_configured_order(domains_api):
    response = domains_api.client.get("/api/auth/domains")

    assert response.status_code == 200
    assert response.json() == {"domains": ["connect.ust.hk", "ust.hk"]}


def test_register_rejects_an_invalid_email_address(api):
    response = api.register("not-an-email")

    assert response.status_code == 400
    assert response.json() == {"detail": "email address is not valid"}


def test_register_rejects_a_short_password(api):
    response = api.register("alice@ust.hk", password="short")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "password must be at least 8 characters"
    }


def test_register_normalises_the_email_address(api):
    response = api.register("Alice@UST.HK")

    assert response.status_code == 201
    assert response.json()["email"] == "alice@ust.hk"


def test_register_returns_conflict_for_an_active_account(api):
    api.create_active_account("alice@ust.hk")

    response = api.register("alice@ust.hk")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "an account with this email already exists"
    }


def test_verification_code_expires_after_ten_minutes(api):
    api.register("alice@ust.hk")
    code = api.verification_code()

    api.clock.advance(minutes=10, seconds=1)
    response = api.verify("alice@ust.hk", code=code)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "invalid or expired verification code"
    }


def test_verification_code_is_single_use(api):
    api.register("alice@ust.hk")
    code = api.verification_code()
    assert api.verify("alice@ust.hk", code=code).status_code == 200

    response = api.verify("alice@ust.hk", code=code)

    assert response.status_code == 400


def test_wrong_verification_code_is_rejected(api):
    api.register("alice@ust.hk")

    response = api.verify("alice@ust.hk", code="000000")

    assert response.status_code == 400
