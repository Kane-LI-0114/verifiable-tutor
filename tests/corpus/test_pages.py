"""The page-record reader seam.

Seam: ``read_pages(path)``. It catches a page file that is not the
``vt-page-record/1`` contract or that carries an OCR request prefix in its
document id; it does not catch content-level OCR errors (an empty page still
reads as a page).
"""

import json
from pathlib import Path

import pytest

from verifiable_tutor.corpus.pages import read_pages


def page_record(doc_id: str, page_no: int, text: str = "slide text") -> dict:
    return {
        "schema": "vt-page-record/1",
        "doc_id": doc_id,
        "pdf": f"{doc_id}.pdf",
        "page_no": page_no,
        "text": text,
        "blocks": [],
    }


def write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    return path


def test_read_pages_normalizes_the_ocr_request_prefix(tmp_path: Path) -> None:
    pages_path = write_jsonl(
        tmp_path / "pages.jsonl",
        [
            page_record("20261029-203110-360-course_project", 1, "first"),
            page_record("20261029-203110-360-course_project", 2, "second"),
        ],
    )

    pages = read_pages(pages_path)

    assert [page["doc_id"] for page in pages] == ["course_project", "course_project"]
    assert [page["page_no"] for page in pages] == [1, 2]


def test_read_pages_returns_the_pages_in_page_order(tmp_path: Path) -> None:
    pages_path = write_jsonl(
        tmp_path / "pages.jsonl",
        [page_record("ACS_Lecture_1_2026F", 3), page_record("ACS_Lecture_1_2026F", 1)],
    )

    pages = read_pages(pages_path)

    assert [page["page_no"] for page in pages] == [1, 3]


def test_read_pages_refuses_a_record_from_another_schema(tmp_path: Path) -> None:
    record = page_record("course_project", 1)
    record["schema"] = "vt-page-record/0"
    pages_path = write_jsonl(tmp_path / "pages.jsonl", [record])

    with pytest.raises(ValueError, match="vt-page-record/1"):
        read_pages(pages_path)


def test_read_pages_refuses_a_page_without_a_page_number(tmp_path: Path) -> None:
    record = page_record("course_project", 1)
    record.pop("page_no")
    pages_path = write_jsonl(tmp_path / "pages.jsonl", [record])

    with pytest.raises(ValueError, match="page_no"):
        read_pages(pages_path)
