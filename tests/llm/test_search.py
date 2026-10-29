import json
from pathlib import Path

import httpx
import pytest

from verifiable_tutor.llm.adapter import (
    FetchResult,
    ModelAdapter,
    ProviderAPIError,
    SearchResult,
)
from verifiable_tutor.llm.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config" / "models.yaml"
ENV = {"DEEPSEEK_API_KEY": "sk-deepseek-test", "MIMO_API_KEY": "sk-mimo-test"}


def make_adapter(handler) -> ModelAdapter:
    resolved = load_model_config(REAL_CONFIG, env=ENV)
    resolved.config.cache.enabled = False
    return ModelAdapter(resolved, transport=httpx.MockTransport(handler))


def search_response() -> dict:
    return {
        "results": [
            {
                "rerank_score": 2.4,
                "title": "DeepSeek V4 模型发布",
                "url": "https://example.com/deepseek-v4",
                "snippet": "DeepSeek V4 已上线，支持工具调用与长上下文。",
                "summary": "DeepSeek 发布了 V4 模型。此次发布改进了工具调用与长上下文能力。",
                "content": "DeepSeek V4 现已正式上线。",
                "site_name": "Example News",
                "site_icon": "https://example.com/favicon.ico",
                "date": "2026-06-01T00:00:00+00:00",
                "authority": 3,
            }
        ]
    }


def test_search_uses_deepseek_endpoint_and_normalizes_results() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=search_response())

    results = make_adapter(handler).search("DeepSeek V4 发布", count=5)

    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "DeepSeek V4 模型发布"
    assert results[0].url == "https://example.com/deepseek-v4"
    assert results[0].summary.startswith("DeepSeek 发布了 V4")
    assert results[0].site_name == "Example News"
    assert results[0].rerank_score == 2.4
    assert results[0].authority == 3

    request = captured[0]
    assert request.url.host == "api.deepseek.com"
    assert request.url.path == "/v1/tools/search"
    assert request.headers["authorization"] == "Bearer sk-deepseek-test"
    body = json.loads(request.content)
    assert body == {"query": "DeepSeek V4 发布", "count": 5, "need_content": True}


def test_search_uses_config_defaults() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"results": []})

    results = make_adapter(handler).search("roofline model")

    assert results == []
    body = json.loads(captured[0].content)
    assert body["count"] == 10
    assert body["need_content"] is True


def test_search_validates_query_and_count() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected")

    adapter = make_adapter(handler)
    with pytest.raises(ValueError, match="query"):
        adapter.search("   ")
    with pytest.raises(ValueError, match="count"):
        adapter.search("roofline", count=51)


def test_search_retries_retryable_status() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if len(seen) == 1:
            return httpx.Response(503, json={"error": {"message": "busy"}})
        return httpx.Response(200, json=search_response())

    results = make_adapter(handler).search("roofline")

    assert len(results) == 1
    assert seen == ["/v1/tools/search", "/v1/tools/search"]


def test_search_wraps_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    with pytest.raises(ProviderAPIError) as excinfo:
        make_adapter(handler).search("roofline")

    assert excinfo.value.status == 401


def test_fetch_returns_markdown_content() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"title": "Example article", "content": "# Example\n\nBody."}
        )

    result = make_adapter(handler).fetch("https://example.com/article")

    assert isinstance(result, FetchResult)
    assert result.url == "https://example.com/article"
    assert result.title == "Example article"
    assert result.content == "# Example\n\nBody."
    request = captured[0]
    assert request.url.path == "/v1/tools/fetch"
    assert json.loads(request.content) == {"url": "https://example.com/article"}


def test_fetch_rejects_url_with_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected")

    with pytest.raises(ValueError, match="url"):
        make_adapter(handler).fetch("https://user:pass@example.com/article")
