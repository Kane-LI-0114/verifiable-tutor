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


def test_a_chat_without_context_has_only_the_base_system_prompt(api):
    api.create_active_account("alice@ust.hk")

    api.client.post("/api/chat", json={"message": "hello"})

    assert len(_system_messages(api)) == 1


def test_an_unknown_context_field_is_rejected(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.post(
        "/api/chat",
        json={"message": "hi", "document_context": {"doc_id": "x", "chunk": 3}},
    )

    assert response.status_code == 422
