"""The review chapter merges batches and drops repeated points."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from verifiable_tutor.revision.document import DocumentError
from verifiable_tutor.revision.generate import build_document


class FakeAdapter:
    def __init__(self, texts) -> None:
        self.texts = list(texts)
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return SimpleNamespace(text=self.texts.pop(0))


def _chunks(*pages):
    return [
        {"page_no": page, "section": "", "text": "x" * 7000}
        for page in pages
    ]


def test_one_batch_returns_a_clean_chapter():
    adapter = FakeAdapter(
        [
            "Overview.\n\n## Online softmax <!-- page: 23 -->\n\nBody.\n\n"
            "## Bank conflicts <!-- page: 12 -->\n\nBody two.\n"
        ]
    )

    document = build_document(
        title="Tutorial 4",
        filename="Tutorial_4.pdf",
        chunks=_chunks(10),
        adapter=adapter,
    )

    assert document.batches == 1
    assert document.intro_markdown == "Overview."
    assert [point.title for point in document.points] == [
        "Online softmax",
        "Bank conflicts",
    ]
    assert "<!-- page:" not in document.markdown


def test_long_documents_are_batched_and_duplicates_are_dropped():
    adapter = FakeAdapter(
        [
            "First overview.\n\n## Shared point <!-- page: 1 -->\n\nFirst body.\n",
            "Second overview.\n\n## Shared point <!-- page: 2 -->\n\nAgain.\n\n"
            "## New point <!-- page: 3 -->\n\nNew body.\n",
        ]
    )

    document = build_document(
        title="Lecture",
        filename="Lecture.pdf",
        chunks=_chunks(1, 2),
        adapter=adapter,
        overview="Whole document overview.",
    )

    assert adapter.calls == 2
    assert document.batches == 2
    assert document.intro_markdown == "Whole document overview."
    assert [point.title for point in document.points] == ["Shared point", "New point"]
    assert document.points[0].body_markdown == "First body."


def test_a_document_without_chunks_is_rejected():
    with pytest.raises(DocumentError, match="no OCR chunks"):
        build_document(
            title="Empty",
            filename="Empty.pdf",
            chunks=[],
            adapter=FakeAdapter([]),
        )


def test_a_batch_without_points_is_rejected():
    adapter = FakeAdapter(["Nothing structured."])

    with pytest.raises(DocumentError, match="no knowledge points"):
        build_document(
            title="Lecture",
            filename="Lecture.pdf",
            chunks=_chunks(1),
            adapter=adapter,
        )
