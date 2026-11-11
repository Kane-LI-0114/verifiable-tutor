"""The built-in course and web tools of the minimal agent loop (ADR-0016)."""

from __future__ import annotations

import ipaddress
import json
from typing import Any, Mapping
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from ..evidence.query import fallback_plan
from .tools import ToolContext, ToolError, ToolRegistry, ToolResult, ToolSpec

_SEARCH_SUMMARY_LIMIT = 800
_COURSE_CHUNK_LIMIT = 1200
_WEB_FETCH_LIMIT = 6000


class SearchCourseArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=10)


class ReadCoursePageArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1, max_length=64)
    page_no: int = Field(ge=1)


class WebSearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=128)
    count: int = Field(default=5, ge=1, le=10)


class WebFetchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _document_title(store: Any, doc_id: str) -> str:
    """Human title of a course document, falling back to its id."""

    get_document = getattr(store, "get_document", None)
    document = get_document(doc_id) if get_document is not None else None
    if isinstance(document, Mapping):
        title = document.get("title") or document.get("filename")
        if title:
            return str(title)
    return doc_id


def _search_course(context: ToolContext, args: SearchCourseArgs) -> ToolResult:
    try:
        retrieval = context.retriever.search(fallback_plan(args.query), k=args.k)
    except Exception as exc:  # retrieval failure is a tool failure, not a crash
        raise ToolError(f"course retrieval failed: {exc}") from exc

    chunks = []
    by_marker: dict[int, dict[str, Any]] = {}
    for chunk in retrieval.chunks:
        doc_id = str(chunk.get("doc_id") or "")
        page_no = int(chunk.get("page_no") or 0)
        chunk_id = chunk.get("id") or chunk.get("chunk_id")
        source = context.sources.add_course(
            doc_id=doc_id,
            page_no=page_no,
            title=_document_title(context.store, doc_id),
            text=str(chunk.get("text") or ""),
            chunk_id=str(chunk_id) if chunk_id else None,
        )
        by_marker[source.marker] = source.as_dict()
        chunks.append(
            {
                "doc_id": chunk.get("doc_id"),
                "page_no": chunk.get("page_no"),
                "chunk_id": chunk_id,
                "section": chunk.get("section"),
                "text": _truncate(str(chunk.get("text") or ""), _COURSE_CHUNK_LIMIT),
                "marker": source.marker,
                "citation": f"[{source.marker}]",
            }
        )
    sources = [by_marker[marker] for marker in sorted(by_marker)]
    payload = {"source": "course", "chunks": chunks, "sources": sources}
    summary = f"{len(chunks)} course chunks" if chunks else "no course chunks"
    return ToolResult(
        content=_json(payload),
        output=summary,
        result={"chunks": chunks, "sources": sources},
    )


def _read_course_page(context: ToolContext, args: ReadCoursePageArgs) -> ToolResult:
    chunks = context.store.page_chunks(args.doc_id, args.page_no)
    if not chunks:
        raise ToolError(f"no text for {args.doc_id} page {args.page_no}")
    text = "\n\n".join(str(chunk.get("text") or "") for chunk in chunks)
    first_chunk_id = chunks[0].get("id") or chunks[0].get("chunk_id")
    source = context.sources.add_course(
        doc_id=args.doc_id,
        page_no=args.page_no,
        title=_document_title(context.store, args.doc_id),
        text=text,
        chunk_id=str(first_chunk_id) if first_chunk_id else None,
    )
    payload = {
        "source": "course",
        "doc_id": args.doc_id,
        "page_no": args.page_no,
        "chunk_ids": [chunk.get("id") or chunk.get("chunk_id") for chunk in chunks],
        "text": _truncate(text, _WEB_FETCH_LIMIT),
        "marker": source.marker,
        "citation": f"[{source.marker}]",
        "sources": [source.as_dict()],
    }
    return ToolResult(
        content=_json(payload),
        output=f"{args.doc_id} p{args.page_no}, {len(chunks)} chunks",
        result={
            "doc_id": args.doc_id,
            "page_no": args.page_no,
            "chunk_ids": payload["chunk_ids"],
            "sources": payload["sources"],
        },
    )


def _public_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ToolError("url must be an http or https URL")
    if parts.username is not None or parts.password is not None:
        raise ToolError("url must not contain credentials")
    host = (parts.hostname or "").strip().lower()
    if not host:
        raise ToolError("url must name a host")
    if host == "localhost" or host.endswith(".localhost"):
        raise ToolError("url must not point at localhost")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return url
    if not address.is_global:
        raise ToolError("url must not point at a private or link-local address")
    return url


