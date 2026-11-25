"""The outline groups every summarised document exactly once."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from verifiable_tutor.revision.category import document_category
from verifiable_tutor.revision.outline import OutlineError, build_outline

DOCUMENTS = [
    {
        "doc_id": "Tutorial_4",
        "title": "Tutorial 4: FlashAttention",
        "filename": "Tutorial_4.pdf",
        "summary": "FlashAttention tiling and online softmax.",
    },
    {
        "doc_id": "ACS_lecture_2_2026F",
        "title": "Memory hierarchy",
        "filename": "ACS_lecture_2_2026F.pdf",
        "summary": "Caches, DRAM, HBM, and CXL.",
    },
    {
        "doc_id": "Assignment_2",
        "title": "Assignment 2",
        "filename": "Assignment_2.pdf",
        "summary": "Implement scaled dot-product attention in CUDA.",
    },
]


class FakeAdapter:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return SimpleNamespace(text=text)


def _themes(*mappings):
    return {
        "themes": [
            {"title": title, "summary": summary, "doc_ids": doc_ids}
            for title, summary, doc_ids in mappings
        ]
    }


def test_categories_follow_the_file_name():
    assert document_category("Assignment_1_final") == "assignment"
    assert document_category("ACS_Lecture_3_2026F") == "lecture"
    assert document_category("Tutorial_6") == "tutorial"
    assert document_category("TACC_Toturial") == "tutorial"
    assert document_category("course_project") == "other"


def test_the_outline_maps_every_document_once():
    adapter = FakeAdapter(
        _themes(
            ("Memory hierarchy", "Caches and memory.", ["ACS_lecture_2_2026F"]),
            ("Attention", "Tiling and softmax.", ["Tutorial_4", "Assignment_2"]),
        )
    )

    themes = build_outline(DOCUMENTS, adapter)

    assert [theme.id for theme in themes] == ["t1", "t2"]
    assert [theme.position for theme in themes] == [0, 1]
    assert themes[1].doc_ids == ("Tutorial_4", "Assignment_2")
    assert "temperature" not in adapter.calls[0]
    prompt = adapter.calls[0]["messages"][0]["content"]
    assert "ACS_lecture_2_2026F" in prompt
    assert "%%DOCUMENTS%%" not in prompt


def test_a_missing_document_is_rejected():
    adapter = FakeAdapter(
        _themes(("Everything", "All of it.", ["Tutorial_4", "Assignment_2"]))
    )

    with pytest.raises(OutlineError, match="missing"):
        build_outline(DOCUMENTS, adapter)


def test_a_duplicate_document_is_rejected():
    adapter = FakeAdapter(
        _themes(
            ("One", "First.", ["Tutorial_4", "ACS_lecture_2_2026F"]),
            ("Two", "Second.", ["Tutorial_4", "Assignment_2"]),
        )
    )

    with pytest.raises(OutlineError, match="more than one theme"):
        build_outline(DOCUMENTS, adapter)


def test_an_unknown_document_is_rejected():
    adapter = FakeAdapter(
        _themes(
            (
                "Everything",
                "All of it.",
                ["Tutorial_4", "ACS_lecture_2_2026F", "Assignment_2", "Ghost"],
            )
        )
    )

    with pytest.raises(OutlineError, match="unknown"):
        build_outline(DOCUMENTS, adapter)


def test_a_fenced_json_object_is_accepted():
    adapter = FakeAdapter(
        "```json\n"
        + json.dumps(
            _themes(
                (
                    "Everything",
                    "All of it.",
                    ["Tutorial_4", "ACS_lecture_2_2026F", "Assignment_2"],
                )
            )
        )
        + "\n```"
    )

    themes = build_outline(DOCUMENTS, adapter)

    assert len(themes) == 1
