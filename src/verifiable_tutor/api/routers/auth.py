"""Account routes: registration, verification, sessions, and password reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict

from ...auth.service import AuthError, AuthService
from ..deps import CurrentUser, SettingsDep, get_auth
from ..schemas import (
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
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "student@ust.hk",
                "password": "correct-horse-battery",
            }
        },
    )

    email: str
    password: str


class VerifyBody(_StrictBody):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"email": "student@ust.hk", "code": "123456"}
        },
    )

    email: str
    code: str


class LoginBody(_StrictBody):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "student@ust.hk",
                "password": "correct-horse-battery",
            }
        },
    )

    email: str
    password: str


class ResetRequestBody(_StrictBody):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"email": "student@ust.hk"}},
    )

    email: str


class ResetBody(_StrictBody):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "token": "one-time-reset-token",
                "new_password": "new-password-123",
            }
        },
    )

    token: str
    new_password: str


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
