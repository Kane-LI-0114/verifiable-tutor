"""Unified model adapter over the external OpenAI-compatible providers.

The adapter owns provider selection, request shaping, response normalization,
thinking control, tool-call handling, fallback, streaming normalization, and
the DeepSeek search and fetch APIs. Tests inject an ``httpx`` transport at the
network boundary; the live smoke script uses the real network.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

import httpx
import openai
from openai import OpenAI

from .cache import ResponseCache
from .config import ResolvedModelConfig


class AdapterError(RuntimeError):
    """Base class for adapter errors."""


class ConfigSelectionError(AdapterError):
    """Raised when a provider or model alias cannot be resolved."""


class ModelSelectionError(ConfigSelectionError):
    """Raised when the requested provider or tier does not exist."""


class CapabilityError(AdapterError):
    """Raised when the selected provider cannot handle the input."""


class ProviderAPIError(AdapterError):
    """Raised when a provider returns an error response."""

    def __init__(self, status: int | None, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"provider error status={status}: {message}")

    @property
    def retryable(self) -> bool:
        if self.status is None:
            return True
        return self.status in {408, 409, 429} or self.status >= 500


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ToolCallDelta:
    index: int
    id: str | None
    name: str | None
    arguments_delta: str


@dataclass(frozen=True)
class ChatResult:
    text: str
    reasoning: str | None
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str | None
    usage: Mapping[str, Any]
    provider: str
    model: str


@dataclass(frozen=True)
class StreamEvent:
    kind: str
    text: str | None = None
    tool_call: ToolCallDelta | None = None
    finish_reason: str | None = None
    usage: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    language: str
    seconds: float | None
    model: str


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    summary: str
    content: str
    site_name: str | None
    date: str | None
    rerank_score: float | None
    authority: int | None


@dataclass(frozen=True)
class FetchResult:
    url: str
    title: str
    content: str


@dataclass(frozen=True)
class SpeechResult:
    audio: bytes
    format: str
    voice: str
    model: str


_IMAGE_BLOCK_TYPES = {"image_url", "input_image", "file"}
_AUDIO_BLOCK_TYPES = {"input_audio"}
_ASR_MIMES = {"audio/wav", "audio/mpeg", "audio/mp3"}
_ASR_MAX_BASE64_BYTES = 10 * 1024 * 1024
_RETRYABLE_STATUS = {408, 409, 429}


class ModelAdapter:
    """Provider-neutral chat client with per-provider request adapters."""

    def __init__(
        self,
        resolved: ResolvedModelConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        cache_root: str | Path | None = None,
    ) -> None:
        self._resolved = resolved
        self._config = resolved.config
        self._transport = transport
        self._clients: dict[str, OpenAI] = {}
        root = Path(cache_root) if cache_root is not None else resolved.cache_dir
        self._cache = ResponseCache(root, enabled=self._config.cache.enabled)

    # -- provider plumbing -------------------------------------------------
    def _client(self, provider_name: str) -> OpenAI:
        client = self._clients.get(provider_name)
        if client is not None:
            return client
        provider = self._config.providers[provider_name]
        http_client = (
            httpx.Client(transport=self._transport) if self._transport is not None else None
        )
        client = OpenAI(
            api_key=self._resolved.api_keys[provider_name],
            base_url=provider.base_url,
            timeout=self._config.defaults.timeout_s,
            max_retries=0,
            http_client=http_client,
        )
        self._clients[provider_name] = client
        return client

    def _resolve(self, role: str, provider: str | None, tier: str | None) -> tuple[str, str]:
        role_config = self._config.roles.get(role)
        if role_config is None:
            raise ModelSelectionError(f"unknown role {role!r}")
        if provider is None:
            provider_name = role_config.provider
            alias = tier or role_config.model
        else:
            provider_name = provider
            alias = tier or (role_config.model if provider == role_config.provider else "")
        if provider_name not in self._config.providers:
            raise ModelSelectionError(f"unknown provider {provider_name!r}")
        models = self._config.providers[provider_name].models
        if not alias or alias not in models:
            raise ModelSelectionError(
                f"provider {provider_name!r} has no model alias {alias!r}; "
                f"available: {sorted(models)}"
            )
        return provider_name, models[alias]

    def _effective_thinking(self, role: str, thinking: str | None, tools: Sequence | None) -> str:
        role_config = self._config.roles[role]
        level = thinking or role_config.thinking or self._config.defaults.thinking
        if tools and self._config.thinking.disable_for_tools:
            level = "off"
        return level

    def _has_image_input(self, messages: Sequence[Mapping[str, Any]]) -> bool:
        return self._has_block_type(messages, _IMAGE_BLOCK_TYPES)

    def _has_audio_input(self, messages: Sequence[Mapping[str, Any]]) -> bool:
        return self._has_block_type(messages, _AUDIO_BLOCK_TYPES)

    def _has_block_type(
        self, messages: Sequence[Mapping[str, Any]], block_types: set[str]
    ) -> bool:
        for message in messages:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, Mapping) and part.get("type") in block_types:
                    return True
        return False

    def _prepare_chat(
        self,
        role: str,
        messages: Sequence[Mapping[str, Any]],
        provider: str | None,
        tier: str | None,
        thinking: str | None,
        tools: Sequence[Mapping[str, Any]] | None,
        tool_choice: str,
        response_format: Mapping[str, Any] | None,
        temperature: float | None,
        top_p: float | None,
        max_output_tokens: int | None,
    ) -> tuple[str, str, dict[str, Any]]:
        role_config = self._config.roles.get(role)
        if role_config is None:
            raise ModelSelectionError(f"unknown role {role!r}")
        provider_name, model_id = self._resolve(role, provider, tier)
        provider_config = self._config.providers[provider_name]

        if self._has_image_input(messages) and not provider_config.supports.image:
            raise CapabilityError(f"provider {provider_name!r} does not accept image input")
        if self._has_audio_input(messages) and not provider_config.supports.audio:
            raise CapabilityError(
                f"provider {provider_name!r} does not accept audio input; "
                "select a MiMo model for audio files"
            )

        level = self._effective_thinking(role, thinking, tools)
        mapped = self._config.thinking.mapping.get(provider_name, {}).get(level)
        if mapped is None:
            raise ModelSelectionError(
                f"provider {provider_name!r} has no thinking mapping for level {level!r}"
            )

        output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else role_config.params.max_output_tokens
            or self._config.defaults.max_output_tokens
        )
        request: dict[str, Any] = {
            "model": model_id,
            "messages": list(messages),
            provider_config.max_tokens_field: output_tokens,
        }
        if level == "off":
            request["temperature"] = (
                temperature
                if temperature is not None
                else role_config.params.temperature
                if role_config.params.temperature is not None
                else self._config.defaults.temperature
            )
            request["top_p"] = (
                top_p
                if top_p is not None
                else role_config.params.top_p
                if role_config.params.top_p is not None
                else self._config.defaults.top_p
            )

        if provider_name == "deepseek":
            request["reasoning_effort"] = mapped
        else:
            request.setdefault("extra_body", {})["thinking"] = {"type": mapped}

        if tools:
            request["tools"] = list(tools)
            request["tool_choice"] = "auto" if provider_name == "mimo" else tool_choice
        if response_format is not None:
            request["response_format"] = dict(response_format)
        return provider_name, model_id, request

    # -- public seam -------------------------------------------------------
    def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        role: str = "chat",
        provider: str | None = None,
        tier: str | None = None,
        thinking: str | None = None,
        tools: Sequence[Mapping[str, Any]] | None = None,
        tool_choice: str = "auto",
        response_format: Mapping[str, Any] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
        use_cache: bool = True,
        _allow_fallback: bool = True,
    ) -> ChatResult:
        provider_name, model_id, request = self._prepare_chat(
            role,
            messages,
            provider,
            tier,
            thinking,
            tools,
            tool_choice,
            response_format,
            temperature,
            top_p,
            max_output_tokens,
        )

        cache_key = {"provider": provider_name, "request": request}
        if use_cache:
            cached = self._cache.get("chat", cache_key)
            if cached is not None:
                try:
                    return _chat_result_from_dict(cached)
                except (KeyError, TypeError, ValueError):
                    pass

        try:
            response = self._client(provider_name).chat.completions.create(**request)
        except openai.APIStatusError as exc:
            error = ProviderAPIError(exc.status_code, _error_message(exc))
            return self._maybe_fallback(
                error,
                role,
                messages,
                thinking,
                tools,
                tool_choice,
                response_format,
                temperature,
                top_p,
                max_output_tokens,
                use_cache,
                _allow_fallback,
            )
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            error = ProviderAPIError(None, str(exc))
            return self._maybe_fallback(
                error,
                role,
                messages,
                thinking,
                tools,
                tool_choice,
                response_format,
                temperature,
                top_p,
                max_output_tokens,
                use_cache,
                _allow_fallback,
            )

        choice = response.choices[0]
        message = choice.message
        tool_calls = tuple(
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in message.tool_calls or []
        )
        usage = response.usage.model_dump() if response.usage is not None else {}
        result = ChatResult(
            text=message.content or "",
            reasoning=_extra_field(message, "reasoning_content"),
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=usage,
            provider=provider_name,
            model=model_id,
        )
        if use_cache:
            self._cache.set("chat", cache_key, _chat_result_to_dict(result))
        return result

    def chat_stream(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        role: str = "chat",
        provider: str | None = None,
        tier: str | None = None,
        thinking: str | None = None,
        tools: Sequence[Mapping[str, Any]] | None = None,
        tool_choice: str = "auto",
        response_format: Mapping[str, Any] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
        use_cache: bool = True,
    ) -> Iterator[StreamEvent]:
        provider_name, _model_id, request = self._prepare_chat(
            role,
            messages,
            provider,
            tier,
            thinking,
            tools,
            tool_choice,
            response_format,
            temperature,
            top_p,
            max_output_tokens,
        )
        request["stream"] = True
        if provider_name == "deepseek":
            request["stream_options"] = {"include_usage": True}

        cache_key = {"provider": provider_name, "request": request}
        if use_cache:
            cached = self._cache.get("chat_stream", cache_key)
            if isinstance(cached, list):
                try:
                    replay = [_stream_event_from_dict(item) for item in cached]
                except (KeyError, TypeError, ValueError):
                    replay = None
                if replay is not None:
                    yield from replay
                    return

        try:
            stream = self._client(provider_name).chat.completions.create(**request)
        except openai.APIStatusError as exc:
            raise ProviderAPIError(exc.status_code, _error_message(exc)) from exc
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise ProviderAPIError(None, str(exc)) from exc

        events: list[StreamEvent] = []
        for event in self._events_from_chunks(stream):
            events.append(event)
            yield event
        if use_cache:
            self._cache.set(
                "chat_stream", cache_key, [_stream_event_to_dict(event) for event in events]
            )

    def _events_from_chunks(self, stream: Iterator[Any]) -> Iterator[StreamEvent]:
        for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta
                reasoning = _extra_field(delta, "reasoning_content")
                if reasoning:
                    yield StreamEvent(kind="reasoning", text=reasoning)
                if delta.content:
                    yield StreamEvent(kind="text", text=delta.content)
                for call in delta.tool_calls or []:
                    function = call.function
                    yield StreamEvent(
                        kind="tool_call",
                        tool_call=ToolCallDelta(
                            index=call.index,
                            id=call.id,
                            name=function.name if function is not None else None,
                            arguments_delta=(
                                function.arguments if function is not None and function.arguments else ""
                            ),
                        ),
                    )
                if choice.finish_reason is not None:
                    yield StreamEvent(kind="finish", finish_reason=choice.finish_reason)
            if chunk.usage is not None:
                usage = (
                    chunk.usage.model_dump()
                    if hasattr(chunk.usage, "model_dump")
                    else dict(chunk.usage)
                )
                yield StreamEvent(kind="usage", usage=usage)

    def transcribe(
        self,
        audio: bytes,
        *,
        mime: str = "audio/wav",
        language: str = "auto",
        use_cache: bool = True,
    ) -> TranscriptResult:
        """Transcribe speech with the MiMo ASR model, regardless of the chat provider."""

        if mime not in _ASR_MIMES:
            raise CapabilityError(
                f"unsupported ASR mime {mime!r}; MiMo ASR accepts audio/wav or audio/mpeg"
            )
        encoded = base64.b64encode(audio).decode("ascii")
        if len(encoded) > _ASR_MAX_BASE64_BYTES:
            raise CapabilityError("ASR audio exceeds the 10 MiB base64 limit")

        provider_name = "mimo"
        provider = self._config.providers.get(provider_name)
        if provider is None or not provider.asr_model:
            raise CapabilityError("no MiMo ASR model is configured")
        request: dict[str, Any] = {
            "model": provider.asr_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": f"data:{mime};base64,{encoded}"},
                        }
                    ],
                }
            ],
            "extra_body": {"asr_options": {"language": language}},
        }
        cache_key = {
            "model": provider.asr_model,
            "mime": mime,
            "language": language,
            "audio_sha256": hashlib.sha256(audio).hexdigest(),
        }
        if use_cache:
            cached = self._cache.get("transcribe", cache_key)
            if cached is not None:
                try:
                    return _transcript_from_dict(cached)
                except (KeyError, TypeError, ValueError):
                    pass
        try:
            response = self._client(provider_name).chat.completions.create(**request)
        except openai.APIStatusError as exc:
            raise ProviderAPIError(exc.status_code, _error_message(exc)) from exc
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise ProviderAPIError(None, str(exc)) from exc

        message = response.choices[0].message
        usage = response.usage
        seconds: float | None = None
        if usage is not None:
            raw_seconds = _extra_field(usage, "seconds")
            if raw_seconds is not None:
                seconds = float(raw_seconds)
        result = TranscriptResult(
            text=message.content or "",
            language=language,
            seconds=seconds,
            model=provider.asr_model,
        )
        if use_cache:
            self._cache.set("transcribe", cache_key, _transcript_to_dict(result))
        return result

    # -- MiMo text to speech ----------------------------------------------
    def speak(
        self,
        text: str,
        *,
        voice: str | None = None,
        format: str | None = None,
        instructions: str | None = None,
        model_alias: str = "default",
        use_cache: bool = True,
    ) -> SpeechResult:
        """Synthesize text with the MiMo TTS family."""

        if not text.strip():
            raise CapabilityError("TTS text must not be empty")
        tts = self._config.tts
        provider = self._config.providers.get(tts.provider)
        if provider is None:
            raise CapabilityError(f"tts provider {tts.provider!r} is not configured")
        resolved_format = format or tts.default_format
        if resolved_format not in tts.formats:
            raise CapabilityError(
                f"unsupported TTS format {resolved_format!r}; choose from {tts.formats}"
            )
        resolved_voice = voice or tts.default_voice
        model_id = tts.models.get(model_alias)
        if model_id is None:
            raise ModelSelectionError(f"unknown TTS model alias {model_alias!r}")

        request: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": instructions or tts.default_instructions},
                {"role": "assistant", "content": text},
            ],
            "extra_body": {"audio": {"format": resolved_format, "voice": resolved_voice}},
        }
        cache_key = {
            "model": model_id,
            "messages": request["messages"],
            "audio": {"format": resolved_format, "voice": resolved_voice},
        }
        if use_cache:
            cached = self._cache.get("tts", cache_key)
            if cached is not None:
                try:
                    return _speech_from_dict(cached)
                except (KeyError, TypeError, ValueError):
                    pass
        try:
            response = self._client(tts.provider).chat.completions.create(**request)
        except openai.APIStatusError as exc:
            raise ProviderAPIError(exc.status_code, _error_message(exc)) from exc
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise ProviderAPIError(None, str(exc)) from exc

        message = response.choices[0].message
        audio_payload = _extra_field(message, "audio")
        if isinstance(audio_payload, Mapping):
            audio_data = audio_payload.get("data")
        else:
            audio_data = getattr(audio_payload, "data", None)
        if not isinstance(audio_data, str):
            raise ProviderAPIError(None, "TTS response did not contain audio data")
        try:
            audio = base64.b64decode(audio_data)
        except (ValueError, TypeError) as exc:
            raise ProviderAPIError(None, f"invalid base64 TTS audio: {exc}") from exc
        result = SpeechResult(
            audio=audio,
            format=resolved_format,
            voice=resolved_voice,
            model=model_id,
        )
        if use_cache:
            self._cache.set("tts", cache_key, _speech_to_dict(result))
        return result

    # -- DeepSeek REST search and fetch -----------------------------------
    def _rest_http_client(self) -> httpx.Client:
        client = getattr(self, "_rest_client", None)
        if client is None:
            client = httpx.Client(
                transport=self._transport,
                timeout=self._config.search.timeout_s,
            )
            self._rest_client = client
        return client

    def _post_search_json(self, url: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._resolved.api_keys['search']}",
            "Content-Type": "application/json",
        }
        attempts = self._config.search.max_retries + 1
        last_error: ProviderAPIError | None = None
        for attempt in range(attempts):
            try:
                response = self._rest_http_client().post(url, headers=headers, json=dict(payload))
            except httpx.RequestError as exc:
                last_error = ProviderAPIError(None, str(exc))
                if attempt + 1 < attempts:
                    continue
                raise last_error from exc
            if response.status_code >= 400:
                error = ProviderAPIError(response.status_code, _http_error_message(response))
                if (response.status_code in _RETRYABLE_STATUS or response.status_code >= 500) and (
                    attempt + 1 < attempts
                ):
                    last_error = error
                    continue
                raise error
            try:
                data = response.json()
            except ValueError as exc:
                raise ProviderAPIError(response.status_code, "invalid JSON response") from exc
            if not isinstance(data, Mapping):
                raise ProviderAPIError(response.status_code, "unexpected response body")
            return data
        raise last_error or ProviderAPIError(None, "search request failed")

    def search(
        self,
        query: str,
        *,
        count: int | None = None,
        need_content: bool | None = None,
        ori_question: str | None = None,
        use_cache: bool = True,
    ) -> list[SearchResult]:
        """Search the web with the DeepSeek Search API, independent of the chat model."""

        query = (query or "").strip()
        if not 1 <= len(query) <= 128:
            raise ValueError("query must contain 1 to 128 characters")
        resolved_count = self._config.search.default_count if count is None else count
        if not 1 <= resolved_count <= 50:
            raise ValueError("count must be between 1 and 50")
        resolved_need = self._config.search.need_content if need_content is None else need_content
        payload: dict[str, Any] = {
            "query": query,
            "count": resolved_count,
            "need_content": resolved_need,
        }
        if ori_question is not None:
            payload["ori_question"] = ori_question
        cache_key = {"base_url": self._config.search.base_url, "payload": payload}
        if use_cache:
            cached = self._cache.get("search", cache_key)
            if isinstance(cached, list):
                try:
                    return [_search_result_from_dict(item) for item in cached]
                except (KeyError, TypeError, ValueError):
                    pass
        data = self._post_search_json(
            f"{self._config.search.base_url}{self._config.search.search_path}", payload
        )

        results: list[SearchResult] = []
        for item in data.get("results", []) or []:
            if not isinstance(item, Mapping):
                continue
            results.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    snippet=item.get("snippet") or "",
                    summary=item.get("summary") or "",
                    content=item.get("content") or "",
                    site_name=item.get("site_name"),
                    date=item.get("date"),
                    rerank_score=item.get("rerank_score"),
                    authority=item.get("authority"),
                )
            )
        if use_cache:
            self._cache.set(
                "search", cache_key, [_search_result_to_dict(result) for result in results]
            )
        return results

    def fetch(self, url: str, *, use_cache: bool = True) -> FetchResult:
        """Fetch a page as Markdown with the DeepSeek Fetch API."""

        parts = urlsplit(url or "")
        if (
            parts.scheme not in {"http", "https"}
            or not parts.netloc
            or parts.username is not None
            or parts.password is not None
            or len(url) > 8192
        ):
            raise ValueError("url must be an http or https URL without credentials")
        cache_key = {"base_url": self._config.search.base_url, "url": url}
        if use_cache:
            cached = self._cache.get("fetch", cache_key)
            if isinstance(cached, Mapping):
                try:
                    return FetchResult(
                        url=str(cached["url"]),
                        title=str(cached["title"]),
                        content=str(cached["content"]),
                    )
                except (KeyError, TypeError, ValueError):
                    pass
        data = self._post_search_json(
            f"{self._config.search.base_url}{self._config.search.fetch_path}", {"url": url}
        )
        result = FetchResult(
            url=url,
            title=data.get("title") or "",
            content=data.get("content") or "",
        )
        if use_cache:
            self._cache.set(
                "fetch",
                cache_key,
                {"url": result.url, "title": result.title, "content": result.content},
            )
        return result

    def _maybe_fallback(
        self,
        error: ProviderAPIError,
        role: str,
        messages: Sequence[Mapping[str, Any]],
        thinking: str | None,
        tools: Sequence[Mapping[str, Any]] | None,
        tool_choice: str,
        response_format: Mapping[str, Any] | None,
        temperature: float | None,
        top_p: float | None,
        max_output_tokens: int | None,
        use_cache: bool,
        allow_fallback: bool,
    ) -> ChatResult:
        fallback = self._config.roles[role].fallback
        if allow_fallback and error.retryable and fallback is not None:
            return self.chat(
                messages,
                role=role,
                provider=fallback.provider,
                tier=fallback.model,
                thinking=thinking,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_output_tokens,
                use_cache=use_cache,
                _allow_fallback=False,
            )
        raise error


def _transcript_to_dict(result: TranscriptResult) -> dict[str, Any]:
    return {
        "text": result.text,
        "language": result.language,
        "seconds": result.seconds,
        "model": result.model,
    }


def _transcript_from_dict(payload: Mapping[str, Any]) -> TranscriptResult:
    seconds = payload.get("seconds")
    return TranscriptResult(
        text=str(payload["text"]),
        language=str(payload["language"]),
        seconds=float(seconds) if seconds is not None else None,
        model=str(payload["model"]),
    )


def _speech_to_dict(result: SpeechResult) -> dict[str, Any]:
    return {
        "audio": base64.b64encode(result.audio).decode("ascii"),
        "format": result.format,
        "voice": result.voice,
        "model": result.model,
    }


def _speech_from_dict(payload: Mapping[str, Any]) -> SpeechResult:
    return SpeechResult(
        audio=base64.b64decode(str(payload["audio"])),
        format=str(payload["format"]),
        voice=str(payload["voice"]),
        model=str(payload["model"]),
    )


def _search_result_to_dict(result: SearchResult) -> dict[str, Any]:
    return {
        "title": result.title,
        "url": result.url,
        "snippet": result.snippet,
        "summary": result.summary,
        "content": result.content,
        "site_name": result.site_name,
        "date": result.date,
        "rerank_score": result.rerank_score,
        "authority": result.authority,
    }


def _search_result_from_dict(payload: Mapping[str, Any]) -> SearchResult:
    return SearchResult(
        title=str(payload["title"]),
        url=str(payload["url"]),
        snippet=str(payload["snippet"]),
        summary=str(payload["summary"]),
        content=str(payload["content"]),
        site_name=payload.get("site_name"),
        date=payload.get("date"),
        rerank_score=payload.get("rerank_score"),
        authority=payload.get("authority"),
    )


def _stream_event_to_dict(event: StreamEvent) -> dict[str, Any]:
    tool_call = None
    if event.tool_call is not None:
        tool_call = {
            "index": event.tool_call.index,
            "id": event.tool_call.id,
            "name": event.tool_call.name,
            "arguments_delta": event.tool_call.arguments_delta,
        }
    return {
        "kind": event.kind,
        "text": event.text,
        "tool_call": tool_call,
        "finish_reason": event.finish_reason,
        "usage": dict(event.usage) if event.usage is not None else None,
    }


def _stream_event_from_dict(payload: Mapping[str, Any]) -> StreamEvent:
    tool_data = payload.get("tool_call")
    tool_call = None
    if isinstance(tool_data, Mapping):
        tool_call = ToolCallDelta(
            index=int(tool_data["index"]),
            id=tool_data.get("id"),
            name=tool_data.get("name"),
            arguments_delta=str(tool_data.get("arguments_delta") or ""),
        )
    usage = payload.get("usage")
    return StreamEvent(
        kind=str(payload["kind"]),
        text=payload.get("text"),
        tool_call=tool_call,
        finish_reason=payload.get("finish_reason"),
        usage=dict(usage) if isinstance(usage, Mapping) else None,
    )


def _chat_result_to_dict(result: ChatResult) -> dict[str, Any]:
    return {
        "text": result.text,
        "reasoning": result.reasoning,
        "tool_calls": [
            {"id": call.id, "name": call.name, "arguments": call.arguments}
            for call in result.tool_calls
        ],
        "finish_reason": result.finish_reason,
        "usage": dict(result.usage),
        "provider": result.provider,
        "model": result.model,
    }


def _chat_result_from_dict(payload: Mapping[str, Any]) -> ChatResult:
    tool_calls = tuple(
        ToolCall(id=str(call["id"]), name=str(call["name"]), arguments=str(call["arguments"]))
        for call in payload.get("tool_calls", []) or []
    )
    return ChatResult(
        text=str(payload["text"]),
        reasoning=payload.get("reasoning"),
        tool_calls=tool_calls,
        finish_reason=payload.get("finish_reason"),
        usage=dict(payload.get("usage") or {}),
        provider=str(payload["provider"]),
        model=str(payload["model"]),
    )


def _extra_field(message: Any, name: str) -> str | None:
    value = getattr(message, name, None)
    if value is not None:
        return value
    extra = getattr(message, "model_extra", None) or {}
    return extra.get(name)


def _error_message(exc: openai.APIStatusError) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping) and isinstance(error.get("message"), str):
            return error["message"]
    return str(exc)


def _http_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping) and isinstance(error.get("message"), str):
            return error["message"]
    return response.text or f"HTTP {response.status_code}"
