"""Tool calls persist their provider id, arguments, result, and duration."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from verifiable_tutor.storage import Storage

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


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


def _tool_call(**overrides):
    call = {
        "tool_call_id": "call_1",
        "name": "search_course",
        "arguments": {"query": "MPI_Allreduce", "k": 3},
        "result": {"chunks": [{"doc_id": "Tutorial_2", "page_no": 8}]},
        "output": "3 course chunks",
        "command": [],
        "exit_code": None,
        "status": "done",
        "duration_ms": 42,
    }
    call.update(overrides)
    return call


def _turn(storage: Storage, **overrides):
    values = {
        "message_id": "msg-2",
        "conversation_id": "conv-1",
        "sequence": 2,
        "content": "It reduces across ranks.",
        "created_at": NOW,
        "provider": "deepseek",
        "tier": "flash",
        "model": "deepseek-flash",
        "thinking": "off",
        "steps": [{"step": "generate", "status": "done"}],
        "tool_calls": [_tool_call()],
    }
    values.update(overrides)
    return storage.add_assistant_turn(**values)


def test_tool_call_provider_fields_round_trip(tmp_path):
    storage = _seeded_storage(tmp_path)

    _turn(storage)

    assistant = storage.list_messages("conv-1")[1]
    assert len(assistant["tool_calls"]) == 1
    call = assistant["tool_calls"][0]
    assert call["tool_call_id"] == "call_1"
    assert call["name"] == "search_course"
    assert call["arguments"] == {"query": "MPI_Allreduce", "k": 3}
    assert call["result"] == {"chunks": [{"doc_id": "Tutorial_2", "page_no": 8}]}
    assert call["output"] == "3 course chunks"
    assert call["command"] == []
    assert call["exit_code"] is None
    assert call["status"] == "done"
    assert call["duration_ms"] == 42


def test_legacy_tool_call_columns_are_null(tmp_path):
    storage = _seeded_storage(tmp_path)

    _turn(
        storage,
        tool_calls=[
            {
                "name": "course_search",
                "command": ["rg", "MPI_Allreduce"],
                "exit_code": 0,
                "output": "found 2 pages",
                "status": "done",
            }
        ],
    )

    call = storage.list_messages("conv-1")[1]["tool_calls"][0]
    assert call["tool_call_id"] is None
    assert call["arguments"] is None
    assert call["result"] is None
    assert call["duration_ms"] is None


def test_work_chain_events_keep_reasoning_and_tool_calls_in_order(tmp_path):
    storage = _seeded_storage(tmp_path)

    _turn(
        storage,
        steps=[
            {"id": "step-generate", "step": "generate", "status": "done"},
            {"id": "step-retrieve", "step": "retrieve", "status": "done"},
        ],
        events=[
            {
                "kind": "reasoning",
                "reasoning": "I should search the course.",
                "step_id": "step-generate",
            },
            {
                "kind": "tool_call",
                "tool_call_position": 0,
                "step_id": "step-retrieve",
            },
        ],
        tool_calls=[_tool_call()],
    )

    assistant = storage.list_messages("conv-1")[1]
    assert [event["kind"] for event in assistant["events"]] == [
        "reasoning",
        "tool_call",
    ]
    assert [event["step_id"] for event in assistant["events"]] == [
        "step-generate",
        "step-retrieve",
    ]
    assert assistant["events"][0]["reasoning"] == "I should search the course."
    assert assistant["events"][0]["tool_call"] is None
    assert assistant["events"][1]["tool_call"]["name"] == "search_course"
    assert assistant["events"][1]["tool_call"]["tool_call_id"] == "call_1"


def test_a_legacy_event_without_a_step_reads_as_null(tmp_path):
    storage = _seeded_storage(tmp_path)

    _turn(
        storage,
        events=[{"kind": "reasoning", "reasoning": "No step was recorded."}],
        tool_calls=[],
    )

    assert storage.list_messages("conv-1")[1]["events"][0]["step_id"] is None


def test_a_reasoning_event_without_text_rolls_back_the_whole_turn(tmp_path):
    storage = _seeded_storage(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        _turn(
            storage,
            events=[{"kind": "reasoning", "reasoning": None}],
            tool_calls=[],
        )

    assert [message["role"] for message in storage.list_messages("conv-1")] == [
        "user"
    ]


def test_an_invalid_tool_status_rolls_back_the_whole_turn(tmp_path):
    storage = _seeded_storage(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        _turn(storage, tool_calls=[_tool_call(status="not-a-status")])

    messages = storage.list_messages("conv-1")
    assert [message["role"] for message in messages] == ["user"]
