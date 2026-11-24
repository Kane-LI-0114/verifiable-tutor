"""The chat turn tells the model which assignment deadlines have passed."""

from __future__ import annotations

from verifiable_tutor.llm.adapter import StreamEvent


def _text_events(*chunks: str) -> list[StreamEvent]:
    events = [StreamEvent(kind="text", text=chunk) for chunk in chunks]
    return [*events, StreamEvent(kind="finish", finish_reason="stop")]


def test_chat_tells_the_model_which_assignment_deadlines_passed(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.events = _text_events("Hello")

    response = api.client.post("/api/chat", json={"message": "What is MPI?"})

    assert response.status_code == 200
    messages = api.adapter.calls[0]["messages"]
    system = "\n".join(
        message["content"] for message in messages if message["role"] == "system"
    )
    assert "Assignment 1" in system
    assert "passed" in system
    assert "Assignment 3" in system
    assert "open" in system
