"""Replay: re-emit a recorded session trace without any model call."""

from __future__ import annotations

from datetime import datetime, timezone

from verifiable_tutor.api.replay import replay_delays

from helpers import parse_sse

TIMESTAMPS = [100.0, 101.0, 103.0, 110.0]


def test_replay_delays_scale_with_speed_and_cap_long_gaps():
    assert replay_delays(TIMESTAMPS, speed=1.0) == [0.0, 1.0, 2.0, 2.0]
    assert replay_delays(TIMESTAMPS, speed=2.0) == [0.0, 0.5, 1.0, 2.0]


def test_replay_requires_sign_in(api):
    response = api.client.get("/api/sessions/unknown/replay")

    assert response.status_code == 401


def test_replay_re_emits_the_recorded_frames(api):
    api.create_active_account("alice@ust.hk")
    live = api.client.post("/api/chat", json={"message": "What is MPI?"})
    session_id = live.headers["x-conversation-id"]
    live_parts = parse_sse(live.text)

    response = api.client.get(f"/api/sessions/{session_id}/replay")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    replay_parts = parse_sse(response.text)
    assert replay_parts[:-1] == live_parts[:-1]
    assert replay_parts[-1] == "[DONE]"
    assert len(api.adapter.calls) == 1


def test_replay_of_an_unknown_conversation_is_not_found(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/sessions/does-not-exist/replay")

    assert response.status_code == 404
    assert response.json() == {"detail": "conversation not found"}


def test_replay_of_a_foreign_conversation_is_not_found(api):
    api.create_active_account("alice@ust.hk")
    created = api.client.post("/api/chat", json={"message": "alice question"})
    session_id = created.headers["x-conversation-id"]

    api.clear_cookies()
    api.register("bob@ust.hk")
    api.verify("bob@ust.hk")
    api.login("bob@ust.hk")
    response = api.client.get(f"/api/sessions/{session_id}/replay")

    assert response.status_code == 404


def test_replay_without_a_recorded_trace_is_not_found(api):
    api.create_active_account("alice@ust.hk")
    created = api.client.post("/api/chat", json={"message": "alice question"})
    session_id = created.headers["x-conversation-id"]
    user_id = api.client.get("/api/auth/me").json()["id"]
    trace_path = api.settings.trace_dir / user_id / f"{session_id}.jsonl"
    assert trace_path.is_file()
    trace_path.unlink()

    response = api.client.get(f"/api/sessions/{session_id}/replay")

    assert response.status_code == 404
    assert response.json() == {"detail": "no replay trace"}


def test_replay_rejects_an_out_of_range_speed(api):
    api.create_active_account("alice@ust.hk")
    created = api.client.post("/api/chat", json={"message": "alice question"})
    session_id = created.headers["x-conversation-id"]

    assert api.client.get(f"/api/sessions/{session_id}/replay?speed=0").status_code == 422
    assert api.client.get(f"/api/sessions/{session_id}/replay?speed=50").status_code == 422


def test_replay_sleeps_for_recorded_gaps(api):
    api.create_active_account("alice@ust.hk")
    created = api.client.post("/api/chat", json={"message": "alice question"})
    session_id = created.headers["x-conversation-id"]
    user_id = api.client.get("/api/auth/me").json()["id"]
    trace_path = api.settings.trace_dir / user_id / f"{session_id}.jsonl"

    # Rewrite the recorded frame timestamps so the replay has measurable gaps.
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    rewritten: list[str] = []
    frame_index = 0
    import json

    for line in lines:
        record = json.loads(line)
        if record["kind"] == "frame":
            record["ts"] = 1000.0 + frame_index * 0.5
            frame_index += 1
        rewritten.append(json.dumps(record))
    trace_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")

    response = api.client.get(f"/api/sessions/{session_id}/replay")

    assert response.status_code == 200
    assert api.sleep_calls == [0.5] * (frame_index - 1)
