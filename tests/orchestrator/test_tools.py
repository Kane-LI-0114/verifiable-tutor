"""The typed tool registry: schemas, validation, dispatch, and safe failures."""

from __future__ import annotations

import json
from types import SimpleNamespace

from verifiable_tutor.llm.adapter import FetchResult, SearchResult
from verifiable_tutor.orchestrator.builtin_tools import build_tool_registry
from verifiable_tutor.orchestrator.tools import ToolContext


class FakeSettings:
    agent_web_tools_enabled = True
    agent_max_tool_output_chars = 4000


class FakeRetriever:
    def __init__(self, chunks=None):
        self.chunks = chunks if chunks is not None else []

    def search(self, plan, *, k=8):
        return SimpleNamespace(chunks=self.chunks[:k], lexical=True, dense=False, plan=plan)


class FakeStore:
    def __init__(self, pages=None):
        self.pages = pages or {}

    def page_chunks(self, doc_id: str, page_no: int):
        return self.pages.get((doc_id, page_no), [])


class FakeAdapter:
    def __init__(self, search_results=None, page=None, fail_search=False, fail_fetch=False):
        self.search_results = search_results or []
        self.page = page
        self.fail_search = fail_search
        self.fail_fetch = fail_fetch
        self.search_calls: list[dict] = []
        self.fetch_calls: list[str] = []

    def search(self, query: str, *, count=None, need_content=None):
        self.search_calls.append(
            {"query": query, "count": count, "need_content": need_content}
        )
        if self.fail_search:
            raise RuntimeError("provider exploded with secret sk-test")
        return list(self.search_results)

    def fetch(self, url: str):
        self.fetch_calls.append(url)
        if self.fail_fetch:
            raise RuntimeError("provider exploded with secret sk-test")
        return self.page


def context(*, retriever=None, store=None, adapter=None, settings=None):
    return ToolContext(
        adapter=adapter,
        retriever=retriever or FakeRetriever(),
        store=store or FakeStore(),
        settings=settings or FakeSettings(),
    )


def registry(**kwargs):
    settings = kwargs.pop("settings", None) or FakeSettings()
    return build_tool_registry(settings=settings)


def chunk(doc_id="Tutorial_2", page_no=8):
    return {
        "id": f"{doc_id}:p{page_no:03d}:c00",
        "doc_id": doc_id,
        "page_no": page_no,
        "section": "Collectives",
        "text": "MPI_Allreduce reduces a value across all ranks.",
    }


def test_registry_lists_the_closed_tool_set_with_json_schemas():
    tool_registry = registry()

    assert tool_registry.names() == [
        "search_course",
        "read_course_page",
        "verify_span",
        "web_search",
        "web_fetch",
    ]
    specs = tool_registry.specs()
    names = [spec["function"]["name"] for spec in specs]
    assert names == tool_registry.names()
    for spec in specs:
        assert spec["type"] == "function"
        assert spec["function"]["parameters"]["type"] == "object"
        assert "properties" in spec["function"]["parameters"]


def test_web_tools_can_be_disabled():
    class NoWeb(FakeSettings):
        agent_web_tools_enabled = False

    tool_registry = build_tool_registry(settings=NoWeb())

    assert tool_registry.names() == ["search_course", "read_course_page", "verify_span"]


def test_unknown_tool_is_a_failed_result_not_an_exception():
    result = registry().execute("delete_everything", "{}", context=context())

    assert result.status == "failed"
    assert "unknown tool" in result.output


def test_invalid_json_and_invalid_arguments_are_failed_results():
    tool_registry = registry()

    bad_json = tool_registry.execute("search_course", "{not json", context=context())
    assert bad_json.status == "failed"
    assert "invalid arguments" in bad_json.output

    bad_args = tool_registry.execute(
        "search_course", {"query": "", "k": 3}, context=context()
    )
    assert bad_args.status == "failed"
    assert "invalid arguments" in bad_args.output


def test_search_course_returns_page_anchored_chunks():
    tool_registry = registry()
    retriever = FakeRetriever([chunk()])

    result = tool_registry.execute(
        "search_course",
        {"query": "MPI_Allreduce", "k": 3},
        context=context(retriever=retriever),
    )

    assert result.status == "done"
    payload = json.loads(result.content)
    assert payload["source"] == "course"
    assert payload["chunks"][0]["doc_id"] == "Tutorial_2"
    assert payload["chunks"][0]["page_no"] == 8
    assert payload["chunks"][0]["chunk_id"] == "Tutorial_2:p008:c00"
    assert payload["chunks"][0]["text"].startswith("MPI_Allreduce")
    assert result.output == "1 course chunks"


def test_search_course_reports_an_empty_result_without_failing():
    result = registry().execute(
        "search_course", {"query": "nothing"}, context=context()
    )

    assert result.status == "done"
    assert json.loads(result.content)["chunks"] == []
    assert result.output == "no course chunks"


