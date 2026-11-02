"""Security units: password hashing and signed session values."""

from __future__ import annotations

from verifiable_tutor.auth.security import (
    hash_password,
    new_verification_code,
    sign_token,
    unsign_token,
    verify_password,
)


def test_scrypt_hash_is_salted_and_not_the_plaintext():
    first = hash_password("correct-horse-battery")
    second = hash_password("correct-horse-battery")

    assert first.startswith("scrypt$")
    assert "correct-horse-battery" not in first
    assert first != second


def test_verify_password_accepts_the_right_and_rejects_the_wrong_password():
    stored = hash_password("correct-horse-battery")

    assert verify_password("correct-horse-battery", stored) is True
    assert verify_password("wrong-password", stored) is False


def test_session_signature_rejects_tampering_and_foreign_secrets():
    value = sign_token("opaque-token", "secret-a")

    assert unsign_token(value, "secret-a") == "opaque-token"
    assert unsign_token(value, "secret-b") is None
    assert unsign_token(value[:-1] + "x", "secret-a") is None


def test_verification_codes_are_six_digits():
    codes = {new_verification_code() for _ in range(50)}

    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 1
