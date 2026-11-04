"""Chat turns: model streaming with persistence and the JSONL session trace.

The evidence layer, disclosure gate, and LangGraph runtime are not implemented
yet. This service therefore streams ungrounded model text through the
production HTTP and trace path; the wiring points for retrieval and policy
arrive with those packages without changing this HTTP contract.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Iterator

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
    """One chat turn: resolve the conversation, stream, persist, and trace."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        storage: Storage,
        trace: SessionTrace,
        clock: Callable[[], datetime],
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._trace = trace
        self._clock = clock

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
        return [
            {"role": message["role"], "content": message["content"]}
            for message in selected
            if message["role"] in {"user", "assistant"}
        ]

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

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self._history(conversation["id"]),
        ]
        kwargs: dict[str, str] = {}
        if provider is not None:
            kwargs["provider"] = provider
        if tier is not None:
            kwargs["tier"] = tier
        if thinking is not None:
            kwargs["thinking"] = thinking
        try:
            selection = adapter.resolve_selection(
                role="chat",
                provider=provider,
                tier=tier,
                thinking=thinking,
            )
            stream = adapter.chat_stream(messages, **kwargs)
            first_event = next(stream)
        except StopIteration:
            stream = iter(())
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
            stream=stream,
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
        first_event: StreamEvent | None,
        stream: Iterator[StreamEvent],
    ) -> Iterator[dict[str, Any]]:
        session_id = conversation["id"]
        text_part = uuid.uuid4().hex
        reasoning_part = uuid.uuid4().hex
        text_open = False
        reasoning_open = False
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

        def emit(frame: dict[str, Any]) -> dict[str, Any]:
            self._trace.append_frame(
                user["id"], session_id, frame, now=self._clock()
            )
            return frame

        yield emit(streaming.start(message_id))
        yield emit(streaming.data_step("generate", "started"))
        events = itertools.chain(
            [first_event] if first_event is not None else [], stream
        )
        try:
            for event in events:
                if event.kind == "reasoning":
                    if not reasoning_open:
                        reasoning_open = True
                        yield emit(streaming.reasoning_start(reasoning_part))
                    yield emit(
                        streaming.reasoning_delta(reasoning_part, event.text or "")
                    )
                elif event.kind == "text":
                    if reasoning_open:
                        reasoning_open = False
                        yield emit(streaming.reasoning_end(reasoning_part))
                    if not text_open:
                        text_open = True
                        yield emit(streaming.text_start(text_part))
                    collected.append(event.text or "")
                    yield emit(streaming.text_delta(text_part, event.text or ""))
                elif event.kind == "finish":
                    break
        except Exception as exc:  # the stream already started: report in band
            text = _stream_error_text(exc)
            self._trace.append_event(
                user["id"], session_id, "error", {"message": text}, now=self._clock()
            )
            yield emit(streaming.error(text))
            return

        if reasoning_open:
            yield emit(streaming.reasoning_end(reasoning_part))
        if text_open:
            yield emit(streaming.text_end(text_part))
        yield emit(streaming.data_step("generate", "done"))
        yield emit(streaming.finish())

        now = self._clock()
        self._storage.add_message(
            message_id=uuid.uuid4().hex,
            conversation_id=session_id,
            sequence=self._storage.next_message_sequence(session_id),
            role="assistant",
            content="".join(collected),
            provider=provider,
            tier=tier,
            created_at=now,
        )
        self._storage.touch_conversation(session_id, updated_at=now)
        self._trace.append_event(
            user["id"], session_id, "finish", {"message_id": message_id}, now=now
        )