def test_read_course_page_joins_the_page_chunks():
    store = FakeStore(
        {
            ("Tutorial_2", 8): [
                {"id": "Tutorial_2:p008:c00", "text": "first part"},
                {"id": "Tutorial_2:p008:c01", "text": "second part"},
            ]
        }
    )

    result = registry().execute(
        "read_course_page",
        {"doc_id": "Tutorial_2", "page_no": 8},
        context=context(store=store),
    )

    assert result.status == "done"
    payload = json.loads(result.content)
    assert payload["doc_id"] == "Tutorial_2"
    assert payload["page_no"] == 8
    assert payload["chunk_ids"] == ["Tutorial_2:p008:c00", "Tutorial_2:p008:c01"]
    assert payload["text"] == "first part\n\nsecond part"


def test_read_course_page_reports_a_missing_page():
    result = registry().execute(
        "read_course_page",
        {"doc_id": "missing", "page_no": 1},
        context=context(store=FakeStore()),
    )

    assert result.status == "failed"
    assert "no text" in result.output


def test_verify_span_confirms_a_matching_span():
    store = FakeStore(
        {
            ("Tutorial_2", 8): [
                {"id": "Tutorial_2:p008:c00", "text": "MPI_Allreduce reduces a value across all ranks."},
            ]
        }
    )

    result = registry().execute(
        "verify_span",
        {"doc_id": "Tutorial_2", "page_no": 8, "span": "reduces a value"},
        context=context(store=store),
    )

    assert result.status == "done"
    payload = json.loads(result.content)
    assert payload["verified"] is True
    assert result.output == "span verified"


def test_verify_span_rejects_a_missing_span():
    store = FakeStore(
        {
            ("Tutorial_2", 8): [
                {"id": "Tutorial_2:p008:c00", "text": "MPI_Allreduce reduces a value across all ranks."},
            ]
        }
    )

    result = registry().execute(
        "verify_span",
        {"doc_id": "Tutorial_2", "page_no": 8, "span": "CUDA kernels"},
        context=context(store=store),
    )

    assert result.status == "done"
    assert json.loads(result.content)["verified"] is False
    assert result.output == "span not found on page"


def test_verify_span_normalizes_whitespace_and_case():
    store = FakeStore(
        {
            ("Tutorial_2", 8): [
                {"id": "Tutorial_2:p008:c00", "text": "MPI_Allreduce reduces a value across all ranks."},
            ]
        }
    )

    result = registry().execute(
        "verify_span",
        {"doc_id": "Tutorial_2", "page_no": 8, "span": "  REDUCES   A VALUE  "},
        context=context(store=store),
    )

    assert json.loads(result.content)["verified"] is True


def test_verify_span_reports_a_missing_page():
    result = registry().execute(
        "verify_span",
        {"doc_id": "missing", "page_no": 1, "span": "anything"},
        context=context(store=FakeStore()),
    )

    assert result.status == "failed"
    assert "no text" in result.output


def _search_result():
    return SearchResult(
        title="DeepSeek V4 released",
        url="https://example.com/deepseek",
        snippet="short",
        summary="A long summary about the release.",
        content="",
        site_name="Example",
        date="2026-06-01T00:00:00+00:00",
        rerank_score=2.4,
        authority=3,
    )


def test_web_search_returns_external_results_and_marks_them_untrusted():
    adapter = FakeAdapter(search_results=[_search_result()])

    result = registry().execute(
        "web_search",
        {"query": "DeepSeek V4", "count": 3},
        context=context(adapter=adapter),
    )

    assert result.status == "done"
    payload = json.loads(result.content)
    assert payload["source"] == "web"
    assert payload["untrusted"] is True
    assert payload["results"][0]["url"] == "https://example.com/deepseek"
    assert adapter.search_calls == [
        {"query": "DeepSeek V4", "count": 3, "need_content": False}
    ]


def test_web_search_failure_is_safe_and_does_not_leak_the_key():
    adapter = FakeAdapter(fail_search=True)

    result = registry().execute(
        "web_search", {"query": "anything"}, context=context(adapter=adapter)
    )

    assert result.status == "failed"
    assert result.output == "web search failed"
    assert "sk-test" not in result.content


def test_web_fetch_rejects_local_and_non_http_urls_before_calling_provider():
    adapter = FakeAdapter(page=FetchResult("https://example.com", "T", "body"))

    for url in (
        "http://localhost:8000/api/chat",
        "http://127.0.0.1/",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
        "https://user:pass@example.com/",
    ):
        result = registry().execute(
            "web_fetch", {"url": url}, context=context(adapter=adapter)
        )
        assert result.status == "failed", url

    assert adapter.fetch_calls == []


def test_web_fetch_returns_page_content_and_truncates_it():
    adapter = FakeAdapter(page=FetchResult("https://example.com", "Example", "x" * 7000))

    result = registry().execute(
        "web_fetch", {"url": "https://example.com"}, context=context(adapter=adapter)
    )

    assert result.status == "done"
    payload = json.loads(result.content)
    assert payload["url"] == "https://example.com"
    assert payload["untrusted"] is True
    assert len(payload["content"]) <= 6000
    assert adapter.fetch_calls == ["https://example.com"]


def test_tool_output_respects_the_configured_cap():
    class Small(FakeSettings):
        agent_max_tool_output_chars = 200

    tool_registry = registry(settings=Small())
    result = tool_registry.execute(
        "search_course",
        {"query": "MPI", "k": 10},
        context=context(
            retriever=FakeRetriever([chunk()]), settings=Small()
        ),
    )

    assert result.status == "done"
    assert len(result.content) <= 200
