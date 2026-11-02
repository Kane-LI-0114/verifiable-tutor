"""Liveness and schema contract for the HTTP API."""


def test_health_reports_ok(api):
    response = api.client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "database": "ok",
    }


def test_openapi_lists_health(api):
    schema = api.client.get("/openapi.json").json()

    assert "/api/health" in schema["paths"]
