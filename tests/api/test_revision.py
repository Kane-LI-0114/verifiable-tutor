"""The revision guide HTTP contract."""

from __future__ import annotations


def _seed_documents(api) -> None:
    with api.app.state.storage.connect() as connection:
        for doc_id, filename in (
            ("Tutorial_4", "Tutorial_4.pdf"),
            ("ACS_lecture_2_2026F", "ACS_lecture_2_2026F.pdf"),
        ):
            connection.execute(
                "INSERT INTO kb_documents"
                " (id, title, filename, pdf_sha256, page_count, pdf_path, status,"
                "  created_at, updated_at, summary)"
                " VALUES (?, ?, ?, ?, 10, ?, 'ready', ?, ?, ?)",
                (
                    doc_id,
                    doc_id,
                    filename,
                    f"sha-{doc_id}",
                    f"data/{filename}",
                    api.clock().isoformat(),
                    api.clock().isoformat(),
                    f"Summary of {doc_id}",
                ),
            )


def _seed_outline(api) -> None:
    api.app.state.storage.replace_revision_outline(
        themes=[
            {
                "id": "t1",
                "title": "Memory and attention",
                "summary": "How data movement shapes attention.",
                "position": 0,
            }
        ],
        documents=[
            {
                "doc_id": "ACS_lecture_2_2026F",
                "theme_id": "t1",
                "category": "lecture",
            },
            {"doc_id": "Tutorial_4", "theme_id": "t1", "category": "tutorial"},
        ],
        created_at=api.clock(),
        model="deepseek-flash",
        prompt_version="revision-outline/1",
    )


def test_revision_requires_sign_in(api):
    response = api.client.get("/api/revision")

    assert response.status_code == 401


def test_a_new_database_has_no_revision_themes(api):
    api.create_active_account("alice@ust.hk")

    response = api.client.get("/api/revision")

    assert response.status_code == 200
    assert response.json() == {"themes": []}


def test_the_tree_lists_themes_and_their_documents(api):
    api.create_active_account("alice@ust.hk")
    _seed_documents(api)
    _seed_outline(api)

    response = api.client.get("/api/revision")

    assert response.status_code == 200
    body = response.json()
    assert [theme["title"] for theme in body["themes"]] == ["Memory and attention"]
    documents = body["themes"][0]["documents"]
    assert [document["doc_id"] for document in documents] == [
        "ACS_lecture_2_2026F",
        "Tutorial_4",
    ]
    assert documents[0]["category"] == "lecture"
    assert documents[0]["filename"] == "ACS_lecture_2_2026F.pdf"
