"""Chat turns: the agent loop, streaming frames, persistence, and trace.

The turn runs through the LangGraph tool loop in ``orchestrator.runner``. This
service keeps the HTTP contract: it owns the conversation, the prompt history,
the AI SDK frame sequence, the persisted turn metadata, and the JSONL trace.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Iterator, Mapping

from ..llm.adapter import (
    AdapterError,
    CapabilityError,
    ConfigSelectionError,
    ModelResponseError,
    ModelSelection,
    ModelSelectionError,
    ProviderAPIError,
    StreamEvent,
)
from ..orchestrator.runner import AgentEvent, AgentRunner
from ..orchestrator.tools import ToolRegistry
from . import streaming
from ..prompts import load_prompt
from ..settings import AppSettings
from ..storage import Storage
from ..trace import SessionTrace

# The chat system prompt lives in src/verifiable_tutor/prompts/chat_system.md;
# edit that file, not this code (see AGENTS.md, prompt texts).
SYSTEM_PROMPT = load_prompt("chat_system")
GENERIC_STREAM_ERROR = "The model failed while answering. Please try again."
GENERIC_UNAVAILABLE = "The model is temporarily unavailable. Please try again."
SAVE_ERROR = "The answer could not be saved. Please try again."
EMPTY_TURN = "The agent produced no answer. Please try again."


class ChatError(Exception):
    """A client-visible chat failure raised before the stream starts.

    ``conversation_id`` is set once the turn has created or resolved its
    conversation, so the HTTP layer can return it and the client can recover
    instead of creating a second conversation when it retries.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        conversation_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.conversation_id = conversation_id
        super().__init__(detail)


@dataclass
class ChatTurn:
    conversation_id: str
    frames: Iterable[dict[str, Any]]


def _prestream_error(exc: Exception, *, conversation_id: str | None) -> ChatError:
    if isinstance(exc, (ModelSelectionError, ConfigSelectionError, CapabilityError)):
        status, detail = 400, str(exc)
    elif isinstance(exc, ModelResponseError):
        status, detail = 503, exc.user_message
    elif isinstance(exc, AdapterError):
        status, detail = 503, GENERIC_UNAVAILABLE
    else:
        status, detail = 503, "The model layer is not available."
    return ChatError(status, detail, conversation_id=conversation_id)


def _stream_error_text(exc: Exception) -> str:
    if isinstance(exc, ModelResponseError):
        return exc.user_message
    if isinstance(exc, ProviderAPIError):
        return GENERIC_UNAVAILABLE
    return GENERIC_STREAM_ERROR


