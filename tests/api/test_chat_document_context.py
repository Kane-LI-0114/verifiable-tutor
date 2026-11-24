"""The chat prompt names the document and page open in the preview."""

from __future__ import annotations


def _system_messages(api) -> list[str]:
    call = api.adapter.calls[-1]
    return [
        message["content"]
        for message in call["messages"]
        if message["role"] == "system"
    ]


def test_the_open_document_and_page_reach_the_prompt(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/chat",
        json={
            "message": "explain this page",
            "document_context": {"doc_id": "ACS_Lecture_1_2026F", "page_no": 7},
        },
    )

    assert response.status_code == 200
    systems = _system_messages(api)
    assert any("ACS_Lecture_1_2026F" in text and "Page: 7" in text for text in systems)


def test_a_chat_without_context_has_the_base_prompt_and_the_deadline_note(api):
    api.create_active_account("alice@ust.hk")

    api.client.post("/api/chat", json={"message": "hello"})

    systems = _system_messages(api)
    assert len(systems) == 2
    assert systems[0].startswith("You are a tutor for the CSIT6000V course")
    assert "Assignment deadlines as of" in systems[1]


def test_an_unknown_context_field_is_rejected(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/chat",
        json={"message": "hi", "document_context": {"doc_id": "x", "chunk": 3}},
    )

    assert response.status_code == 422
