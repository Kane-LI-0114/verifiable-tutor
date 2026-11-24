"""Account, verification, and server-side session business logic."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from .email import EmailMessage, EmailSender
from .security import (
    hash_password,
    hash_reset_token,
    hash_verification_code,
    new_token,
    new_verification_code,
    password_error,
    sign_token,
    unsign_token,
    verify_password,
)
from ..settings import AppSettings
from ..storage import Storage, iso, parse_iso, row_to_public_user

logger = logging.getLogger("verifiable_tutor.api.auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GENERIC_LOGIN_ERROR = "incorrect email or password"
GENERIC_RESET_ERROR = "invalid or expired reset token"
GENERIC_CODE_ERROR = "invalid or expired verification code"


class AuthError(Exception):
    """A client-visible failure in the account flows."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class LoginResult:
    user: dict[str, Any]
    cookie_value: str


class AuthService:
    """Registration, verification, sign-in, sign-out, and password reset."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        storage: Storage,
        email_sender: EmailSender,
        clock: Callable[[], datetime],
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._email = email_sender
        self._clock = clock

    # -- validation helpers ------------------------------------------------
    def _normalise_email(self, email: str) -> str:
        value = email.strip().lower()
        if not _EMAIL_RE.match(value):
            raise AuthError(400, "email address is not valid")
        domain = value.partition("@")[2]
        allowed = self._settings.allowed_email_domains
        if allowed and domain not in allowed:
            raise AuthError(400, "email domain is not allowed")
        return value

    def _validate_password(self, password: str) -> None:
        error = password_error(password)
        if error is not None:
            raise AuthError(400, error)

    def _send(self, to: str, subject: str, body: str) -> None:
        self._email.send(EmailMessage(to=to, subject=subject, body=body))

    # -- registration ------------------------------------------------------
    def register(self, email: str, password: str) -> dict[str, Any]:
        normalised = self._normalise_email(email)
        self._validate_password(password)
        existing = self._storage.find_user_by_email(normalised)
        now = self._clock()
        if existing is not None:
            if existing["status"] == "active":
                raise AuthError(409, "an account with this email already exists")
            user_id = existing["id"]
            self._storage.update_user(
                user_id, password_hash=hash_password(password), status="pending"
            )
        else:
            user_id = uuid.uuid4().hex
            self._storage.create_user(
                user_id=user_id,
                email=normalised,
                password_hash=hash_password(password),
                role="student",
                status="pending",
                created_at=now,
            )
        code = new_verification_code()
        self._storage.replace_open_code(
            code_id=uuid.uuid4().hex,
            user_id=user_id,
            purpose="verify",
            code_hash=hash_verification_code(code, user_id),
            created_at=now,
            expires_at=now + self._settings.verification_code_ttl,
        )
        minutes = int(self._settings.verification_code_ttl.total_seconds() // 60)
        self._send(
            normalised,
            "Verifiable Tutor verification code",
            f"Your verification code is {code}. It expires in {minutes} minutes.",
        )
        return {
            "email": normalised,
            "role": "student",
            "verification": "pending",
            "email_delivery": self._email.delivery,
        }

    def verify(self, email: str, code: str) -> dict[str, Any]:
        normalised = self._normalise_email(email)
        user = self._storage.find_user_by_email(normalised)
        if user is None:
            raise AuthError(400, GENERIC_CODE_ERROR)
        record = self._storage.find_open_code_for_user(user["id"], "verify")
        now = self._clock()
        if (
            record is None
            or parse_iso(record["expires_at"]) < now
            or record["code_hash"]
            != hash_verification_code(code.strip(), user["id"])
        ):
            raise AuthError(400, GENERIC_CODE_ERROR)
        self._storage.consume_code(record["id"], now)
        self._storage.update_user(
            user["id"], status="active", verified_at=iso(now)
        )
        return {"email": normalised, "status": "active"}

    # -- sign in and sessions ---------------------------------------------
    def login(self, email: str, password: str) -> LoginResult:
        normalised = email.strip().lower()
        user = self._storage.find_user_by_email(normalised)
        if user is None or not verify_password(password, user["password_hash"]):
            raise AuthError(401, GENERIC_LOGIN_ERROR)
        if user["status"] == "pending":
            raise AuthError(403, "account is not verified")
        if user["status"] != "active":
            raise AuthError(403, "account is disabled")
        now = self._clock()
        token = new_token()
        self._storage.create_login_session(
            session_id=token,
            user_id=user["id"],
            created_at=now,
            expires_at=now + self._settings.session_ttl,
        )
        public = row_to_public_user(user)
        return LoginResult(
            user={"id": public["id"], "email": public["email"], "role": public["role"]},
            cookie_value=sign_token(token, self._settings.session_secret),
        )

    def current_user(self, cookie_value: str | None) -> dict[str, Any]:
        if not cookie_value:
            raise AuthError(401, "not signed in")
        token = unsign_token(cookie_value, self._settings.session_secret)
        if token is None:
            raise AuthError(401, "not signed in")
        session = self._storage.find_login_session(token)
        if session is None:
            raise AuthError(401, "not signed in")
        now = self._clock()
        if parse_iso(session["expires_at"]) < now:
            self._storage.delete_login_session(token)
            raise AuthError(401, "not signed in")
        user = self._storage.find_user_by_id(session["user_id"])
        if user is None or user["status"] != "active":
            raise AuthError(401, "not signed in")
        self._storage.touch_login_session(
            token, seen_at=now, expires_at=now + self._settings.session_ttl
        )
        return row_to_public_user(user)

    def logout(self, cookie_value: str | None) -> None:
        if not cookie_value:
            return
        token = unsign_token(cookie_value, self._settings.session_secret)
        if token is not None:
            self._storage.delete_login_session(token)

    # -- password reset ----------------------------------------------------
    def request_reset(self, email: str) -> dict[str, Any]:
        normalised = email.strip().lower()
        if not _EMAIL_RE.match(normalised):
            raise AuthError(400, "email address is not valid")
        result = {"email": normalised, "email_delivery": self._email.delivery}
        user = self._storage.find_user_by_email(normalised)
        if user is None:
            return result
        now = self._clock()
        token = new_token()
        self._storage.replace_open_code(
            code_id=uuid.uuid4().hex,
            user_id=user["id"],
            purpose="reset",
            code_hash=hash_reset_token(token),
            created_at=now,
            expires_at=now + self._settings.reset_token_ttl,
        )
        minutes = int(self._settings.reset_token_ttl.total_seconds() // 60)
        link = f"{self._settings.base_url}/reset?token={token}"
        self._send(
            normalised,
            "Verifiable Tutor password reset",
            f"Open this link within {minutes} minutes to reset your password: {link}",
        )
        return result

    def reset(self, token: str, new_password: str) -> dict[str, Any]:
        self._validate_password(new_password)
        now = self._clock()
        record = self._storage.find_open_code_by_hash(
            "reset", hash_reset_token(token.strip())
        )
        if record is None or parse_iso(record["expires_at"]) < now:
            raise AuthError(400, GENERIC_RESET_ERROR)
        user = self._storage.find_user_by_id(record["user_id"])
        if user is None:
            raise AuthError(400, GENERIC_RESET_ERROR)
        self._storage.consume_code(record["id"], now)
        self._storage.update_user(
            user["id"], password_hash=hash_password(new_password)
        )
        invalidated = self._storage.delete_login_sessions_for_user(user["id"])
        return {"email": user["email"], "sessions_invalidated": invalidated}


def _ensure_account(
    *,
    storage: Storage,
    email: str,
    password: str,
    role: str,
    clock: Callable[[], datetime],
    repair_password: bool,
) -> dict[str, Any]:
    """Create a seeded account or repair its role, status, and password.

    A seeded account is active without the email verification round trip, so it
    can sign in on a fresh checkout. Repairing is idempotent: a second call
    changes nothing once the row matches the configuration.
    """

    normalised = email.strip().lower()
    if not _EMAIL_RE.match(normalised):
        raise AuthError(400, "email address is not valid")
    error = password_error(password)
    if error is not None:
        raise AuthError(400, error)
    existing = storage.find_user_by_email(normalised)
    now = clock()
    if existing is None:
        storage.create_user(
            user_id=uuid.uuid4().hex,
            email=normalised,
            password_hash=hash_password(password),
            role=role,
            status="active",
            created_at=now,
        )
        return {"email": normalised, "role": role, "created": True}
    updates: dict[str, Any] = {}
    if existing["role"] != role:
        updates["role"] = role
    if existing["status"] != "active":
        updates["status"] = "active"
    if repair_password and not verify_password(password, existing["password_hash"]):
        updates["password_hash"] = hash_password(password)
    if updates:
        storage.update_user(existing["id"], **updates)
    return {"email": normalised, "role": role, "created": False}


def bootstrap_instructor(
    *,
    storage: Storage,
    email: str,
    password: str,
    clock: Callable[[], datetime],
) -> dict[str, Any]:
    """Create the seeded instructor account or repair its role; idempotent."""

    return _ensure_account(
        storage=storage,
        email=email,
        password=password,
        role="instructor",
        clock=clock,
        repair_password=False,
    )


def ensure_demo_account(
    *,
    storage: Storage,
    email: str,
    password: str,
    clock: Callable[[], datetime],
) -> dict[str, Any]:
    """Create the seeded student reviewer account, or repair it; idempotent.

    The login page advertises these credentials, so a password changed in
    config/app.yaml takes effect on the next backend start. The account is a
    plain student: it grants the access any verified registration would.
    """

    return _ensure_account(
        storage=storage,
        email=email,
        password=password,
        role="student",
        clock=clock,
        repair_password=True,
    )