class ChatService:
    """One chat turn: resolve the conversation, run the agent, stream, persist."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        storage: Storage,
        trace: SessionTrace,
        clock: Callable[[], datetime],
        tool_registry: ToolRegistry,
        retriever: Any,
        knowledge_store: Any,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._trace = trace
        self._clock = clock
        self._runner = AgentRunner(
            settings=settings,
            registry=tool_registry,
            retriever=retriever,
            store=knowledge_store,
        )

    # -- conversation helpers ---------------------------------------------
    def _conversation(
        self, user: dict[str, Any], session_id: str | None, message: str
    ) -> dict[str, Any]:
        if session_id:
            conversation = self._storage.find_conversation(session_id)
            if conversation is None or conversation["user_id"] != user["id"]:
                raise ChatError(404, "conversation not found")
            return conversation
        title = message.strip()[:60] or None
        return self._storage.create_conversation(
            conversation_id=uuid.uuid4().hex,
            user_id=user["id"],
            title=title,
            created_at=self._clock(),
        )

    def _history(self, conversation_id: str) -> list[dict[str, str]]:
        stored = self._storage.list_messages(conversation_id)
        limit = self._settings.chat_history_messages
        selected = stored[-limit:] if limit > 0 else stored
        history: list[dict[str, str]] = []
        for message in selected:
            if message["role"] not in {"user", "assistant"}:
                continue
            item = {"role": message["role"], "content": message["content"]}
            if message["role"] == "assistant" and message.get("reasoning"):
                # DeepSeek and MiMo require previous reasoning_content when a
                # request carries tools, including turns that made no tool call.
                item["reasoning_content"] = message["reasoning"]
            history.append(item)
        return history

    # -- public entry point ------------------------------------------------
    def begin_turn(
        self,
        user: dict[str, Any],
        *,
        session_id: str | None,
        message: str,
        provider: str | None,
        tier: str | None,
        thinking: str | None,
        adapter: Any,
        document_context: Mapping[str, Any] | None = None,
    ) -> ChatTurn:
        message = message.strip()
        if not message:
            raise ChatError(400, "message must not be empty")
        conversation = self._conversation(user, session_id, message)
        now = self._clock()
        self._storage.add_message(
            message_id=uuid.uuid4().hex,
            conversation_id=conversation["id"],
            sequence=self._storage.next_message_sequence(conversation["id"]),
            role="user",
            content=message,
            created_at=now,
        )
        self._storage.touch_conversation(conversation["id"], updated_at=now)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self._history(conversation["id"]),
        ]
        if document_context:
            note = load_prompt("chat_document_context")
            note = note.replace(
                "%%DOC_ID%%", str(document_context.get("doc_id") or "")
            ).replace(
                "%%PAGE%%", str(document_context.get("page_no") or 1)
            )
            messages.insert(1, {"role": "system", "content": note})

        try:
            selection = adapter.resolve_selection(
                role="chat",
                provider=provider,
                tier=tier,
                thinking=thinking,
            )
            events = self._runner.run(
                messages,
                adapter=adapter,
                provider=selection.provider,
                tier=tier,
                thinking=thinking,
            )
            first_event = next(events)
        except StopIteration:
            events = iter(())
            first_event = None
        except Exception as exc:  # model boundary failures become HTTP errors
            raise _prestream_error(
                exc, conversation_id=conversation["id"]
            ) from exc

        message_id = uuid.uuid4().hex
        frames = self._frame_stream(
            user=user,
            conversation=conversation,
            message_id=message_id,
            provider=provider,
            tier=tier,
            selection=selection,
            first_event=first_event,
            events=events,
        )
        return ChatTurn(conversation_id=conversation["id"], frames=frames)

    # -- frame generator ---------------------------------------------------
    def _frame_stream(
        self,
        *,
        user: dict[str, Any],
        conversation: dict[str, Any],
        message_id: str,
        provider: str | None,
        tier: str | None,
        selection: ModelSelection,
        first_event: AgentEvent | None,
        events: Iterator[AgentEvent],
    ) -> Iterator[dict[str, Any]]:
        session_id = conversation["id"]
        text_part: str | None = None
        reasoning_part: str | None = None
        text_started = False
        steps: list[dict[str, Any]] = []
        active_step_positions: dict[str, int] = {}
        active_step_ids: dict[str, str] = {}
        chain_events: list[dict[str, Any]] = []
        tool_positions = 0
        turn_result: dict[str, Any] | None = None
        model_started = False
        collected: list[str] = []

        self._trace.append_meta(
            user["id"],
            session_id,
            {
                "conversation_id": session_id,
                "message_id": message_id,
                "provider": selection.provider,
                "model": selection.model,
                "tier": selection.tier,
                "thinking": selection.thinking,
                "started_at": self._clock().isoformat(),
            },
            now=self._clock(),
        )

        def record_step(frame: dict[str, Any]) -> None:
            """Merge a data-step frame into the ordered work-chain steps."""

            data = frame["data"]
            name = data["step"]
            position = active_step_positions.get(name)
            if position is None:
                step_id = uuid.uuid4().hex
                position = len(steps)
                steps.append({})
                active_step_positions[name] = position
            else:
                step_id = steps[position]["id"]
            data["id"] = step_id
            active_step_ids[name] = step_id
            steps[position] = {
                "id": step_id,
                "step": name,
                "status": data["status"],
                "detail": data.get("detail"),
                "duration_ms": data.get("duration_ms"),
                "policy": data.get("policy"),
                "rule_id": data.get("rule_id"),
            }
            if data["status"] in {"done", "failed"}:
                active_step_positions.pop(name, None)

        def emit(frame: dict[str, Any]) -> dict[str, Any]:
            if frame["type"] == "data-step":
                record_step(frame)
            self._trace.append_frame(
                user["id"], session_id, frame, now=self._clock()
            )
            return frame

        def close_reasoning() -> Iterator[dict[str, Any]]:
            nonlocal reasoning_part
            if reasoning_part is not None:
                part = reasoning_part
                reasoning_part = None
                yield emit(streaming.reasoning_end(part))

        def close_text() -> Iterator[dict[str, Any]]:
            nonlocal text_part
            if text_part is not None:
                part = text_part
                text_part = None
                yield emit(streaming.text_end(part))

        def open_text() -> Iterator[dict[str, Any]]:
            nonlocal text_part, text_started
            if text_part is None:
                text_part = uuid.uuid4().hex
                text_started = True
                yield emit(streaming.text_start(text_part))

        yield emit(streaming.start(message_id))
        try:
            stream = itertools.chain(
                [first_event] if first_event is not None else [], events
            )
            for event in stream:
                if event.kind == "model_start":
                    if not model_started:
                        model_started = True
                        yield emit(streaming.data_step("generate", "started"))
                    yield emit(streaming.start_step())
                elif event.kind == "reasoning_delta":
                    if text_part is not None:
                        yield from close_text()
                    if reasoning_part is None:
                        reasoning_part = uuid.uuid4().hex
                        yield emit(streaming.reasoning_start(reasoning_part))
                    yield emit(
                        streaming.reasoning_delta(
                            reasoning_part, str(event.data.get("text") or "")
                        )
                    )
                elif event.kind == "text_delta":
                    if reasoning_part is not None:
                        yield from close_reasoning()
                    if text_part is None:
                        yield from open_text()
                    delta = str(event.data.get("text") or "")
                    collected.append(delta)
                    yield emit(streaming.text_delta(text_part, delta))
                elif event.kind == "model_end":
                    yield from close_reasoning()
                    yield from close_text()
                    yield emit(streaming.finish_step())
                    reasoning = str(event.data.get("reasoning") or "").strip()
                    if reasoning:
                        chain_events.append(
                            {
                                "kind": "reasoning",
                                "reasoning": reasoning,
                                "step_id": active_step_ids.get("generate"),
                            }
                        )
                elif event.kind == "tool_start":
                    yield from close_reasoning()
                    yield from close_text()
                    data = event.data
                    step_name = data.get("step")
                    if step_name == "retrieve":
                        yield emit(streaming.data_step("retrieve", "started"))
                    yield emit(
                        streaming.data_tool(
                            {
                                "tool_call_id": data.get("tool_call_id"),
                                "name": data.get("name"),
                                "status": "running",
                                "arguments": data.get("arguments") or {},
                                "output": None,
                                "result": None,
                                "duration_ms": None,
                                "step_id": active_step_ids.get(step_name),
                            }
                        )
                    )
                elif event.kind == "tool_end":
                    data = event.data
                    step_id = active_step_ids.get(data.get("step"))
                    yield emit(
                        streaming.data_tool(
                            {
                                "tool_call_id": data.get("tool_call_id"),
                                "name": data.get("name"),
                                "status": data.get("status"),
                                "arguments": data.get("arguments") or {},
                                "output": data.get("output"),
                                "result": data.get("result"),
                                "duration_ms": data.get("duration_ms"),
                                "step_id": step_id,
                            }
                        )
                    )
                    if data.get("step") == "retrieve":
                        yield emit(
                            streaming.data_step(
                                "retrieve",
                                "done",
                                duration_ms=data.get("duration_ms"),
                            )
                        )
                    chain_events.append(
                        {
                            "kind": "tool_call",
                            "tool_call_position": tool_positions,
                            "step_id": step_id,
                        }
                    )
                    tool_positions += 1
                elif event.kind == "turn_end":
                    turn_result = dict(event.data)
                    break
        except Exception as exc:  # the stream already started: report in band
            text = _stream_error_text(exc)
            self._trace.append_event(
                user["id"], session_id, "error", {"message": text}, now=self._clock()
            )
            yield emit(streaming.error(text))
            return

        if turn_result is None:
            turn_result = {"text": EMPTY_TURN, "reasoning": "", "tool_calls": []}

        yield from close_reasoning()
        yield from close_text()
        if turn_result.get("text") and not collected:
            text_part = uuid.uuid4().hex
            yield emit(streaming.text_start(text_part))
            collected.append(str(turn_result["text"]))
            yield emit(streaming.text_delta(text_part, str(turn_result["text"])))
            yield emit(streaming.text_end(text_part))
            text_part = None
        yield emit(streaming.data_step("generate", "done"))

        # Persist the whole turn before the finish frame: a client that sees the
        # answer complete must be able to read it back from the history.
        now = self._clock()
        try:
            self._storage.add_assistant_turn(
                message_id=message_id,
                conversation_id=session_id,
                sequence=self._storage.next_message_sequence(session_id),
                content=str(turn_result.get("text") or ""),
                created_at=now,
                provider=provider,
                tier=tier,
                model=selection.model,
                thinking=selection.thinking,
                reasoning=str(turn_result.get("reasoning") or "") or None,
                steps=steps,
                tool_calls=turn_result.get("tool_calls") or (),
                events=chain_events,
            )
        except Exception:  # a storage failure must not claim a finished turn
            self._trace.append_event(
                user["id"], session_id, "error", {"message": SAVE_ERROR}, now=now
            )
            yield emit(streaming.error(SAVE_ERROR))
            return

        if turn_result.get("usage"):
            self._trace.append_event(
                user["id"], session_id, "usage", dict(turn_result["usage"]), now=now
            )
        self._trace.append_event(
            user["id"],
            session_id,
            "agent",
            {
                "model_calls": turn_result.get("model_calls"),
                "tool_calls": len(turn_result.get("tool_calls") or ()),
            },
            now=now,
        )
        self._storage.touch_conversation(session_id, updated_at=now)
        self._trace.append_event(
            user["id"], session_id, "finish", {"message_id": message_id}, now=self._clock()
        )
        yield emit(streaming.finish())
