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
    assert response.json() == {"themes": [], "total": 0, "mastered": 0}


def test_the_tree_lists_themes_and_their_documents(api):
    api.create_active_account("alice@ust.hk")
    _seed_documents(api)
    _seed_outline(api)

    response = api.client.get("/api/revision")

    assert response.status_code == 200
    body = response.json()
    assert [theme["title"] for theme in body["themes"]] == ["Memory and attention"]
    assert body["total"] == 0
    assert body["mastered"] == 0
    documents = body["themes"][0]["documents"]
    assert [document["doc_id"] for document in documents] == [
        "ACS_lecture_2_2026F",
        "Tutorial_4",
    ]
    assert documents[0]["category"] == "lecture"
    assert documents[0]["filename"] == "ACS_lecture_2_2026F.pdf"
    assert documents[0]["generated"] is False
    assert documents[0]["total"] == 0


def _generate(api) -> dict:
    api.app.state.storage.save_revision_document(
        doc_id="Tutorial_4",
        markdown="# Tutorial 4\n\n## Online softmax\n\nBody one.\n\n"
        "## Bank conflicts\n\nBody two.\n",
        intro_markdown="# Tutorial 4",
        points=[
            {"title": "Online softmax", "body_markdown": "Body one.", "page_no": 23},
            {"title": "Bank conflicts", "body_markdown": "Body two.", "page_no": 12},
        ],
        model="deepseek-flash",
        prompt_version="revision-document/1",
        generated_at=api.clock(),
    )
    detail = api.client.get("/api/revision/docs/Tutorial_4").json()
    return detail


def test_a_generated_chapter_returns_its_points(api):
    api.create_active_account("alice@ust.hk")
    _seed_documents(api)
    _seed_outline(api)

    detail = _generate(api)

    assert detail["title"] == "Tutorial_4"
    assert detail["theme_title"] == "Memory and attention"
    assert detail["total"] == 2
    assert detail["mastered"] == 0
    assert [point["title"] for point in detail["points"]] == [
        "Online softmax",
        "Bank conflicts",
    ]
    assert [point["page_no"] for point in detail["points"]] == [23, 12]
    tree = api.client.get("/api/revision").json()
    document = next(
        doc
        for theme in tree["themes"]
        for doc in theme["documents"]
        if doc["doc_id"] == "Tutorial_4"
    )
    assert document["generated"] is True
    assert document["total"] == 2
    assert tree["total"] == 2


def test_marking_a_point_updates_the_document_and_course_counts(api):
    api.create_active_account("alice@ust.hk")
    _seed_documents(api)
    _seed_outline(api)
    detail = _generate(api)

    response = api.client.patch(
        f"/api/revision/points/{detail['points'][0]['id']}",
        json={"mastered": True},
    )

    assert response.status_code == 200
    assert response.json() == {"doc_id": "Tutorial_4", "total": 2, "mastered": 1}
    tree = api.client.get("/api/revision").json()
    assert tree["mastered"] == 1
    assert tree["themes"][0]["mastered"] == 1


def test_an_ungenerated_chapter_is_not_found(api):
    api.create_active_account("alice@ust.hk")
    _seed_documents(api)
    _seed_outline(api)

    response = api.client.get("/api/revision/docs/Tutorial_4")

    assert response.status_code == 404


def test_the_markdown_download_has_no_page_markers(api):
    api.create_active_account("alice@ust.hk")
    _seed_documents(api)
    _seed_outline(api)
    _generate(api)

    response = api.client.get("/api/revision/docs/Tutorial_4/markdown")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert 'filename="Tutorial_4.md"' in response.headers["content-disposition"]
    assert response.text.startswith("# Tutorial_4")
    assert "<!-- page:" not in response.text
    assert "## Online softmax" in response.text


def test_revision_documents_require_sign_in(api):
    assert api.client.get("/api/revision/docs/Tutorial_4").status_code == 401
    assert (
        api.client.get("/api/revision/docs/Tutorial_4/markdown").status_code == 401
    )
    assert (
        api.client.patch(
            "/api/revision/points/abc", json={"mastered": True}
        ).status_code
        == 401
    )
