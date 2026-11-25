"""Practice sessions: generation persists, answers resume, redos do not rewrite status."""

from __future__ import annotations

import json

from verifiable_tutor.llm.adapter import StreamEvent

QUESTIONS = [
    {
        "type": "single-choice",
        "topic": "MPI",
        "question": "Which collective leaves the result on every rank?",
        "choices": ["MPI_Allreduce", "MPI_Reduce"],
        "correct_answer": "MPI_Allreduce",
        "reference_answer": "MPI_Allreduce.",
        "scoring_points": ["names Allreduce"],
        "max_score": 2,
        "knowledge_points": ["collectives"],
    },
    {
        "type": "short-answer",
        "topic": "MPI",
        "question": "What does MPI_Reduce do?",
        "choices": [],
        "correct_answer": "",
        "reference_answer": "Reduces to the root rank.",
        "scoring_points": ["names the root rank"],
        "max_score": 3,
        "knowledge_points": ["collectives"],
    },
]


def _script_questions(harness, questions=QUESTIONS) -> None:
    harness.adapter.events = [
        StreamEvent(kind="text", text=json.dumps(questions)),
        StreamEvent(kind="finish", finish_reason="stop"),
    ]


def _create(harness) -> dict:
    _script_questions(harness)
    response = harness.client.post(
        "/api/practice/sessions", json={"topic": "MPI"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_generation_requires_sign_in(api):
    response = api.client.post("/api/practice/sessions", json={"topic": "MPI"})

    assert response.status_code == 401


def test_generation_persists_the_questions_before_the_first_answer(agent_api):
    agent_api.create_active_account("alice@ust.hk")

    body = _create(agent_api)

    assert body["status"] == "not_started"
    assert body["max_score"] == 5
    assert [question["id"] for question in body["questions"]] == ["q1", "q2"]
    assert len(body["attempts"]) == 1
    assert body["attempts"][0]["attempt_no"] == 1
    assert body["attempts"][0]["answers"] == {}
    assert set(body["attempts"][0]["option_orders"]["q1"]) == {
        "MPI_Allreduce",
        "MPI_Reduce",
    }

    reloaded = agent_api.client.get(f"/api/practice/sessions/{body['id']}")
    assert reloaded.status_code == 200
    assert [q["id"] for q in reloaded.json()["questions"]] == ["q1", "q2"]


def test_generation_without_questions_stores_nothing(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    agent_api.adapter.events = [
        StreamEvent(kind="text", text="Sorry, I cannot."),
        StreamEvent(kind="finish", finish_reason="stop"),
    ]

    response = agent_api.client.post(
        "/api/practice/sessions", json={"topic": "MPI"}
    )

    assert response.status_code == 502
    sessions = agent_api.client.get("/api/sessions").json()["sessions"]
    assert [session for session in sessions if session["kind"] == "practice"] == []


def test_saved_answers_resume_after_a_reload(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)

    saved = agent_api.client.patch(
        f"/api/practice/sessions/{body['id']}/attempts/1/answers",
        json={"answers": {"q1": ["MPI_Allreduce"]}},
    )

    assert saved.status_code == 200
    assert saved.json()["status"] == "in_progress"
    reloaded = agent_api.client.get(f"/api/practice/sessions/{body['id']}").json()
    assert reloaded["status"] == "in_progress"
    assert reloaded["attempts"][0]["answers"] == {"q1": ["MPI_Allreduce"]}


def test_first_submission_completes_the_session(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)

    response = agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/1/submit",
        json={
            "answers": {"q1": ["MPI_Allreduce"], "q2": ["to the root"]},
            "results": {
                "q1": {"score": 2, "max_score": 2, "explanation": "correct"},
                "q2": {"score": 1, "max_score": 3, "explanation": "partial"},
            },
        },
    )

    assert response.status_code == 200, response.text
    session = response.json()
    assert session["status"] == "completed"
    assert session["best_score"] == 3
    assert session["attempts"][0]["status"] == "completed"


def test_a_redo_keeps_the_status_and_only_raises_the_best_score(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)
    agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/1/submit",
        json={
            "answers": {"q1": ["MPI_Allreduce"]},
            "results": {"q1": {"score": 2, "max_score": 2, "explanation": "ok"}},
        },
    )

    redo = agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts"
    )
    assert redo.status_code == 201, redo.text
    assert [attempt["attempt_no"] for attempt in redo.json()["attempts"]] == [1, 2]

    submitted = agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/2/submit",
        json={
            "answers": {"q1": ["MPI_Allreduce"], "q2": ["to the root"]},
            "results": {
                "q1": {"score": 2, "max_score": 2, "explanation": "ok"},
                "q2": {"score": 3, "max_score": 3, "explanation": "ok"},
            },
        },
    )

    assert submitted.status_code == 200
    session = submitted.json()
    assert session["status"] == "completed"
    assert session["best_score"] == 5
    assert session["attempts"][1]["status"] == "completed"


