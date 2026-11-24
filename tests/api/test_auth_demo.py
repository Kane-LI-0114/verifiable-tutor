"""The seeded reviewer account: startup seeding and the login-page hint."""

from __future__ import annotations

from datetime import datetime, timezone

from verifiable_tutor.auth.service import ensure_demo_account

from conftest import DEMO_EMAIL, DEMO_PASSWORD


def test_demo_endpoint_advertises_the_seeded_student(demo_api):
    response = demo_api.client.get("/api/auth/demo")

    assert response.status_code == 200
    assert response.json() == {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}


def test_seeded_student_signs_in_without_registering(demo_api):
    response = demo_api.login_response(DEMO_EMAIL, DEMO_PASSWORD)

    assert response.status_code == 200
    assert response.json()["user"]["email"] == DEMO_EMAIL
    assert response.json()["user"]["role"] == "student"


def test_demo_endpoint_returns_nulls_when_no_account_is_configured(api):
    response = api.client.get("/api/auth/demo")

    assert response.status_code == 200
    assert response.json() == {"email": None, "password": None}


def test_seeding_repairs_a_password_that_no_longer_matches(demo_api):
    storage = demo_api.app.state.storage
    user = storage.find_user_by_email(DEMO_EMAIL)
    assert user is not None
    storage.update_user(user["id"], password_hash="stale-hash")

    ensure_demo_account(
        storage=storage,
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD,
        clock=lambda: datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
    )

    assert demo_api.login_response(DEMO_EMAIL, DEMO_PASSWORD).status_code == 200
