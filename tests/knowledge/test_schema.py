from verifiable_tutor.knowledge.schema import (
    normalize_text,
    quote_on_page,
    validate_progress,
    validate_record,
)

PAGE_TEXT = (
    "Course Project\nBuilding an End-to-End Agent System\n"
    "Advanced AI Computing and Systems"
)
PAGES = {("course_project", 1): PAGE_TEXT}


def valid_record() -> dict:
    return {
        "schema": "vt-kb-record/1",
        "build_id": "kb-20261102-01",
        "job_id": "28001",
        "chunk_id": "course_project:p001:c00",
        "doc_id": "course_project",
        "page_no": 1,
        "section": "Course Project",
        "source_block_ids": ["0", "1"],
        "summary": "The page introduces the course project and its title.",
        "key_terms": ["course project", "agent system"],
        "study_questions": [
            "What is the title of the course project?",
            "Which systems course does the page belong to?",
        ],
        "citations": [
            {
                "doc_id": "course_project",
                "page_no": 1,
                "quote": "Building an End-to-End Agent System",
            }
        ],
        "model": "qwen3.8-27b",
        "prompt_version": "kb-v1",
        "corpus_hash": "abc123",
        "created_at": "2026-11-02T02:00:00+00:00",
    }


def test_validate_record_accepts_a_complete_record() -> None:
    assert validate_record(valid_record(), PAGES) == []


def test_validate_record_requires_a_summary() -> None:
    record = valid_record()
    del record["summary"]

    assert any("summary" in issue for issue in validate_record(record, PAGES))


def test_validate_record_limits_key_terms_to_eight() -> None:
    record = valid_record()
    record["key_terms"] = [f"term{i}" for i in range(9)]

    assert any("key_terms" in issue for issue in validate_record(record, PAGES))


def test_validate_record_requires_two_study_questions() -> None:
    record = valid_record()
    record["study_questions"] = ["only one question"]

    assert any(
        "study_questions" in issue for issue in validate_record(record, PAGES)
    )


def test_validate_record_rejects_a_quote_missing_from_the_page() -> None:
    record = valid_record()
    record["citations"][0]["quote"] = "this sentence is not on the page"

    assert any("quote" in issue for issue in validate_record(record, PAGES))


def test_validate_record_accepts_a_quote_with_different_spacing_and_case() -> None:
    record = valid_record()
    record["citations"][0]["quote"] = "  building an end-to-end   agent system  "

    assert validate_record(record, PAGES) == []


def test_validate_record_rejects_a_citation_to_an_unknown_page() -> None:
    record = valid_record()
    record["citations"][0]["page_no"] = 99

    assert any("page_no" in issue or "page 99" in issue for issue in validate_record(record, PAGES))


def test_validate_record_rejects_a_non_integer_page_number() -> None:
    record = valid_record()
    record["page_no"] = "1"

    assert any("page_no" in issue for issue in validate_record(record, PAGES))


def test_validate_record_rejects_no_citations() -> None:
    record = valid_record()
    record["citations"] = []

    assert any("citations" in issue for issue in validate_record(record, PAGES))


def test_normalize_text_collapses_whitespace_and_case() -> None:
    assert normalize_text("  Building\n an  END-to-end ") == "building an end-to-end"


def test_quote_on_page_uses_normalized_text() -> None:
    assert quote_on_page("building an end-to-end agent system", PAGE_TEXT)
    assert not quote_on_page("missing sentence", PAGE_TEXT)


def valid_progress() -> dict:
    return {
        "schema": "vt-kb-progress/1",
        "build_id": "kb-20261102-01",
        "job_id": "28001",
        "status": "done",
        "done_chunks": 2,
        "total_chunks": 2,
        "error": None,
        "updated_at": "2026-11-02T02:01:00+00:00",
    }


def test_validate_progress_accepts_a_done_progress() -> None:
    assert validate_progress(valid_progress()) == []


def test_validate_progress_rejects_an_unknown_status() -> None:
    progress = valid_progress()
    progress["status"] = "finished"

    assert any("status" in issue for issue in validate_progress(progress))


def test_validate_progress_rejects_more_done_than_total() -> None:
    progress = valid_progress()
    progress["done_chunks"] = 3

    assert any("done_chunks" in issue for issue in validate_progress(progress))
