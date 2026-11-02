import pytest

from verifiable_tutor.knowledge.chunks import chunks_from_pages, normalize_doc_id

PAGE_TEXT = "Course Project\nBuilding an End-to-End Agent System"
PAGES = [
    {
        "schema": "vt-page-record/1",
        "doc_id": "20261029-203110-360-course_project",
        "pdf": "20261029-203110-360-course_project.pdf",
        "page_no": 1,
        "text": PAGE_TEXT,
        "blocks": [
            {
                "block_id": 0,
                "block_order": 1,
                "label": "paragraph_title",
                "content": "Course Project",
            },
            {
                "block_id": 1,
                "block_order": 2,
                "label": "text",
                "content": "Building an End-to-End Agent System",
            },
            {
                "block_id": 3,
                "block_order": None,
                "label": "footer_image",
                "content": "",
            },
        ],
    },
    {
        "schema": "vt-page-record/1",
        "doc_id": "20261029-203110-360-course_project",
        "pdf": "20261029-203110-360-course_project.pdf",
        "page_no": 2,
        "text": "   \n  ",
        "blocks": [],
    },
    {
        "schema": "vt-page-record/1",
        "doc_id": "20261029-203110-360-course_project",
        "pdf": "20261029-203110-360-course_project.pdf",
        "page_no": 3,
        "text": "Lecture notes about MPI",
        "blocks": [],
    },
]


def test_normalize_doc_id_strips_the_request_prefix() -> None:
    assert normalize_doc_id("20261029-203110-360-course_project") == "course_project"
    assert normalize_doc_id("course_project") == "course_project"


def test_chunks_from_pages_carry_the_request_contract() -> None:
    chunks = chunks_from_pages(PAGES)

    assert len(chunks) == 2
    first = chunks[0]
    assert set(first) == {
        "chunk_id",
        "doc_id",
        "page_no",
        "section",
        "source_block_ids",
        "text",
    }
    assert first["chunk_id"] == "course_project:p001:c00"
    assert first["doc_id"] == "course_project"
    assert first["page_no"] == 1
    assert first["section"] == "Course Project"
    assert first["source_block_ids"] == ["0", "1"]
    assert first["text"] == PAGE_TEXT


def test_chunks_from_pages_skip_pages_without_text() -> None:
    chunks = chunks_from_pages(PAGES)

    assert [chunk["page_no"] for chunk in chunks] == [1, 3]


def test_chunks_from_pages_respect_max_chunks() -> None:
    chunks = chunks_from_pages(PAGES, max_chunks=1)

    assert [chunk["page_no"] for chunk in chunks] == [1]


def test_chunks_from_pages_accept_an_explicit_doc_id() -> None:
    chunks = chunks_from_pages(PAGES, doc_id="course_project")

    assert chunks[0]["doc_id"] == "course_project"
    assert chunks[0]["chunk_id"] == "course_project:p001:c00"


def test_chunks_from_pages_without_text_returns_empty() -> None:
    assert chunks_from_pages([PAGES[1]]) == []


def test_chunks_from_pages_rejects_non_positive_max_chunks() -> None:
    with pytest.raises(ValueError):
        chunks_from_pages(PAGES, max_chunks=0)
