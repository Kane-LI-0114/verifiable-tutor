"""The agent loop over HTTP: frames, persistence, history, trace, and replay."""

from __future__ import annotations

import json

from verifiable_tutor.llm.adapter import StreamEvent, ToolCallDelta

from helpers import parse_sse


def tool_script(name="search_course", arguments='{"query":"MPI_Allreduce","k":2}', call_id="call_1"):
    return [
        StreamEvent(
            kind="tool_call",
            tool_call=ToolCallDelta(
                index=0, id=call_id, name=name, arguments_delta=arguments
            ),
        ),
        StreamEvent(kind="finish", finish_reason="tool_calls"),
    ]


def text_script(text="Allreduce sums a value across ranks."):
    return [
        StreamEvent(kind="text", text=text),
        StreamEvent(kind="finish", finish_reason="stop"),
    ]


def sse_types(response):
    parts = parse_sse(response.text)
    return [part if part == "[DONE]" else part["type"] for part in parts], parts


def test_history_replays_reasoning_content_for_tool_requests(api):
    api.create_active_account("alice@ust.hk")
    api.adapter.events = [
        StreamEvent(kind="reasoning", text="Think before answering."),
        StreamEvent(kind="text", text="First answer."),
        StreamEvent(kind="finish", finish_reason="stop"),
    ]

    first = api.client.post("/api/chat", json={"message": "First question"})
    session_id = first.headers["x-conversation-id"]
    api.adapter.events = [
        StreamEvent(kind="text", text="Second answer."),
        StreamEvent(kind="finish", finish_reason="stop"),
    ]

    api.client.post(
        "/api/chat", json={"message": "Second question", "session_id": session_id}
    )

    history = api.adapter.calls[1]["messages"]
    assistant = [message for message in history if message["role"] == "assistant"][0]
    assert assistant["reasoning_content"] == "Think before answering."


def test_agent_streams_tool_frames_and_persists_the_call(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    agent_api.adapter.scripts = [tool_script(), text_script()]

    response = agent_api.client.post("/api/chat", json={"message": "What is MPI_Allreduce?"})

    assert response.status_code == 200
    types, parts = sse_types(response)
    assert types[0] == "start"
    assert types.count("start-step") == 2
    assert types.count("finish-step") == 2
    assert types.count("data-tool") == 2
    assert types.count("data-step") == 4
    assert "finish" in types

    tool_frames = [
        part for part in parts if isinstance(part, dict) and part["type"] == "data-tool"
    ]
    assert [frame["data"]["status"] for frame in tool_frames] == ["running", "done"]
    assert tool_frames[0]["data"]["name"] == "search_course"
    assert tool_frames[0]["data"]["arguments"] == {"query": "MPI_Allreduce", "k": 2}
    assert tool_frames[1]["data"]["output"] == "1 course chunks"

    # Both calls see the tool set, and the second one gets the tool result.
    assert agent_api.adapter.calls[0]["kwargs"]["tools"]
    assert agent_api.adapter.calls[1]["kwargs"]["tools"]
    tool_messages = [
        message
        for message in agent_api.adapter.calls[1]["messages"]
        if message["role"] == "tool"
    ]
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0]["content"])["chunks"][0]["doc_id"] == "Tutorial_2"

    session_id = response.headers["x-conversation-id"]
    history = agent_api.client.get(f"/api/sessions/{session_id}/messages").json()
    assistant = history["messages"][1]
    assert assistant["content"] == "Allreduce sums a value across ranks."
    assert len(assistant["tool_calls"]) == 1
    call = assistant["tool_calls"][0]
    assert call["tool_call_id"] == "call_1"
    assert call["name"] == "search_course"
    assert call["arguments"] == {"query": "MPI_Allreduce", "k": 2}
    assert call["result"]["chunks"][0]["doc_id"] == "Tutorial_2"
    assert call["output"] == "1 course chunks"
    assert call["status"] == "done"
    assert call["duration_ms"] is not None


def test_agent_persists_reasoning_before_each_tool_call(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    first_call = [
        StreamEvent(kind="reasoning", text="I should search the course pages."),
        *tool_script(),
    ]
    second_call = [
        StreamEvent(kind="reasoning", text="Now answer from the retrieved pages."),
        *text_script("Allreduce sums a value across ranks."),
    ]
    agent_api.adapter.scripts = [first_call, second_call]

    response = agent_api.client.post("/api/chat", json={"message": "What is MPI?"})

    assert response.status_code == 200
    session_id = response.headers["x-conversation-id"]
    assistant = agent_api.client.get(
        f"/api/sessions/{session_id}/messages"
    ).json()["messages"][1]
    events = assistant["events"]
    assert [event["kind"] for event in events] == [
        "reasoning",
        "tool_call",
        "reasoning",
    ]
    assert events[0]["reasoning"] == "I should search the course pages."
    assert events[0]["tool_call"] is None
    assert events[1]["tool_call"]["name"] == "search_course"
    assert events[1]["tool_call"]["status"] == "done"
    assert events[2]["reasoning"] == "Now answer from the retrieved pages."


def test_agent_records_tool_frames_in_the_trace_and_replays_them(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    agent_api.adapter.scripts = [tool_script(), text_script()]

    response = agent_api.client.post("/api/chat", json={"message": "What is MPI?"})
    session_id = response.headers["x-conversation-id"]
    user_id = agent_api.client.get("/api/auth/me").json()["id"]

    trace_path = agent_api.settings.trace_dir / user_id / f"{session_id}.jsonl"
    frames = [
        record["frame"]
        for record in (
            json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()
        )
        if record["kind"] == "frame"
    ]
    assert any(frame["type"] == "data-tool" for frame in frames)

    replay = agent_api.client.get(f"/api/sessions/{session_id}/replay")
    replay_types, replay_parts = sse_types(replay)
    assert replay_types.count("data-tool") == 2
    assert "Allreduce" in replay.text


def test_unknown_tool_is_recorded_as_failed_and_the_turn_finishes(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    agent_api.adapter.scripts = [
        tool_script(name="delete_everything", arguments="{}", call_id="call_x"),
        text_script("I cannot do that."),
    ]

    response = agent_api.client.post("/api/chat", json={"message": "delete the corpus"})

    assert response.status_code == 200
    session_id = response.headers["x-conversation-id"]
    assistant = agent_api.client.get(
        f"/api/sessions/{session_id}/messages"
    ).json()["messages"][1]
    assert assistant["tool_calls"][0]["status"] == "failed"
    assert assistant["content"] == "I cannot do that."


def test_web_search_tool_can_run_through_the_agent(agent_api):
    agent_api.create_active_account("alice@ust.hk")
    agent_api.adapter.scripts = [
        tool_script(
            name="web_search",
            arguments='{"query":"DeepSeek V4","count":3}',
            call_id="call_web",
        ),
        text_script("The release is external news."),
    ]

    response = agent_api.client.post("/api/chat", json={"message": "What is new?"})

    assert response.status_code == 200
    session_id = response.headers["x-conversation-id"]
    assistant = agent_api.client.get(
        f"/api/sessions/{session_id}/messages"
    ).json()["messages"][1]
    assert assistant["tool_calls"][0]["name"] == "web_search"
    assert assistant["tool_calls"][0]["result"]["untrusted"] is True
