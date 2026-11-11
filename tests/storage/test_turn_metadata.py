"""Assistant turns persist their display metadata with the answer text."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from verifiable_tutor.storage import Storage

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def _seeded_storage(tmp_path) -> Storage:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
    storage.create_user(
        user_id="user-1",
        email="alice@ust.hk",
        password_hash="hash",
        role="student",
        status="active",
        created_at=NOW,
    )
    storage.create_conversation(
        conversation_id="conv-1",
        user_id="user-1",
        title="MPI question",
        created_at=NOW,
    )
    storage.add_message(
        message_id="msg-1",
        conversation_id="conv-1",
        sequence=1,
        role="user",
        content="How does MPI_Allreduce work?",
        created_at=NOW,
    )
    return storage


def _assistant_turn(storage: Storage, **overrides) -> dict:
    values = {
        "message_id": "msg-2",
        "conversation_id": "conv-1",
        "sequence": 2,
        "content": "It reduces across ranks.",
        "created_at": NOW,
        "provider": "deepseek",
        "tier": "flash",
        "model": "deepseek-flash",
        "thinking": "high",
        "reasoning": "The question asks about a collective.",
        "steps": [
            {"step": "understand", "status": "done", "duration_ms": 12},
            {"step": "generate", "status": "done", "detail": "model answer"},
        ],
        "citations": [
            {
                "doc_id": "ACS_lecture_2",
                "page_no": 3,
                "quoted_span": "reduces the value across all ranks",
                "bbox_norm": [0.1, 0.2, 0.3, 0.4],
            },
            {
                "doc_id": "course_project",
                "page_no": 1,
                "quoted_span": "end-to-end agent system",
            },
        ],
        "tool_calls": [
            {
                "name": "course_search",
                "command": ["rg", "MPI_Allreduce"],
                "exit_code": 0,
                "output": "found 2 pages",
                "status": "done",
            }
        ],
    }
    values.update(overrides)
    return storage.add_assistant_turn(**values)


def test_assistant_turn_metadata_round_trips(tmp_path):
    storage = _seeded_storage(tmp_path)

    _assistant_turn(storage)

    messages = storage.list_messages("conv-1")
    assert [message["role"] for message in messages] == ["user", "assistant"]
    user, assistant = messages

    assert user["reasoning"] is None
    assert user["model"] is None
    assert user["thinking"] is None
    assert user["work_steps"] == []
    assert user["citations"] == []
    assert user["tool_calls"] == []

    assert assistant["reasoning"] == "The question asks about a collective."
    assert assistant["model"] == "deepseek-flash"
    assert assistant["thinking"] == "high"
    assert [step["step"] for step in assistant["work_steps"]] == [
        "understand",
        "generate",
    ]
    assert [step["position"] for step in assistant["work_steps"]] == [0, 1]
    assert assistant["work_steps"][1]["detail"] == "model answer"
    assert assistant["work_steps"][0]["status"] == "done"

    assert [citation["quoted_span"] for citation in assistant["citations"]] == [
        "reduces the value across all ranks",
        "end-to-end agent system",
    ]
    assert assistant["citations"][0]["bbox_norm"] == [0.1, 0.2, 0.3, 0.4]
    assert assistant["citations"][1]["bbox_norm"] is None

    assert assistant["tool_calls"][0]["command"] == ["rg", "MPI_Allreduce"]
    assert assistant["tool_calls"][0]["exit_code"] == 0
    assert assistant["tool_calls"][0]["status"] == "done"


def test_assistant_sources_round_trip(tmp_path):
    storage = _seeded_storage(tmp_path)

    _assistant_turn(
        storage,
        sources=[
            {
                "marker": 1,
                "kind": "course",
                "title": "Lecture 2: Collectives",
                "summary": "MPI_Allreduce combines values from all ranks.",
                "doc_id": "ACS_lecture_2",
                "page_no": 12,
                "url": None,
                "chunk_id": "ACS_lecture_2:p012:c00",
            },
            {
                "marker": 2,
                "kind": "web",
                "title": "DeepSeek API documentation",
                "summary": "Search API reference.",
                "doc_id": None,
                "page_no": None,
                "url": "https://api-docs.deepseek.com/guides/search",
                "chunk_id": None,
            },
        ],
    )

    messages = storage.list_messages("conv-1")
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["sources"] == []
    assert messages[1]["sources"] == [
        {
            "position": 0,
            "marker": 1,
            "kind": "course",
            "title": "Lecture 2: Collectives",
            "summary": "MPI_Allreduce combines values from all ranks.",
            "doc_id": "ACS_lecture_2",
            "page_no": 12,
            "url": None,
            "chunk_id": "ACS_lecture_2:p012:c00",
        },
        {
            "position": 1,
            "marker": 2,
            "kind": "web",
            "title": "DeepSeek API documentation",
            "summary": "Search API reference.",
            "doc_id": None,
            "page_no": None,
            "url": "https://api-docs.deepseek.com/guides/search",
            "chunk_id": None,
        },
    ]


def test_an_invalid_step_rolls_back_the_whole_turn(tmp_path):
    storage = _seeded_storage(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        _assistant_turn(
            storage,
            steps=[{"step": "generate", "status": "not-a-status"}],
        )

    assert [message["role"] for message in storage.list_messages("conv-1")] == [
        "user"
    ]
