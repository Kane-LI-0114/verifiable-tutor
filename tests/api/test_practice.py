"""Practice-run scaffold: the interface exists but execution is pending."""

from __future__ import annotations

PRACTICE_UNAVAILABLE = (
    "practice execution is not available: the tacc/exec job is pending (FR-E4)"
)


def test_practice_run_requires_sign_in(api):
    response = api.client.post("/api/practice/runs", json={})

    assert response.status_code == 401


def test_practice_run_reports_the_documented_unavailability(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/practice/runs",
        json={"pack_id": "mpi-gemm", "question_id": "q1", "answer": "int x = 1;"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": PRACTICE_UNAVAILABLE}
