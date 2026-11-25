"""The generated chapter splits on H2 headings and hides the page markers."""

from __future__ import annotations

import pytest

from verifiable_tutor.revision.document import DocumentError, parse_document

SAMPLE = """An overview of the chapter.

## Online softmax <!-- page: 23 -->

Online softmax keeps a running maximum and normaliser.

### Why it matters

It avoids a second pass over the rows.

```python
## this is a comment inside a code block
```

## Bank conflicts <!-- page: 12 -->

Shared memory is split into banks.
"""


def test_the_parser_splits_points_and_extracts_pages():
    parsed = parse_document(SAMPLE)

    assert parsed.intro_markdown == "An overview of the chapter."
    assert [point.title for point in parsed.points] == [
        "Online softmax",
        "Bank conflicts",
    ]
    assert [point.page_no for point in parsed.points] == [23, 12]
    assert "### Why it matters" in parsed.points[0].body_markdown
    assert "## this is a comment" in parsed.points[0].body_markdown


def test_the_clean_markdown_has_no_page_comments():
    parsed = parse_document(SAMPLE)

    assert "<!-- page:" not in parsed.markdown
    assert parsed.markdown.startswith("An overview of the chapter.")
    assert "## Online softmax\n" in parsed.markdown
    assert "## Bank conflicts\n" in parsed.markdown


def test_a_missing_page_comment_is_allowed():
    parsed = parse_document("## A point\n\nBody.")

    assert parsed.points[0].page_no is None


def test_a_document_without_points_is_rejected():
    with pytest.raises(DocumentError, match="no knowledge points"):
        parse_document("Only an introduction.")


def test_duplicate_headings_keep_the_first_one():
    parsed = parse_document(
        "## Same point <!-- page: 1 -->\n\nFirst.\n\n"
        "## Same point <!-- page: 2 -->\n\nSecond.\n"
    )

    assert len(parsed.points) == 1
    assert parsed.points[0].body_markdown == "First."
