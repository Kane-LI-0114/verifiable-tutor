"""The revision outline stores themes and maps every document to one theme."""

from __future__ import annotations

from datetime import datetime, timezone

from verifiable_tutor.storage import Storage

NOW = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)


def _storage(tmp_path) -> Storage:
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
    with storage.connect() as connection:
        for doc_id, filename in (
            ("Tutorial_4", "Tutorial_4.pdf"),
            ("ACS_lecture_2_2026F", "ACS_lecture_2_2026F.pdf"),
            ("course_project", "course_project.pdf"),
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
                    NOW.isoformat(),
                    NOW.isoformat(),
                    f"Summary of {doc_id}",
                ),
            )
    return storage


def _outline(storage: Storage) -> None:
    storage.replace_revision_outline(
        themes=[
            {
                "id": "attention",
                "title": "Attention and FlashAttention",
                "summary": "How attention works and why tiling matters.",
                "position": 0,
            },
            {
                "id": "systems",
                "title": "Systems and projects",
                "summary": "The course project and its platform.",
                "position": 1,
            },
        ],
        documents=[
            {"doc_id": "Tutorial_4", "theme_id": "attention", "category": "tutorial"},
            {
                "doc_id": "ACS_lecture_2_2026F",
                "theme_id": "attention",
                "category": "lecture",
            },
            {
                "doc_id": "course_project",
                "theme_id": "systems",
                "category": "other",
            },
        ],
        created_at=NOW,
        model="deepseek-flash",
        prompt_version="revision-outline/1",
    )


def test_the_outline_lists_themes_in_order_with_their_documents(tmp_path):
    storage = _storage(tmp_path)
    _outline(storage)

    themes = storage.list_revision_tree("user-1")

    assert [theme["title"] for theme in themes] == [
        "Attention and FlashAttention",
        "Systems and projects",
    ]
    assert [doc["doc_id"] for doc in themes[0]["documents"]] == [
        "ACS_lecture_2_2026F",
        "Tutorial_4",
    ]
    assert themes[0]["documents"][0]["category"] == "lecture"
    assert themes[0]["documents"][1]["category"] == "tutorial"
    assert themes[1]["documents"][0]["category"] == "other"


def test_replacing_the_outline_removes_the_previous_one(tmp_path):
    storage = _storage(tmp_path)
    _outline(storage)

    storage.replace_revision_outline(
        themes=[
            {
                "id": "one",
                "title": "One theme",
                "summary": "Everything.",
                "position": 0,
            }
        ],
        documents=[
            {"doc_id": "Tutorial_4", "theme_id": "one", "category": "tutorial"}
        ],
        created_at=NOW,
        model="deepseek-flash",
        prompt_version="revision-outline/1",
    )

    themes = storage.list_revision_tree("user-1")
    assert len(themes) == 1
    assert [doc["doc_id"] for doc in themes[0]["documents"]] == ["Tutorial_4"]


def test_candidates_are_the_summarised_documents(tmp_path):
    storage = _storage(tmp_path)

    candidates = storage.list_revision_candidates()

    assert {row["doc_id"] for row in candidates} == {
        "Tutorial_4",
        "ACS_lecture_2_2026F",
        "course_project",
    }
    assert candidates[0]["summary"]


def test_generated_points_and_progress_reach_the_tree(tmp_path):
    storage = _storage(tmp_path)
    _outline(storage)

    saved = storage.save_revision_document(
        doc_id="Tutorial_4",
        markdown="# Tutorial 4\n\n## First point\n\nBody one.\n\n## Second point\n\nBody two.\n",
        intro_markdown="# Tutorial 4",
        points=[
            {"title": "First point", "body_markdown": "Body one.", "page_no": 3},
            {"title": "Second point", "body_markdown": "Body two.", "page_no": 4},
        ],
        model="deepseek-flash",
        prompt_version="revision-document/1",
        generated_at=NOW,
    )
    assert saved == 2

    detail = storage.revision_document_detail("Tutorial_4", "user-1")
    assert detail is not None
    assert detail["total"] == 2
    assert detail["mastered"] == 0
    assert [point["page_no"] for point in detail["points"]] == [3, 4]

    updated = storage.set_revision_progress(
        user_id="user-1",
        point_id=detail["points"][0]["id"],
        mastered=True,
        updated_at=NOW,
    )
    assert updated == {"doc_id": "Tutorial_4", "total": 2, "mastered": 1}

    themes = storage.list_revision_tree("user-1")
    attention = next(theme for theme in themes if theme["id"] == "attention")
    document = next(
        doc for doc in attention["documents"] if doc["doc_id"] == "Tutorial_4"
    )
    assert document["generated"] is True
    assert document["total"] == 2
    assert document["mastered"] == 1
    assert attention["total"] == 2
    assert attention["mastered"] == 1


def test_an_ungenerated_document_has_no_detail(tmp_path):
    storage = _storage(tmp_path)
    _outline(storage)

    assert storage.revision_document_detail("Tutorial_4", "user-1") is None


def test_a_snapshot_round_trips_without_user_progress(tmp_path):
    source = _storage(tmp_path)
    _outline(source)
    source.save_revision_document(
        doc_id="Tutorial_4",
        markdown="# Tutorial 4\n\n## First point\n\nBody one.\n",
        intro_markdown="# Tutorial 4",
        points=[
            {"title": "First point", "body_markdown": "Body one.", "page_no": 3}
        ],
        model="deepseek-flash",
        prompt_version="revision-document/2",
        generated_at=NOW,
    )
    source_detail = source.revision_document_detail("Tutorial_4", "user-1")
    assert source_detail is not None
    source.set_revision_progress(
        user_id="user-1",
        point_id=source_detail["points"][0]["id"],
        mastered=True,
        updated_at=NOW,
    )
    snapshot = source.revision_snapshot()

    target = Storage(tmp_path / "target.sqlite3")
    target.initialize()
    with target.connect() as connection:
        for doc_id, filename in (
            ("Tutorial_4", "Tutorial_4.pdf"),
            ("ACS_lecture_2_2026F", "ACS_lecture_2_2026F.pdf"),
            ("course_project", "course_project.pdf"),
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
                    NOW.isoformat(),
                    NOW.isoformat(),
                    f"Summary of {doc_id}",
                ),
            )
    result = target.import_revision_snapshot(snapshot, imported_at=NOW)

    assert result == {"imported": True, "themes": 2, "documents": 3, "points": 1}
    detail = target.revision_document_detail("Tutorial_4", "user-1")
    assert detail is not None
    assert detail["total"] == 1
    assert detail["mastered"] == 0
    assert detail["document"]["markdown"].startswith("# Tutorial 4")
    assert target.list_revision_tree("user-1")[0]["total"] == 1

    again = target.import_revision_snapshot(snapshot, imported_at=NOW)
    assert again["imported"] is False


