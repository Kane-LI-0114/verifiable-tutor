"""Practice generation and model grading HTTP contracts."""

from __future__ import annotations


def test_practice_run_requires_sign_in(api):
    response = api.client.post(
        "/api/practice/runs",
        json={
            "question": "q",
            "answer": "a",
            "reference_answer": "r",
            "scoring_points": ["p"],
            "max_score": 1,
        },
    )

    assert response.status_code == 401


def test_practice_run_grades_with_the_model(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/practice/runs",
        json={
            "question": "What is MPI?",
            "answer": "Message passing",
            "reference_answer": "Message passing interface",
            "scoring_points": ["defines MPI"],
            "max_score": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 2.0
    assert body["max_score"] == 3.0
    assert body["explanation"] == "ok"


def test_practice_generate_requires_sign_in(api):
    response = api.client.post(
        "/api/practice/generate", json={"topic": "FlashAttention"}
    )

    assert response.status_code == 401


def test_practice_generate_returns_questions_and_sources(agent_api):
    agent_api.create_active_account("alice@ust.hk")

    response = agent_api.client.post(
        "/api/practice/generate", json={"topic": "FlashAttention"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["questions"] == []
    assert body["sources"] == []


# Saving a practice session and recording progress are covered by
# tests/api/test_practice_sessions.py, which drives the persisted session flow.

