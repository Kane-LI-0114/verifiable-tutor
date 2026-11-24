"""Account routes: registration, verification, sessions, and password reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from ...auth.service import AuthError, AuthService
from ..deps import CurrentUser, SettingsDep, get_auth
from ..schemas import (
    DemoAccountResponse,
    DomainsResponse,
    LoginResponse,
    MeResponse,
    RegisterResponse,
    ResetRequestResponse,
    ResetResponse,
    VerifyResponse,
)

router = APIRouter(tags=["auth"])


class _StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterBody(_StrictBody):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        description=(
            "Student email address; the domain must be configured. "
            "Example: student@ust.hk."
        )
    )
    password: str = Field(
        description=(
            "New password; at least 8 characters. "
            "Example: correct-horse-battery."
        )
    )


class VerifyBody(_StrictBody):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        description="Student email address. Example: student@ust.hk."
    )
    code: str = Field(
        description=(
            "Six digit verification code from the email. Example: 123456."
        )
    )


class LoginBody(_StrictBody):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        description="Account email address. Example: student@ust.hk."
    )
    password: str = Field(
        description="Account password. Example: correct-horse-battery."
    )


class ResetRequestBody(_StrictBody):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        description=(
            "Account email address; the same response is returned for unknown "
            "accounts. Example: student@ust.hk."
        )
    )


class ResetBody(_StrictBody):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(
        description=(
            "One-time reset token from the reset email link. "
            "Example: one-time-reset-token."
        )
    )
    new_password: str = Field(
        description=(
            "New password; at least 8 characters. "
            "Example: new-password-123."
        )
    )


def _raise(exc: AuthError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _set_session_cookie(response: Response, request: Request, value: str) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        key=settings.session_cookie_name,
        value=value,
        max_age=int(settings.session_ttl.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


@router.post(
    "/api/auth/register",
    status_code=201,
    response_model=RegisterResponse,
    summary="Register a student account",
)
def register(body: RegisterBody, request: Request, auth: AuthService = Depends(get_auth)):
    try:
        return auth.register(body.email, body.password)
    except AuthError as exc:
        _raise(exc)


@router.post(
    "/api/auth/verify",
    response_model=VerifyResponse,
    summary="Verify the registration code",
)
def verify(body: VerifyBody, auth: AuthService = Depends(get_auth)):
    try:
        return auth.verify(body.email, body.code)
    except AuthError as exc:
        _raise(exc)


@router.post(
    "/api/auth/login",
    response_model=LoginResponse,
    summary="Sign in and set the session cookie",
)
def login(
    body: LoginBody,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth),
):
    try:
        result = auth.login(body.email, body.password)
    except AuthError as exc:
        _raise(exc)
    _set_session_cookie(response, request, result.cookie_value)
    return {"user": result.user}


@router.post(
    "/api/auth/logout",
    status_code=204,
    summary="Sign out and clear the session cookie",
    responses={204: {"description": "Session cleared"}},
)
def logout(request: Request, response: Response, auth: AuthService = Depends(get_auth)):
    settings = request.app.state.settings
    auth.logout(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get(
    "/api/auth/me",
    response_model=MeResponse,
    summary="Current signed-in account",
)
def me(user: CurrentUser):
    return user


@router.get(
    "/api/auth/domains",
    response_model=DomainsResponse,
    summary="Allowed registration email domains",
)
def domains(settings: SettingsDep):
    """Return the configured registration domains in their configured order."""

    return {"domains": list(settings.allowed_email_domains)}


@router.get(
    "/api/auth/demo",
    response_model=DemoAccountResponse,
    summary="Seeded student account shown on the login page",
)
def demo_account(settings: SettingsDep):
    """Return the seeded reviewer account, or nulls when none is configured.

    The account is created at startup by the app lifespan, so a successful
    login needs no registration or verification email.
    """

    account = settings.demo_account
    if account is None:
        return {"email": None, "password": None}
    return {"email": account.email, "password": account.password}


@router.post(
    "/api/auth/reset/request",
    status_code=202,
    response_model=ResetRequestResponse,
    summary="Send a one-time password reset link",
)
def request_reset(body: ResetRequestBody, auth: AuthService = Depends(get_auth)):
    try:
        return auth.request_reset(body.email)
    except AuthError as exc:
        _raise(exc)


@router.post(
    "/api/auth/reset",
    response_model=ResetResponse,
    summary="Reset the password with the one-time token",
)
def reset(body: ResetBody, auth: AuthService = Depends(get_auth)):
    try:
        return auth.reset(body.token, body.new_password)
    except AuthError as exc:
        _raise(exc)
