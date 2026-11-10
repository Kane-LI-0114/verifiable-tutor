"""The OpenAPI schema lists the known interface surface."""

from __future__ import annotations

EXPECTED = {
    "get": [
        "/api/health",
        "/api/auth/me",
        "/api/auth/domains",
        "/api/sessions",
        "/api/sessions/{session_id}/messages",
        "/api/sessions/{session_id}/replay",
        "/api/knowledge/cards",
        "/api/knowledge/builds",
        "/api/knowledge/builds/{build_id}",
        "/api/corpus/{doc_id}/pages/{page_no}.webp",
    ],
    "post": [
        "/api/auth/register",
        "/api/auth/verify",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/reset/request",
        "/api/auth/reset",
        "/api/chat",
        "/api/voice/transcriptions",
        "/api/voice/speech",
        "/api/voice/speech/stream",
        "/api/knowledge/builds",
        "/api/practice/runs",
    ],
}


def test_openapi_contains_the_known_interface_surface(api):
    schema = api.client.get("/openapi.json").json()
    paths = schema["paths"]

    missing = [
        f"{method.upper()} {route}"
        for method, routes in EXPECTED.items()
        for route in routes
        if method not in paths.get(route, {})
    ]
    assert missing == []


def test_built_ui_is_served_from_the_same_origin(ui_api):
    ui_api.create_active_account("alice@ust.hk")

    response = ui_api.client.get("/")

    assert response.status_code == 200
    assert "built ui" in response.text

    health = ui_api.client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_browser_navigation_to_a_spa_route_returns_the_shell(ui_api):
    """A deep link is a browser navigation: the shell must answer, not a 404.

    Characterization guard for ``app.frontend(fallback="auto")``: the fallback
    applies only when the request accepts HTML, so a ``*/*`` client still gets
    a 404 while a browser navigation gets the SPA entry point.
    """

    browser = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    for path in ("/login", "/chat/demo", "/practice", "/instructor/builds"):
        response = ui_api.client.get(path, headers=browser)
        assert response.status_code == 200, path
        assert "built ui" in response.text, path

    api_client = ui_api.client.get("/api/health", headers={"accept": "application/json"})
    assert api_client.status_code == 200
    assert api_client.headers["content-type"].startswith("application/json")
