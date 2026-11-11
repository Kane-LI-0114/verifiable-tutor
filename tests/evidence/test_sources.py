"""Turn-scoped source numbering: markers, dedupe, and summary truncation."""

from __future__ import annotations

from verifiable_tutor.evidence.sources import SourceRegistry


def test_course_page_is_numbered_from_one():
    registry = SourceRegistry()

    source = registry.add_course(
        doc_id="ACS_lecture_2_2026F",
        page_no=12,
        title="Lecture 2: Collectives",
        text="MPI_Allreduce combines values from all ranks.",
        chunk_id="ACS_lecture_2_2026F:p012:c00",
    )

    assert source.marker == 1
    assert source.kind == "course"
    assert source.title == "Lecture 2: Collectives"
    assert source.summary == "MPI_Allreduce combines values from all ranks."
    assert source.doc_id == "ACS_lecture_2_2026F"
    assert source.page_no == 12
    assert source.url is None
    assert source.chunk_id == "ACS_lecture_2_2026F:p012:c00"
    assert [item["marker"] for item in registry.snapshot()] == [1]


def test_same_page_reuses_its_marker_and_merges_retrieved_text():
    registry = SourceRegistry()

    first = registry.add_course(
        doc_id="ACS_lecture_2_2026F",
        page_no=12,
        title="Lecture 2: Collectives",
        text="MPI_Allreduce combines values.",
    )
    second = registry.add_course(
        doc_id="ACS_lecture_2_2026F",
        page_no=12,
        title="Lecture 2: Collectives",
        text="It distributes the result to every rank.",
    )

    assert first.marker == 1
    assert second.marker == 1
    assert "MPI_Allreduce combines values." in second.summary
    assert "It distributes the result to every rank." in second.summary
    assert len(registry.snapshot()) == 1


def test_markers_continue_across_retrieval_calls():
    registry = SourceRegistry()

    markers = [
        registry.add_course(
            doc_id="ACS_lecture_2_2026F",
            page_no=12,
            title="Lecture 2",
            text="page twelve",
        ).marker,
        registry.add_course(
            doc_id="ACS_lecture_2_2026F",
            page_no=13,
            title="Lecture 2",
            text="page thirteen",
        ).marker,
        registry.add_course(
            doc_id="ACS_lecture_2_2026F",
            page_no=12,
            title="Lecture 2",
            text="page twelve again",
        ).marker,
        registry.add_course(
            doc_id="course_project",
            page_no=1,
            title="Course Project",
            text="project brief",
        ).marker,
    ]

    assert markers == [1, 2, 1, 3]
    assert [item["marker"] for item in registry.snapshot()] == [1, 2, 3]


def test_web_url_is_deduped_without_the_fragment_and_summary_updates():
    registry = SourceRegistry()
    short = "A short search summary."
    long = "x" * 250

    first = registry.add_web(
        url="https://example.com/guide#search",
        title="Search guide",
        summary=short,
    )
    second = registry.add_web(
        url="https://example.com/guide#fetch",
        title="Search guide: full page",
        summary=long,
    )

    assert first is not None and second is not None
    assert first.marker == 1
    assert second.marker == 1
    assert second.title == "Search guide: full page"
    assert second.summary.endswith("...")
    assert len(second.summary) == 200
    assert len(registry.snapshot()) == 1


def test_course_summary_is_truncated_to_the_fixed_limit():
    registry = SourceRegistry()

    source = registry.add_course(
        doc_id="ACS_lecture_2_2026F",
        page_no=12,
        title="Lecture 2",
        text="x" * 250,
    )

    assert source.summary == "x" * 197 + "..."
    assert len(source.summary) == 200


def test_invalid_web_url_is_ignored():
    registry = SourceRegistry()

    for url in ("javascript:alert(1)", "ftp://example.com/a", "", "not a url"):
        assert registry.add_web(url=url, title="bad", summary="bad") is None

    assert registry.snapshot() == []


def test_snapshot_exposes_plain_dicts_in_marker_order():
    registry = SourceRegistry()
    registry.add_course(
        doc_id="ACS_lecture_2_2026F",
        page_no=12,
        title="Lecture 2",
        text="first",
    )
    registry.add_web(
        url="https://example.com/a",
        title="Example",
        summary="second",
    )

    assert registry.snapshot() == [
        {
            "marker": 1,
            "kind": "course",
            "title": "Lecture 2",
            "summary": "first",
            "doc_id": "ACS_lecture_2_2026F",
            "page_no": 12,
            "url": None,
            "chunk_id": None,
        },
        {
            "marker": 2,
            "kind": "web",
            "title": "Example",
            "summary": "second",
            "doc_id": None,
            "page_no": None,
            "url": "https://example.com/a",
            "chunk_id": None,
        },
    ]
