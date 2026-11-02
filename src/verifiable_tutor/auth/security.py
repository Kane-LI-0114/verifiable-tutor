"""Password hashing, opaque tokens, and signed session cookie values."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_SALT_BYTES = 16
_PREFIX = "scrypt"

MIN_PASSWORD_LENGTH = 8


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    """Hash a password with scrypt; the stored value carries its parameters."""

    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
    )
    return f"{_PREFIX}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Return whether the password matches the stored scrypt hash."""

    try:
        prefix, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if prefix != _PREFIX:
            return False
        salt = _unb64(salt_b64)
        expected = _unb64(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def new_token(nbytes: int = 32) -> str:
    """Return a fresh opaque token for a server-side session or reset link."""

    return secrets.token_urlsafe(nbytes)


def sign_token(token: str, secret: str) -> str:
    """Return ``token.signature``, the value stored in the session cookie."""

    signature = hmac.new(
        secret.encode("utf-8"), token.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{token}.{_b64(signature)}"


def unsign_token(value: str, secret: str) -> str | None:
    """Return the token when the signature is valid, otherwise ``None``."""

    token, separator, signature = value.partition(".")
    if not separator or not token or not signature:
        return None
    expected = sign_token(token, secret).partition(".")[2]
    if not hmac.compare_digest(signature, expected):
        return None
    return token


def new_verification_code() -> str:
    """Return a six digit registration code."""

    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str, user_id: str) -> str:
    """Hash a registration code together with the account it belongs to."""

    return hashlib.sha256(f"{user_id}:{code}".encode("utf-8")).hexdigest()


def hash_reset_token(token: str) -> str:
    """Hash a reset token; reset tokens are looked up without an email."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def password_error(password: str) -> str | None:
    """Return a user-facing password policy error, or ``None`` when valid."""

    if len(password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    return None