def test_a_redo_cannot_start_before_the_first_attempt_is_submitted(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)

    response = agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts"
    )

    assert response.status_code == 409


def test_a_second_redo_cannot_start_while_one_is_open(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)
    agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/1/submit",
        json={"answers": {}, "results": {}},
    )

    first = agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts"
    )
    assert first.status_code == 201
    second = agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts"
    )

    assert second.status_code == 409
    session = agent_api.client.get(f"/api/practice/sessions/{body['id']}").json()
    assert [attempt["attempt_no"] for attempt in session["attempts"]] == [1, 2]


def test_sessions_list_carries_the_practice_status_and_can_filter(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    practice = _create(agent_api)
    chat = agent_api.client.post("/api/chat", json={"message": "What is MPI?"})
    assert chat.status_code == 200

    sessions = agent_api.client.get("/api/sessions").json()["sessions"]
    listed = next(item for item in sessions if item["id"] == practice["id"])
    assert listed["has_practice"] is True
    assert listed["practice_status"] == "not_started"
    assert listed["practice_best_score"] == 0

    only_practice = agent_api.client.get(
        "/api/sessions", params={"kind": "practice"}
    ).json()["sessions"]
    assert [item["id"] for item in only_practice] == [practice["id"]]


def test_a_legacy_practice_conversation_lists_without_a_session_row(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    agent_api.app.state.storage.create_conversation(
        conversation_id="legacy-1",
        user_id=agent_api.client.get("/api/auth/me").json()["id"],
        title="Old practice",
        created_at=agent_api.clock(),
        kind="practice",
    )

    sessions = agent_api.client.get(
        "/api/sessions", params={"kind": "practice"}
    ).json()["sessions"]

    legacy = next(item for item in sessions if item["id"] == "legacy-1")
    assert legacy["has_practice"] is False
    assert legacy["practice_status"] is None


def test_deleting_a_practice_session_hides_it_from_the_list(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)

    deleted = agent_api.client.delete(f"/api/practice/sessions/{body['id']}")

    assert deleted.status_code == 204
    assert (
        agent_api.client.get(f"/api/practice/sessions/{body['id']}").status_code
        == 404
    )
    sessions = agent_api.client.get("/api/sessions").json()["sessions"]
    assert [item for item in sessions if item["id"] == body["id"]] == []


def test_first_submission_records_knowledge_progress(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)

    agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/1/submit",
        json={
            "answers": {"q1": ["MPI_Allreduce"], "q2": ["to the root"]},
            "results": {
                "q1": {"score": 2, "max_score": 2, "explanation": "ok"},
                "q2": {"score": 0, "max_score": 3, "explanation": "no"},
            },
        },
    )

    topics = agent_api.client.get("/api/profile/mastery").json()["topics"]
    mpi = next(topic for topic in topics if topic["topic"] == "MPI")
    assert mpi["covered_count"] == 1
    assert mpi["mastered_count"] == 1


def test_deleting_one_attempt_keeps_the_session(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)
    agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/1/submit",
        json={
            "answers": {"q1": ["MPI_Allreduce"]},
            "results": {"q1": {"score": 2, "max_score": 2, "explanation": "ok"}},
        },
    )
    agent_api.client.post(f"/api/practice/sessions/{body['id']}/attempts")
    agent_api.client.post(
        f"/api/practice/sessions/{body['id']}/attempts/2/submit",
        json={
            "answers": {"q1": ["MPI_Allreduce"], "q2": ["to the root"]},
            "results": {
                "q1": {"score": 2, "max_score": 2, "explanation": "ok"},
                "q2": {"score": 3, "max_score": 3, "explanation": "ok"},
            },
        },
    )

    deleted = agent_api.client.delete(
        f"/api/practice/sessions/{body['id']}/attempts/2"
    )

    assert deleted.status_code == 204
    session = agent_api.client.get(f"/api/practice/sessions/{body['id']}").json()
    assert [attempt["attempt_no"] for attempt in session["attempts"]] == [1]
    assert session["best_score"] == 2
    assert session["status"] == "completed"


def test_deleting_the_last_attempt_removes_the_session(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)

    deleted = agent_api.client.delete(
        f"/api/practice/sessions/{body['id']}/attempts/1"
    )

    assert deleted.status_code == 204
    assert (
        agent_api.client.get(f"/api/practice/sessions/{body['id']}").status_code
        == 404
    )
    sessions = agent_api.client.get("/api/sessions").json()["sessions"]
    assert [item for item in sessions if item["id"] == body["id"]] == []


def test_a_practice_session_is_private_to_its_owner(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    body = _create(agent_api)
    agent_api.clear_cookies()
    agent_api.create_active_account("bob@ust.hk")

    response = agent_api.client.get(f"/api/practice/sessions/{body['id']}")

    assert response.status_code == 404
