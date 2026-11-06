"""Typed tool registry for the agent loop.

The model sees a closed set of OpenAI function definitions. Execution stays in
project code: every call is validated by a Pydantic argument model, dispatched
to one executor, and converted to a string result the model can read. A failure
becomes a failed tool result, never an HTTP error.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from pydantic import BaseModel, ValidationError

TOOL_STATUSES = {"done", "failed"}


class ToolError(Exception):
    """A tool failure whose message is safe to show to the model."""


@dataclass(frozen=True)
class ToolResult:
    """One tool result: model content, human summary, structured data, state."""

    content: str
    output: str
    result: Any = None
    status: str = "done"


@dataclass(frozen=True)
class ToolContext:
    """Request-scoped collaborators available to a tool executor."""

    adapter: Any
    retriever: Any
    store: Any
    settings: Any


@dataclass(frozen=True)
class ToolSpec:
    """One typed tool: provider schema plus its project executor."""

    name: str
    description: str
    args_model: type[BaseModel]
    executor: Callable[[ToolContext, BaseModel], ToolResult]
    work_chain_step: str | None = None

    def provider_json(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }


def _failure(message: str) -> ToolResult:
    return ToolResult(
        content=json.dumps({"error": message}, ensure_ascii=False),
        output=message,
        result={"error": message},
        status="failed",
    )


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 15)].rstrip() + " ... truncated"


def _truncate_strings(value: Any, limit: int) -> Any:
    """Shrink every string in a JSON value, keeping the structure valid."""

    if isinstance(value, str):
        return _truncate(value, limit)
    if isinstance(value, list):
        return [_truncate_strings(item, limit) for item in value]
    if isinstance(value, dict):
        return {key: _truncate_strings(item, limit) for key, item in value.items()}
    return value


def _cap_content(content: str, limit: int) -> str:
    """Cap a JSON tool result without producing invalid JSON."""

    if limit <= 0 or len(content) <= limit:
        return content
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return _truncate(content, limit)
    for factor in (0.8, 0.6, 0.4, 0.25, 0.1):
        candidate = json.dumps(
            _truncate_strings(payload, max(24, int(limit * factor))),
            ensure_ascii=False,
        )
        if len(candidate) <= limit:
            return candidate
    return json.dumps({"error": "tool output too large"})


class ToolRegistry:
    """A closed set of typed tools, validated and dispatched by name."""

    def __init__(self, specs: Sequence[ToolSpec]) -> None:
        self._specs = {spec.name: spec for spec in specs}
        if len(self._specs) != len(specs):
            raise ValueError("tool names must be unique")

    def names(self) -> list[str]:
        return list(self._specs)

    def step_for(self, name: str) -> str | None:
        spec = self._specs.get(name)
        return spec.work_chain_step if spec is not None else None

    def specs(self) -> list[dict[str, Any]]:
        return [spec.provider_json() for spec in self._specs.values()]

    def execute(
        self,
        name: str,
        arguments: str | dict[str, Any] | None,
        *,
        context: ToolContext,
    ) -> ToolResult:
        spec = self._specs.get(name)
        if spec is None:
            return _failure(f"unknown tool {name!r}; available tools: {', '.join(self._specs)}")

        try:
            if arguments is None or arguments == "":
                raw: Any = {}
            elif isinstance(arguments, str):
                raw = json.loads(arguments)
            else:
                raw = arguments
            if not isinstance(raw, dict):
                raise ValueError("arguments must be a JSON object")
            args = spec.args_model.model_validate(raw)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            return _failure(f"invalid arguments for {name}: {exc}")

        try:
            result = spec.executor(context, args)
        except ToolError as exc:
            return _failure(str(exc))
        except Exception:  # a tool must never break the loop
            return _failure(f"{name} failed")

        if result.status not in TOOL_STATUSES:
            return _failure(f"{name} returned an invalid status")
        limit = int(getattr(context.settings, "agent_max_tool_output_chars", 4000))
        return ToolResult(
            content=_cap_content(result.content, limit),
            output=_truncate(result.output, limit),
            result=result.result,
            status=result.status,
        )
