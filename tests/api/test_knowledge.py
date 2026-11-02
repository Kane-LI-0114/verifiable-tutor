"""Knowledge-base card browsing and build lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

PASSWORD = "correct-horse-battery"

CARD_ONE = {
    "build_id": "kb-20261102-01",
    "chunk_id": "course_project:p001:c00",
    "doc_id": "course_project",
    "page_no": 1,
    "section": "Course Project",
    "summary": "This page introduces the course project.",
    "key_terms": ["Course Project", "Agent System"],
    "study_questions": ["What is the course project?", "Which system is built?"],
    "citations": [
        {"doc_id": "course_project", "page_no": 1, "quote": "Course Project"}
    ],
    "model": "qwen3.8-27b",
    "prompt_version": "kb-v1",
    "created_at": "2026-11-02T03:02:12+00:00",
}
CARD_TWO = {
    **CARD_ONE,
    "chunk_id": "mpi:p0012:c03",
    "doc_id": "mpi",
    "page_no": 12,
    "section": "Collective operations",
    "summary": "MPI_Allreduce combines values across ranks.",
    "key_terms": ["MPI_Allreduce", "Collective"],
    "created_at": "2026-11-02T04:00:00+00:00",
}


def _write_cards(api, *cards: dict) -> None:
    directory = api.settings.knowledge_records_dir
    directory.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(card, ensure_ascii=False) for card in cards]
    (directory / "kb-test.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_cards_require_sign_in(api):
    assert api.client.get("/api/knowledge/cards").status_code == 401


def test_cards_are_empty_when_no_build_has_been_downloaded(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/knowledge/cards")

    assert response.status_code == 200
    assert response.json() == {"cards": [], "total": 0}


def test_cards_are_listed_with_their_citations(api):
    api.create_active_account("alice@ust.hk")
    _write_cards(api, CARD_ONE, CARD_TWO)

    response = api.client.get("/api/knowledge/cards")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [card["chunk_id"] for card in body["cards"]] == [
        CARD_ONE["chunk_id"],
        CARD_TWO["chunk_id"],
    ]
    first = body["cards"][0]
    assert first["summary"] == CARD_ONE["summary"]
    assert first["key_terms"] == CARD_ONE["key_terms"]
    assert first["citations"] == CARD_ONE["citations"]
    assert first["prompt_version"] == "kb-v1"


def test_cards_filter_by_doc_id_and_query(api):
    api.create_active_account("alice@ust.hk")
    _write_cards(api, CARD_ONE, CARD_TWO)

    by_doc = api.client.get("/api/knowledge/cards?doc_id=mpi").json()
    by_query = api.client.get("/api/knowledge/cards?q=allreduce").json()

    assert by_doc["total"] == 1
    assert by_doc["cards"][0]["doc_id"] == "mpi"
    assert by_query["total"] == 1
    assert by_query["cards"][0]["chunk_id"] == CARD_TWO["chunk_id"]


def test_cards_paginate(api):
    api.create_active_account("alice@ust.hk")
    _write_cards(api, CARD_ONE, CARD_TWO)

    response = api.client.get("/api/knowledge/cards?limit=1&offset=1")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["cards"]) == 1
    assert response.json()["cards"][0]["chunk_id"] == CARD_TWO["chunk_id"]


def test_cards_skip_malformed_lines(api):
    api.create_active_account("alice@ust.hk")
    directory = api.settings.knowledge_records_dir
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "kb-test.jsonl").write_text(
        '{"chunk_id": "broken"\n' + json.dumps(CARD_ONE) + "\n",
        encoding="utf-8",
    )

    response = api.client.get("/api/knowledge/cards")

    assert response.status_code == 200
    assert response.json()["total"] == 1


# -- builds -------------------------------------------------------------


def test_builds_require_the_instructor_role(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post("/api/knowledge/builds", json={})

    assert response.status_code == 403
    assert response.json() == {"detail": "instructor role is required"}
    assert api.client.get("/api/knowledge/builds").status_code == 403


def test_build_submission_is_unavailable_without_a_pages_path(api):
    api.create_instructor("teacher@ust.hk")

    response = api.client.post("/api/knowledge/builds", json={"doc_id": "course_project"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "knowledge-base build is not configured: set "
        "knowledge.pages_path in config/app.yaml"
    }


def test_instructor_can_submit_a_build_and_watch_it_finish(kb_api):
    kb_api.create_instructor("teacher@ust.hk")

    response = kb_api.client.post(
        "/api/knowledge/builds", json={"doc_id": "course_project", "max_chunks": 4}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["state"] == "queued"
    assert body["build_id"].startswith("kb-")
    build = kb_api.client.get(f"/api/knowledge/builds/{body['build_id']}")
    assert build.status_code == 200
    detail = build.json()
    assert detail["state"] == "ready"
    assert detail["job_id"] == "28067"
    assert detail["records_count"] == 8
    assert kb_api.runner.calls == [
        {"build_id": body["build_id"], "doc_id": "course_project", "max_chunks": 4}
    ]
    listing = kb_api.client.get("/api/knowledge/builds").json()
    assert [item["id"] for item in listing["builds"]] == [body["build_id"]]


def test_build_failure_is_recorded(kb_api):
    kb_api.create_instructor("teacher@ust.hk")
    kb_api.runner.error = RuntimeError("driver failed")

    created = kb_api.client.post("/api/knowledge/builds", json={})

    build = kb_api.client.get(f"/api/knowledge/builds/{created.json()['build_id']}")
    assert build.status_code == 200
    assert build.json()["state"] == "failed"
    assert "driver failed" in build.json()["error"]


def test_a_second_build_is_rejected_while_one_is_active(kb_api):
    kb_api.create_instructor("teacher@ust.hk")
    now = kb_api.clock()
    instructor = kb_api.app.state.storage.find_user_by_email("teacher@ust.hk")
    kb_api.app.state.storage.create_build(
        build_id="kb-active",
        user_id=instructor["id"],
        request_json="{}",
        created_at=now,
    )

    response = kb_api.client.post("/api/knowledge/builds", json={})

    assert response.status_code == 409
    assert response.json() == {
        "detail": "a knowledge-base build is already running"
    }


def test_unknown_build_is_not_found(kb_api):
    kb_api.create_instructor("teacher@ust.hk")

    response = kb_api.client.get("/api/knowledge/builds/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "build not found"}
