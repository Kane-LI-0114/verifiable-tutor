"""The revision outline stores themes and maps every document to one theme."""

from __future__ import annotations

from datetime import datetime, timezone

from verifiable_tutor.storage import Storage

NOW = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)


def _storage(tmp_path) -> Storage:
    storage = Storage(tmp_path / "app.sqlite3")
    storage.initialize()
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

    themes = storage.list_revision_tree()

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

    themes = storage.list_revision_tree()
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
