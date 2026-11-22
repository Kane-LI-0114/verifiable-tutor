"""The minimal LangGraph tool loop (ADR-0016).

The graph has an agent node and a tools node. The agent node calls the project's
model adapter and streams deltas through LangGraph's custom writer; the tools
node validates and executes the requested calls and appends the results to the
message list. The last allowed model call runs without tools so the turn always
ends with an answer or an abstention.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Sequence, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from ..evidence.sources import SourceRegistry
from ..llm.adapter import StreamEvent
from .tools import ToolContext, ToolRegistry

FALLBACK_TEXT = (
    "I could not produce a grounded answer within the tool budget. "
    "Please narrow the question or try again."
)
BUDGET_NOTE = (
    "The tool budget is exhausted. Answer from the evidence already in the "
    "conversation, or state clearly what is missing. Do not request tools."
)


@dataclass
class AgentEvent:
    """One event the graph emits for the chat service to translate."""

    kind: str
    data: dict[str, Any] = field(default_factory=dict)


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    model_calls: int
    tool_call_count: int
    pending_tool_calls: list[dict[str, Any]]
    final_text: str


@dataclass
class _Accumulator:
    text: str = ""
    reasoning: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    model_calls: int = 0


def _merge_usage(total: dict[str, Any], usage: Mapping[str, Any] | None) -> None:
    if not usage:
        return
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            total[key] = int(total.get(key, 0)) + value


def _tool_arguments(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


class AgentRunner:
    """Run one agent turn: model calls, tool dispatch, and streamed events."""

    def __init__(
        self,
        *,
        settings: Any,
        registry: ToolRegistry,
        retriever: Any,
        store: Any,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._retriever = retriever
        self._store = store

    # -- public seam -------------------------------------------------------
    def run(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        adapter: Any,
        provider: str | None = None,
        tier: str | None = None,
        thinking: str | None = None,
    ) -> Iterator[AgentEvent]:
        """Yield turn events; the final event is ``turn_end``."""

        accumulator = _Accumulator()
        sources = SourceRegistry()
        graph = self._compile(
            adapter=adapter,
            provider=provider,
            tier=tier,
            thinking=thinking,
            accumulator=accumulator,
            sources=sources,
        )
        state: AgentState = {
            "messages": [dict(message) for message in messages],
            "model_calls": 0,
            "tool_call_count": 0,
            "pending_tool_calls": [],
        }
        for payload in graph.stream(
            state,
            stream_mode="custom",
            config={"recursion_limit": int(self._settings.agent_recursion_limit)},
        ):
            kind = payload.get("kind") if isinstance(payload, dict) else None
            data = payload.get("data") if isinstance(payload, dict) else None
            if isinstance(kind, str) and isinstance(data, dict):
                yield AgentEvent(kind=kind, data=data)
        yield AgentEvent(
            kind="turn_end",
            data={
                "text": accumulator.text,
                "reasoning": accumulator.reasoning,
                "tool_calls": accumulator.tool_calls,
                "usage": accumulator.usage,
                "model_calls": accumulator.model_calls,
                "sources": sources.snapshot(),
            },
        )

    # -- graph -------------------------------------------------------------
    def _compile(
        self,
        *,
        adapter: Any,
        provider: str | None,
        tier: str | None,
        thinking: str | None,
        accumulator: _Accumulator,
        sources: SourceRegistry,
    ):
        def agent_node(state: AgentState) -> dict[str, Any]:
            return self._agent(
                state,
                adapter=adapter,
                provider=provider,
                tier=tier,
                thinking=thinking,
                accumulator=accumulator,
            )

        def tools_node(state: AgentState) -> dict[str, Any]:
            return self._tools(
                state,
                adapter=adapter,
                accumulator=accumulator,
                sources=sources,
            )

        def route(state: AgentState) -> str:
            if state.get("pending_tool_calls"):
                return "tools"
            return END

        graph = StateGraph(AgentState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
        return graph.compile()

    # -- nodes -------------------------------------------------------------
    def _agent(
        self,
        state: AgentState,
        *,
        adapter: Any,
        provider: str | None,
        tier: str | None,
        thinking: str | None,
        accumulator: _Accumulator,
    ) -> dict[str, Any]:
        writer = get_stream_writer()
        messages = list(state.get("messages") or [])
        model_calls = int(state.get("model_calls") or 0)
        tool_count = int(state.get("tool_call_count") or 0)
        allow_tools = (
            model_calls < int(self._settings.agent_max_model_calls) - 1
            and tool_count < int(self._settings.agent_max_tool_calls)
        )
        request_messages = list(messages)
        if not allow_tools:
            request_messages = [*request_messages, {"role": "system", "content": BUDGET_NOTE}]

        stream = adapter.chat_stream(
            request_messages,
            role="chat",
            provider=provider,
            tier=tier,
            thinking=thinking,
            tools=self._registry.specs() if allow_tools else None,
            tool_choice="auto",
        )
        first = next(stream, None)
        writer({"kind": "model_start", "data": {"call": model_calls + 1}})

        text_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_deltas: dict[int, dict[str, str]] = {}
        finish_reason: str | None = None
        usage: dict[str, Any] | None = None

        def consume(event: StreamEvent | None) -> None:
            nonlocal finish_reason, usage
            if event is None:
                return
            if event.kind == "text" and event.text:
                text_parts.append(event.text)
                accumulator.text += event.text
                writer({"kind": "text_delta", "data": {"text": event.text}})
            elif event.kind == "reasoning" and event.text:
                reasoning_parts.append(event.text)
                accumulator.reasoning += event.text
                writer({"kind": "reasoning_delta", "data": {"text": event.text}})
            elif event.kind == "tool_call" and event.tool_call is not None:
                delta = event.tool_call
                slot = tool_deltas.setdefault(
                    delta.index, {"id": "", "name": "", "arguments": ""}
                )
                if delta.id:
                    slot["id"] = delta.id
                if delta.name:
                    slot["name"] = delta.name
                if delta.arguments_delta:
                    slot["arguments"] += delta.arguments_delta
            elif event.kind == "finish":
                finish_reason = event.finish_reason
            elif event.kind == "usage" and event.usage:
                usage = dict(event.usage)
                _merge_usage(accumulator.usage, event.usage)

        consume(first)
        for event in stream:
            consume(event)

        accumulator.model_calls += 1
        writer(
            {
                "kind": "model_end",
                "data": {
                    "call": model_calls + 1,
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "reasoning": "".join(reasoning_parts),
                },
            }
        )

        next_calls = model_calls + 1
        if allow_tools and tool_deltas:
            calls = []
            for index in sorted(tool_deltas):
                slot = tool_deltas[index]
                raw = slot["arguments"] or "{}"
                calls.append(
                    {
                        "id": slot["id"] or f"call_{index}",
                        "name": slot["name"],
                        "arguments": raw,
                        "index": index,
                    }
                )
            assistant = {
                "role": "assistant",
                "content": "".join(text_parts) or None,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": call["arguments"],
                        },
                    }
                    for call in calls
                ],
            }
            if reasoning_parts:
                # Both providers require the previous reasoning_content when a
                # tool result continues a thinking-mode turn.
                assistant["reasoning_content"] = "".join(reasoning_parts)
            return {
                "messages": [*messages, assistant],
                "model_calls": next_calls,
                "pending_tool_calls": calls,
                "final_text": "",
            }

        final_text = "".join(text_parts) or (accumulator.text or FALLBACK_TEXT)
        if not accumulator.text:
            accumulator.text = final_text
        assistant = {"role": "assistant", "content": final_text}
        return {
            "messages": [*messages, assistant],
            "model_calls": next_calls,
            "pending_tool_calls": [],
            "final_text": final_text,
        }

    def _tools(
        self,
        state: AgentState,
        *,
        adapter: Any,
        accumulator: _Accumulator,
        sources: SourceRegistry,
    ) -> dict[str, Any]:
        writer = get_stream_writer()
        messages = list(state.get("messages") or [])
        pending = list(state.get("pending_tool_calls") or [])
        tool_count = int(state.get("tool_call_count") or 0)
        max_tools = int(self._settings.agent_max_tool_calls)
        context = ToolContext(
            adapter=adapter,
            retriever=self._retriever,
            store=self._store,
            settings=self._settings,
            sources=sources,
        )

        appended: list[dict[str, Any]] = []
        for position, call in enumerate(pending):
            name = str(call.get("name") or "")
            raw_arguments = str(call.get("arguments") or "{}")
            writer(
                {
                    "kind": "tool_start",
                    "data": {
                        "tool_call_id": call.get("id"),
                        "name": name,
                        "arguments": _tool_arguments(raw_arguments),
                        "position": position,
                        "step": self._registry.step_for(name),
                    },
                }
            )
            started = time.perf_counter()
            before_sources = sources.snapshot()
            if tool_count >= max_tools:
                from .tools import ToolResult

                result = ToolResult(
                    content=json.dumps({"error": "tool budget exhausted"}),
                    output="tool budget exhausted",
                    result={"error": "tool budget exhausted"},
                    status="failed",
                )
            else:
                result = self._registry.execute(
                    name, raw_arguments, context=context
                )
            duration_ms = int((time.perf_counter() - started) * 1000)
            tool_count += 1
            record = {
                "tool_call_id": call.get("id"),
                "name": name,
                "arguments": _tool_arguments(raw_arguments),
                "result": result.result,
                "output": result.output,
                "command": [],
                "exit_code": None,
                "status": result.status,
                "duration_ms": duration_ms,
                "step": self._registry.step_for(name),
            }
            accumulator.tool_calls.append(record)
            writer({"kind": "tool_end", "data": dict(record)})
            after_sources = sources.snapshot()
            if after_sources != before_sources:
                writer({"kind": "sources", "data": {"sources": after_sources}})
            appended.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": result.content,
                }
            )

        return {
            "messages": [*messages, *appended],
            "pending_tool_calls": [],
            "tool_call_count": tool_count,
        }