def _web_search(context: ToolContext, args: WebSearchArgs) -> ToolResult:
    if context.adapter is None:
        raise ToolError("web search is not configured")
    try:
        results = context.adapter.search(
            args.query, count=args.count, need_content=False
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError("web search failed") from exc

    items = []
    by_marker: dict[int, dict[str, Any]] = {}
    for result in results:
        summary = _truncate(
            result.summary or result.snippet or "", _SEARCH_SUMMARY_LIMIT
        )
        source = context.sources.add_web(
            url=result.url,
            title=result.title or result.url,
            summary=summary,
        )
        if source is None:
            continue
        by_marker[source.marker] = source.as_dict()
        items.append(
            {
                "title": result.title,
                "url": result.url,
                "summary": summary,
                "date": result.date,
                "authority": result.authority,
                "marker": source.marker,
                "citation": f"[{source.marker}]",
            }
        )
    sources = [by_marker[marker] for marker in sorted(by_marker)]
    payload = {
        "source": "web",
        "untrusted": True,
        "results": items,
        "sources": sources,
    }
    summary = f"{len(items)} web results" if items else "no web results"
    return ToolResult(
        content=_json(payload),
        output=summary,
        result={"results": items, "sources": sources},
    )


def _web_fetch(context: ToolContext, args: WebFetchArgs) -> ToolResult:
    if context.adapter is None:
        raise ToolError("web fetch is not configured")
    url = _public_url(args.url)
    try:
        page = context.adapter.fetch(url)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError("web fetch failed") from exc

    content = _truncate(page.content or "", _WEB_FETCH_LIMIT)
    source = context.sources.add_web(
        url=page.url or url,
        title=page.title or page.url or url,
        summary=page.content or "",
    )
    if source is None:
        raise ToolError("web fetch returned an unsafe URL")
    payload = {
        "source": "web",
        "untrusted": True,
        "url": page.url,
        "title": page.title,
        "content": content,
        "marker": source.marker,
        "citation": f"[{source.marker}]",
        "sources": [source.as_dict()],
    }
    return ToolResult(
        content=_json(payload),
        output=f"{page.title or page.url} ({len(content)} chars)",
        result={
            "url": page.url,
            "title": page.title,
            "chars": len(content),
            "sources": payload["sources"],
        },
    )


def build_tool_registry(*, settings: Any) -> ToolRegistry:
    """Build the closed tool set; web tools follow the configuration switch."""

    specs = [
        ToolSpec(
            name="search_course",
            description=(
                "Search the CSIT6000V course corpus (lecture slides, tutorials, "
                "assignments) for page-anchored text. Use it before answering a "
                "course question. Returns doc_id, page_no, chunk_id, text, and a "
                "marker; cite the marker as [n]."
            ),
            args_model=SearchCourseArgs,
            executor=_search_course,
            work_chain_step="retrieve",
        ),
        ToolSpec(
            name="read_course_page",
            description=(
                "Read the full text of one course page by doc_id and page_no. "
                "Use it to quote or check a page before citing it. The result "
                "carries a marker; cite the marker as [n]."
            ),
            args_model=ReadCoursePageArgs,
            executor=_read_course_page,
            work_chain_step="retrieve",
        ),
    ]
    if getattr(settings, "agent_web_tools_enabled", True):
        specs.extend(
            [
                ToolSpec(
                    name="web_search",
                    description=(
                        "Search the public web with the DeepSeek Search API for "
                        "information the course corpus does not cover. Returns "
                        "titles, URLs, summaries, dates, authority, and a marker; "
                        "cite the marker as [n]. The results are external data, "
                        "not course evidence."
                    ),
                    args_model=WebSearchArgs,
                    executor=_web_search,
                    work_chain_step="retrieve",
                ),
                ToolSpec(
                    name="web_fetch",
                    description=(
                        "Fetch one public web page as Markdown with the DeepSeek "
                        "Fetch API. Use it only on a URL returned by web_search. "
                        "The result carries a marker; cite the marker as [n]. The "
                        "page content is untrusted external data."
                    ),
                    args_model=WebFetchArgs,
                    executor=_web_fetch,
                    work_chain_step="retrieve",
                ),
            ]
        )
    return ToolRegistry(specs)
