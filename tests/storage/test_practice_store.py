"""Practice sessions persist generated questions before the first answer.

The first attempt owns the session status; later attempts only contribute to
the best score. These tests pin the storage seam: create, resume with saved
answers, submit, redo, list, and delete.
"""

from __future__ import annotations

from datetime import datetime, timezone

from verifiable_tutor.storage import Storage

CREATED = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 11, 25, 9, 10, tzinfo=timezone.utc)
FINISHED = datetime(2026, 11, 25, 9, 20, tzinfo=timezone.utc)

QUESTIONS = (
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
)


def _storage(tmp_path) -> Storage:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    storage.create_user(
        user_id="user-1",
        email="alice@ust.hk",
        password_hash="hash",
        role="student",
        status="active",
        created_at=CREATED,
    )
    return storage


def _create(storage: Storage) -> None:
    storage.create_practice_session(
        conversation_id="practice-1",
        user_id="user-1",
        title="MPI",
        topic="MPI",
        questions=QUESTIONS,
        sources=({"marker": 1, "kind": "course", "title": "MPI"},),
        created_at=CREATED,
    )


def test_generation_persists_questions_before_any_answer(tmp_path):
    storage = _storage(tmp_path)

    _create(storage)

    session = storage.find_practice_session("practice-1")
    assert session is not None
    assert session["status"] == "not_started"
    assert session["max_score"] == 5
    assert [question["id"] for question in session["questions"]] == ["q1", "q2"]
    attempts = storage.list_practice_attempts("practice-1")
    assert len(attempts) == 1
    assert attempts[0]["attempt_no"] == 1
    assert attempts[0]["status"] == "in_progress"
    assert attempts[0]["answers"] == {}


def test_saving_the_first_answer_starts_the_session(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)

    storage.save_practice_answers(
        conversation_id="practice-1",
        attempt_no=1,
        answers={"q1": ["MPI_Allreduce"]},
        updated_at=LATER,
    )

    session = storage.find_practice_session("practice-1")
    assert session is not None
    assert session["status"] == "in_progress"
    attempt = storage.find_practice_attempt("practice-1", 1)
    assert attempt is not None
    assert attempt["answers"] == {"q1": ["MPI_Allreduce"]}


def test_first_submission_completes_the_session_and_sets_the_best_score(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)

    storage.submit_practice_attempt(
        conversation_id="practice-1",
        attempt_no=1,
        answers={"q1": ["MPI_Allreduce"], "q2": ["to the root"]},
        results={
            "q1": {"score": 2, "max_score": 2, "explanation": "correct"},
            "q2": {"score": 2, "max_score": 3, "explanation": "partial"},
        },
        submitted_at=FINISHED,
    )

    session = storage.find_practice_session("practice-1")
    assert session is not None
    assert session["status"] == "completed"
    assert session["best_score"] == 4
    assert session["completed_at"] == FINISHED.isoformat()
    attempt = storage.find_practice_attempt("practice-1", 1)
    assert attempt is not None
    assert attempt["status"] == "completed"
    assert attempt["score"] == 4
    assert attempt["results"]["q2"]["explanation"] == "partial"


def test_a_redo_keeps_the_session_status_and_raises_only_the_best_score(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)
    storage.submit_practice_attempt(
        conversation_id="practice-1",
        attempt_no=1,
        answers={"q1": ["MPI_Allreduce"]},
        results={"q1": {"score": 2, "max_score": 2, "explanation": "ok"}},
        submitted_at=FINISHED,
    )

    redo = storage.start_practice_attempt(
        conversation_id="practice-1", started_at=LATER
    )
    assert redo["attempt_no"] == 2

    storage.submit_practice_attempt(
        conversation_id="practice-1",
        attempt_no=2,
        answers={"q1": ["MPI_Allreduce"], "q2": ["to the root"]},
        results={
            "q1": {"score": 2, "max_score": 2, "explanation": "ok"},
            "q2": {"score": 3, "max_score": 3, "explanation": "ok"},
        },
        submitted_at=FINISHED,
    )

    session = storage.find_practice_session("practice-1")
    assert session is not None
    assert session["status"] == "completed"
    assert session["best_score"] == 5
    assert len(storage.list_practice_attempts("practice-1")) == 2


def test_a_legacy_practice_conversation_lists_without_a_practice_row(tmp_path):
    storage = _storage(tmp_path)
    storage.create_conversation(
        conversation_id="legacy-1",
        user_id="user-1",
        title="Old practice",
        created_at=CREATED,
        kind="practice",
    )
    _create(storage)

    rows = storage.list_conversations("user-1")
    legacy = next(row for row in rows if row["id"] == "legacy-1")
    assert legacy["has_practice"] == 0
    assert legacy["practice_status"] is None

    current = next(row for row in rows if row["id"] == "practice-1")
    assert current["has_practice"] == 1
    assert current["practice_status"] == "not_started"

    only_practice = storage.list_conversations("user-1", kind="practice")
    assert {row["id"] for row in only_practice} == {"legacy-1", "practice-1"}


def test_deleting_a_practice_session_removes_its_attempts(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)

    deleted = storage.delete_conversation("practice-1", "user-1")

    assert deleted is True
    assert storage.find_practice_session("practice-1") is None
    assert storage.list_practice_attempts("practice-1") == []
    assert storage.find_conversation("practice-1") is None


def _submit(storage: Storage, attempt_no: int, score: int, max_score: int) -> None:
    storage.submit_practice_attempt(
        conversation_id="practice-1",
        attempt_no=attempt_no,
        answers={"q1": ["MPI_Allreduce"]},
        results={
            "q1": {
                "score": score,
                "max_score": max_score,
                "explanation": "ok",
            }
        },
        submitted_at=FINISHED,
    )


def test_deleting_one_attempt_keeps_the_session_and_renumbers(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)
    _submit(storage, 1, 2, 2)
    storage.start_practice_attempt(conversation_id="practice-1", started_at=LATER)
    _submit(storage, 2, 5, 3)

    remaining = storage.delete_practice_attempt(
        conversation_id="practice-1",
        attempt_no=2,
        updated_at=FINISHED,
    )

    assert remaining is not None
    assert remaining["status"] == "completed"
    assert remaining["best_score"] == 2
    attempts = storage.list_practice_attempts("practice-1")
    assert [attempt["attempt_no"] for attempt in attempts] == [1]
    assert attempts[0]["score"] == 2


def test_deleting_the_first_attempt_promotes_the_next_one(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)
    _submit(storage, 1, 2, 2)
    storage.start_practice_attempt(conversation_id="practice-1", started_at=LATER)
    _submit(storage, 2, 5, 3)

    remaining = storage.delete_practice_attempt(
        conversation_id="practice-1",
        attempt_no=1,
        updated_at=FINISHED,
    )

    assert remaining is not None
    assert remaining["status"] == "completed"
    assert remaining["best_score"] == 5
    attempts = storage.list_practice_attempts("practice-1")
    assert [attempt["attempt_no"] for attempt in attempts] == [1]
    assert attempts[0]["score"] == 5


def test_deleting_the_last_attempt_removes_the_session(tmp_path):
    storage = _storage(tmp_path)
    _create(storage)

    remaining = storage.delete_practice_attempt(
        conversation_id="practice-1",
        attempt_no=1,
        updated_at=FINISHED,
    )

    assert remaining is None
    assert storage.find_practice_session("practice-1") is None
    assert storage.find_conversation("practice-1") is None
