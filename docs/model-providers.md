# Model provider API notes

Agent-facing reference for the two external model providers used by this project, DeepSeek and Xiaomi MiMo. Sources were read from the official documentation on 2026-10-29 with a headless browser; model ids and limits change often, so the configuration, not the code, must stay the source of truth. This document describes the APIs and the routing rules the agent layer must implement. It does not describe implemented code.

Scope and non-goals:

- In scope: model switching between providers and tiers, image input, audio input, thinking control, web search through DeepSeek only, JSON output, tool calling, streaming, errors, and configuration mapping.
- Out of scope: prompts, retrieval design, UI, and any deployment decision. Those live in [tech-selection.md](tech-selection.md).
- No code was changed when this document was written; the configuration gaps are listed in the last sections as follow-up work.

## 1. Provider matrix

| Capability | DeepSeek | Xiaomi MiMo |
|---|---|---|
| Chat base URL | `https://api.deepseek.com` | `https://api.xiaomimimo.com/v1` |
| Auth | `Authorization: Bearer` | `Authorization: Bearer` or `api-key` |
| Text models used here | `deepseek-flash` only | `mimo-v2.6-flash`, `mimo-v2.6-pro` |
| Context / max output | 1M / 384K tokens | 1M / 128K tokens |
| Image input | Yes, `deepseek-flash` only | Yes, both v2.6 tiers |
| Audio file input | No, not supported anywhere | Yes: omni chat on both v2.6 tiers |
| Speech to text | No | Yes: `mimo-v2.5-asr`, transcript output |
| Text to speech | No | Yes: `mimo-v2.5-tts` family, base64 audio output |
| Video input | No | Yes, both v2.6 tiers |
| Thinking control | `thinking.type` plus `reasoning_effort` levels `none, low, high, max` | `thinking.type` only, `enabled` or `disabled`; the composer exposes Off and On, and `low` or `max` normalize to the enabled value |
| JSON output | `response_format: json_object` only | `response_format: json_object` only |
| Tool calling | OpenAI function tools; in thinking mode `tool_choice` must be `auto` or `none`, and `required` or a named function returns 400 | OpenAI function tools; `tool_choice` must be `auto` |
| Web search | Standalone Search and Fetch REST APIs | Own `web_search` tool exists; not used by this project |
| Native files upload | Files API for images | None; URL or base64 only |

Routing rules the agent layer must enforce:

1. Model selection: the user or the config selects provider and tier. DeepSeek exposes only the `flash` tier by project decision. MiMo exposes `flash` and `pro`. All model ids live in `config/models.yaml`, never in code.
2. Image input: route to the selected chat provider. DeepSeek accepts images only on `deepseek-flash`. MiMo accepts images on both v2.6 tiers.
3. Audio file input: supported only when the selected model is a MiMo 2.6 tier. If the selected model is `mimo-v2.6-flash`, flash handles the audio; if it is `mimo-v2.6-pro`, pro handles it. If the selected provider is DeepSeek, the adapter rejects the attachment with a capability error instead of rerouting it silently.
4. Voice-to-text: the microphone in the composer uses MiMo `mimo-v2.5-asr`. The transcript is inserted into the text box, and the normal chat path then runs with the selected text provider. This is a transcription call, not a chat call.
5. Text to speech: assistant output can be synthesized by the MiMo TTS family on demand. This path also serves as the candidate for teaching-video voiceover. It is a separate call and does not change the chat provider.
6. Thinking: expose one control; DeepSeek offers `off`, `low`, `high`, and `max`, while MiMo offers only Off and On, and `low` or `max` normalize to the enabled value. Tool-calling turns follow the per-provider `thinking.disable_for_tools` policy: DeepSeek keeps thinking with `tool_choice: auto` and requires previous `reasoning_content` to be replayed; MiMo disables thinking by default because tool calls with thinking are unstable unless `reasoning_content` is echoed. Force `off` for deterministic evaluation runs, because temperature is ignored while thinking is on.
7. Web search: always call the DeepSeek Search and Fetch REST APIs, even when the chat model is MiMo. These APIs are provider independent and authenticated with the DeepSeek key.
8. JSON output: no provider offers `json_schema`. Put the schema in the prompt, set `json_object`, validate with pydantic, and retry a bounded number of times.
9. Tool calls: apply the per-provider thinking policy, echo the full assistant message (including `reasoning_content`) on every later turn when thinking is active, validate the tool arguments in code, and never rely on `tool_choice` other than `auto`.
10. Failure handling: retry the selected model on transient errors (timeouts, connection errors, 408, 409, 429, 5xx) up to `defaults.max_retries`. Never fall back to a different model or provider. After the last attempt raise `ModelResponseError` with `reason` (`timeout` or `unavailable`) and a `user_message`; the service shows that copy and the user decides when to retry. Non-retryable errors keep the `ProviderAPIError` status.

Adapter surface, current and pending:

| Method | Status | Purpose |
|---|---|---|
| `chat(messages, ...)` | implemented | text, image, and MiMo audio-file chat; DeepSeek audio input raises a capability error |
| `chat_stream(messages, ...)` | implemented | normalized streaming events |
| `transcribe(audio, mime, language)` | implemented | ASR for the composer microphone |
| `search(query, ...)`, `fetch(url)` | implemented | DeepSeek REST search and fetch |
| `speak(text, voice, format)` | implemented | MiMo TTS for playback and teaching-video voiceover |

## 2. Shared client contract

Both providers are OpenAI Chat Completions compatible, but not identically so. The model client must normalize these differences.

| Concern | DeepSeek | Xiaomi MiMo |
|---|---|---|
| OpenAI SDK base URL | `https://api.deepseek.com` (do not append `/v1`) | `https://api.xiaomimimo.com/v1` |
| Output budget field | `max_tokens`, range 1 to 393216; default 8K non-thinking and 64K thinking, 128K at max effort | `max_completion_tokens`, default and max 131072 |
| Default thinking state | Enabled, effort `high` | Enabled |
| Thinking switch location with the OpenAI SDK | `extra_body={"thinking": {...}}` | `extra_body={"thinking": {...}}` |
| Non-standard request fields | `thinking`, `user_id`, `prefix`, `reasoning_effort` is standard | `thinking`, `asr_options` |
| Streaming terminator | `data: [DONE]` | `data: [DONE]` |
| Usage in streaming | Rides on the last content chunk, which still has one `choices` entry | A final chunk with `choices: []` carries usage |
| Keep-alive | Blank lines when non-streaming, `: keep-alive` comments when streaming, closed after 10 minutes if generation has not started | Not documented |
| Error envelope | OpenAI compatible | OpenAI compatible |
| Temperature when thinking | Ignored | Ignored and forced to 1.0, top_p forced to 0.95 |

Streaming parser rules that satisfy both providers:

- Iterate chunks, skip any chunk whose `choices` array is empty, and read `usage` from whichever chunk carries it.
- Accumulate `delta.content` and `delta.reasoning_content` separately.
- Accumulate tool calls by `delta.tool_calls[].index`, concatenating `function.arguments` fragments.
- Treat `finish_reason` values `length`, `tool_calls`, `content_filter`, `insufficient_system_resource`, `aborted`, and `repetition_truncation` explicitly. The last two are provider specific.
- Do not assume `stream_options.include_usage` exists. DeepSeek accepts it with its own semantics; MiMo does not document it.

## 3. DeepSeek

### 3.1 Endpoints and models

- Chat: `POST https://api.deepseek.com/chat/completions`
- Files: `POST https://api.deepseek.com/files`
- Search: `POST https://api.deepseek.com/v1/tools/search`
- Fetch: `POST https://api.deepseek.com/v1/tools/fetch`
- Beta surface: base URL `https://api.deepseek.com/beta` for strict tools, prefix completion, and FIM
- Responses API: `POST https://api.deepseek.com/responses` (not used by this project)
- Anthropic surface: base URL `https://api.deepseek.com/anthropic` (not used)

| Model id | Version | Context / max output | Image input | Notes |
|---|---|---|---|---|
| `deepseek-flash` | DeepSeek-V4.1-Flash-1017 | 1M / 384K | Yes | The only DeepSeek model this project uses |
| `deepseek-v4-pro` | DeepSeek-V4-Pro-0813 | 1M / 384K | No | Not used, because the project fixes DeepSeek to flash |

Retired names must not appear in config: `deepseek-chat` and `deepseek-reasoner` were retired on 2026-07-24. `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are legacy aliases that still resolve to V4.1-Flash but are documented as offline aliases. There is no `deepseek-pro`.

Minimal call:

```python
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[{"role": "user", "content": "hello"}],
    reasoning_effort="none",
    max_tokens=4096,
)
```

### 3.2 Image input

Supported on `deepseek-flash` only. `content` must be a block array. Images are allowed only in `user` messages; images in `system` or `assistant` messages return 400.

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "describe this slide"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<BASE64>"}}
  ]
}
```

Three input modes:

1. Inline data URL with base64.
2. Public `http` or `https` URL; the model downloads it.
3. Files API `file_id` using a `file` block, not `image_url`:

```json
{"type": "file", "file_id": "file-api-xxxxxxxx"}
```

Limits:

- Formats: JPEG, PNG, GIF, WebP; the format is detected from content, not from the filename.
- Request body 48 MiB; single image 32 MiB inline or by URL, 64 MiB through the Files API.
- Up to 600 images per request; total image bytes up to 64 MiB without `file_id`, 200 MiB with `file_id` images.
- Longest side 8192 px, dropping to 4096 px when a request has 15 or more images.
- Images are rescaled before inference, so each image costs at most 1024 tokens.
- Optional `detail` values: `low`, `high`, `original`, `auto`. `low` downscales to 512 by 512.

Unverified: the docs do not state whether images can be combined with thinking or with tools. Test before relying on the combination.

### 3.3 Audio input

Not supported. There is no audio content block, no transcription endpoint, and no mention of audio in the chat reference. Any voice input must go through MiMo.

### 3.4 Thinking and effort

Controls:

- `thinking`: `{"type": "enabled" | "disabled"}`. Not an OpenAI SDK field, so pass it through `extra_body`.
- `reasoning_effort`: `none`, `low`, `high`, `max`. Default is `high`. `none` turns thinking off. Aliases map as follows: `minimal` to `low`, `medium` and `xhigh` to `high`, `ultra` to `max`.

Behaviour:

- Thinking is on by default. A plain call silently runs in thinking mode and silently ignores `temperature`, `presence_penalty`, and `frequency_penalty`.
- With thinking on, `max_tokens` defaults to 64K, or 128K at `max` effort. Set it explicitly.
- Reasoning text arrives in `message.reasoning_content` or `delta.reasoning_content`. Token count is in `usage.completion_tokens_details.reasoning_tokens`.
- With tools present, every later request must echo the earlier assistant `reasoning_content`, or the API returns 400. Without tools, it is ignored.
- `tool_choice` equal to `required` or a named function returns 400 in thinking mode. Disable thinking first.
- `top_p` is effective only in thinking mode on flash, with a floor of 0.95. In non-thinking mode it is fixed at 1.0.

Unified control mapping is in section 7.

### 3.5 Web search and fetch

Both are standalone REST APIs, not chat tools. They are authenticated with the DeepSeek key and can be called while the chat model is MiMo.

Search request:

```json
{
  "query": "TACC Slurm job time limit",
  "count": 10,
  "need_content": true,
  "ori_question": "What is the TACC job time limit?"
}
```

Fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | 1 to 128 characters; supports search operators |
| `count` | integer | no | 1 to 50, default 10 |
| `need_content` | boolean | no | default false; when false `content` is empty |
| `ori_question` | string | no | the original full question, 1 to 128 characters |
| `localization` | string | no | an IP address used to prefer localized results |

Search response items contain `rerank_score`, `title`, `url`, `snippet`, `summary`, `content`, `site_name`, `site_icon`, `date`, and `authority`. `rerank_score` is at most 3, and 1.5 or higher means a good result. `authority` is 0 to 4, with 3 or higher meaning highly authoritative and -1 meaning unknown. `summary` is the long field intended for feeding a model; `snippet` is for UI. There is no citation id field, so citations must be built from `url`, `title`, and `site_name`.

Supported operators: `site:`, `-site:`, `-keyword`, `-"phrase"`, `"exact phrase"`, `lang:zh,en`, `after:2025`, `after:2025-01-01`, `before:2026-06-01`, combinable.

Fetch request:

```json
{"url": "https://example.com/article"}
```

`url` must be http or https, at most 8192 characters, no credentials. Response is `{"title": "...", "content": "<markdown>"}`.

Pricing and limits:

- Search and Fetch are billed per successful request, 5 CNY per 1000 successful requests each. Failures, timeouts, and empty search results are free.
- QPS limits are per account and independent: Search 100 QPS, Fetch 25 QPS, plus per-domain limits on Fetch.
- No pagination is documented; only `count`.

The Chat Completions API has no `web_search` tool type; `tools` accepts only functions. The Responses API has a `web_search` tool, but it is supported only on `deepseek-v4-pro` and ignored on `deepseek-flash`, so the standalone REST APIs are the only route that works with flash and with MiMo.

Error handling: retry on 408, 429, and 5xx; do not retry other 4xx; 402 means insufficient balance; 403 on Fetch means a safety block; 404 on Fetch means no extractable content.

### 3.6 JSON output

- `response_format` accepts `{"type": "text"}` and `{"type": "json_object"}` only. There is no `json_schema` mode in Chat Completions.
- The prompt must contain the word `json` and should include a sample of the desired object.
- The API can return empty `content` in JSON mode. Validate and retry.
- Check `finish_reason == "length"` before parsing, because truncated JSON is common when `max_tokens` is small.
- `json_object` guarantees syntax, not schema conformance.

### 3.7 Tool calling

- Standard OpenAI function tools: `{"type": "function", "function": {"name": ..., "description": ..., "parameters": <JSON Schema>}}`.
- `tool_choice`: `none`, `auto`, `required`, or a named function. Default is `none` without tools and `auto` with tools. In thinking mode only `auto` and `none` work; `required` and named choices return 400.
- The model may produce invalid JSON in `arguments` or invent parameters; validate before dispatch.
- Up to 128 characters in a tool name; characters are letters, digits, underscore, and hyphen.

### 3.8 Streaming quirks

- SSE with `data: {...}` and a final `data: [DONE]`.
- `stream_options.include_usage` adds `usage` to every chunk, null except on the last one. There is no separate usage-only chunk with an empty `choices` array. The last content chunk carries the full usage.
- SSE comments `: keep-alive` and blank lines can appear while the request is queued.

### 3.9 Errors and limits

| Status | Meaning |
|---|---|
| 400 | malformed body, including images in system or assistant messages, and `tool_choice` in thinking mode |
| 401 | bad API key |
| 402 | insufficient balance |
| 422 | invalid parameter |
| 429 | rate or concurrency limit |
| 500 | server error, retry |
| 503 | server busy, retry |

Per-account concurrency: `deepseek-flash` 2500, `deepseek-v4-pro` 500, counted from send to completion. The non-standard `user_id` field goes through `extra_body` and enables isolation and cache separation.

## 4. Xiaomi MiMo

### 4.1 Endpoints and models

- Chat: `POST https://api.xiaomimimo.com/v1/chat/completions`
- Models: `GET https://api.xiaomimimo.com/v1/models`
- Base URL for the OpenAI SDK: `https://api.xiaomimimo.com/v1`
- Batch base URL: `https://batch-api-cn.xiaomimimo.com/v1`
- Anthropic base URL: `https://api.xiaomimimo.com/anthropic`
- Auth headers: `api-key: <key>` or `Authorization: Bearer <key>`; the OpenAI SDK's Bearer header works.
- Key formats: `sk-...` for pay as you go, `tp-...` or `ttp-...` for Token Plan. Do not mix plans and base URLs.

| Model id | Tier | Context / max output | Input modalities | Notes |
|---|---|---|---|---|
| `mimo-v2.6-flash` | flash | 1M / 128K | text, image, audio, video | Cheaper and faster default |
| `mimo-v2.6-pro` | pro | 1M / 128K | text, image, audio, video | Stronger for complex tasks |
| `mimo-v2.6-pro-ultraspeed` | pro, faster decoding | 1M / 128K | text, image, audio, video | Quota by contract; not used |
| `mimo-v2.5-asr` | ASR | 8K / 2K | audio only | Voice input model, still current |
| `mimo-v2.5-tts`, `-voiceclone`, `-voicedesign` | TTS | 8K / 8K | text or audio sample | Not used in the first version |

Retired names must not appear in config: `mimo-v2.5-pro` and `mimo-v2.5` were retired on 2026-10-21, replaced by `mimo-v2.6-pro` and `mimo-v2.6-flash`. The old flash tier was called `mimo-v2.5`; `mimo-v2.5-flash` never existed. ASR and TTS keep the v2.5 names.

Chat defaults and limits:

- `max_completion_tokens`: default 131072, maximum 131072.
- `temperature`: default 1.0, range 0 to 1.5.
- `top_p`: default 0.95, range 0.01 to 1.0.
- `stop`: at most 4 sequences.
- Rate limits for both v2.6 text models: 100 requests per minute and 10M tokens per minute per account and model.

### 4.2 Image input

Both v2.6 tiers accept images. Use `content` as a block array with `image_url`. The URL can be a public URL or a full data URL.

```json
{
  "role": "user",
  "content": [
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,<BASE64>"}},
    {"type": "text", "text": "describe this slide"}
  ]
}
```

Limits: JPEG, PNG, GIF, WebP, BMP; public URL at most 50 MB, base64 string at most 50 MB; no local file upload. Images are tokenized by a patch grid and reported in `usage.prompt_tokens_details.image_tokens`; a typical image costs 1024 image tokens.

### 4.3 Audio input

There are two different features.

Chat audio understanding, for questions about an audio clip. Use `input_audio` with `data` set to a public URL or a full data URL:

```json
{"type": "input_audio", "input_audio": {"data": "data:audio/wav;base64,<BASE64>"}}
```

Formats: MP3, WAV, FLAC, M4A, OGG; URL at most 100 MB, base64 string at most 50 MB. Roughly 6.25 tokens per second of audio. This is descriptive or question answering, not a clean transcript.

ASR for voice input, model `mimo-v2.5-asr`, on the same chat endpoint. There is no multipart transcription endpoint.

```json
{
  "model": "mimo-v2.5-asr",
  "messages": [
    {"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": "data:audio/wav;base64,<BASE64>"}}]}
  ],
  "asr_options": {"language": "auto"}
}
```

ASR constraints:

- `input_audio.data` must be a data URL with base64. Public URLs are not accepted for ASR.
- Formats: mp3 and wav only. Supported MIME types are `audio/wav`, `audio/mpeg`, and `audio/mp3`.
- The base64 string must be at most 10 MB, and only one audio input per request.
- `asr_options.language` is `auto`, `zh`, or `en`; with the OpenAI SDK it must go through `extra_body`.
- The transcript is `choices[0].message.content`. `usage.seconds` reports the audio duration, and `usage.prompt_tokens_details.audio_tokens` reports audio tokens.
- `mimo-v2.5-asr` is billed per audio hour, 0.5 CNY per hour.

Implementation consequence for the browser: MediaRecorder usually produces WebM or Opus, which ASR rejects. The client must record PCM WAV with the Web Audio API or transcode to wav or mp3 before upload. Do not plan on ffmpeg being present in the cluster environment.

Routing in this project:

- An audio file attached to a message is sent to the selected MiMo 2.6 tier through `input_audio`; `flash` handles it when flash is selected, and `pro` handles it when pro is selected. Selecting DeepSeek with an audio attachment raises a capability error rather than rerouting. The model answers or analyzes the audio; it is not a clean transcript path.
- The composer microphone calls the ASR model and inserts the transcript into the text box; the following chat turn uses the selected text provider.
- TTS is a separate output call described in section 4.9. It never changes the chat provider.

### 4.4 Thinking

- Control: `thinking` with `{"type": "enabled" | "disabled"}` only. There is no effort or intensity level. It must go through `extra_body` with the OpenAI SDK.
- Default: enabled for all v2.6 text models.
- Output: `message.reasoning_content` or `delta.reasoning_content`; token count in `usage.completion_tokens_details.reasoning_tokens`.
- While thinking is on, `temperature` and `top_p` are ignored and forced to 1.0 and 0.95. Disable thinking to control sampling.
- With tools, the docs say the combination is unstable: tool calls can leak into `reasoning_content`. The project keeps thinking off for MiMo tool turns by default (`thinking.disable_for_tools.mimo: true`).
- If an assistant turn contains tool calls, its `reasoning_content` must be echoed back on the next request or the API returns 400. The runner adds it when MiMo thinking is enabled.

### 4.5 JSON output

- `response_format` supports `{"type": "json_object"}` only.
- No `json_schema` and no strict structured output. The docs recommend defining the full schema in the prompt, validating with `jsonschema`, and retrying or degrading on failure.
- The prompt must ask for JSON only, with the complete structure, types, enums, numeric ranges, and null policy.
- A small `max_completion_tokens` can truncate the JSON mid-object.

### 4.6 Tool calling

- OpenAI-shaped function tools with `type: function`, `name`, `description`, and `parameters`. Tool names are at most 64 characters.
- `strict` is supported per function, default false.
- `tool_choice` must be `auto`. Any other value is silently stripped and behaves as `auto`, so a forced tool call is impossible. Design prompts so the model wants to call the tool.
- Parallel tool calls are supported; the maximum count is undocumented.
- Tool results use `{"role": "tool", "tool_call_id": ..., "content": ...}`. `finish_reason` is `tool_calls` and `content` is empty on those turns.
- Arguments may be invalid JSON or invent parameters; validate before dispatch.
- Streaming tool deltas use `choices[0].delta.tool_calls[]` with `index`, `id`, `function.name`, and fragmented `function.arguments`.

### 4.7 Streaming

- SSE with `data: {...}` and a final `data: [DONE]`.
- Chunks are `chat.completion.chunk`. The last chunk has `choices: []` and carries the usage totals. Guard against an empty `choices` array.
- Reasoning deltas arrive in `delta.reasoning_content` before content deltas.
- `finish_reason` values include `stop`, `length`, `tool_calls`, `content_filter`, and the MiMo-specific `repetition_truncation`.

### 4.8 MiMo own web search, documented but not used

MiMo has a `tools: [{"type": "web_search", ...}]` capability with console plugin activation, separate per-call billing, and annotations in `message.annotations`. The project does not use it for four reasons: separate paid plugin, per-account console activation, non-standard tool type that breaks the two-provider symmetry, and server-side annotations instead of tool results the orchestrator controls.

### 4.9 Text to speech

The TTS path turns assistant text into audio. It also serves as the candidate for teaching-video voiceover.

- Endpoint: `POST https://api.xiaomimimo.com/v1/chat/completions`, same base URL as chat.
- Models: `mimo-v2.5-tts` for preset voices, `mimo-v2.5-tts-voiceclone` for a cloned voice, and `mimo-v2.5-tts-voicedesign` for a voice described in text.
- Limits: 8K context and 8K output; 100 requests per minute and 10M tokens per minute per model.

Request shape: the `user` message carries style instructions, and the `assistant` message carries the exact text to speak.

```json
{
  "model": "mimo-v2.5-tts",
  "messages": [
    {"role": "user", "content": "Warm, clear, steady teaching pace."},
    {"role": "assistant", "content": "Today we look at the roofline model."}
  ],
  "audio": {"format": "wav", "voice": "mimo_default"}
}
```

- `audio.format`: `wav` by default, or `mp3`, `pcm`, `pcm16`. With `stream: true` the default becomes `pcm`; use `pcm16` when concatenating chunks. The project's streaming route requests `pcm16` through `tts.stream_format` in `config/models.yaml`.
- `audio.voice` preset ids: `mimo_default`, `冰糖`, `茉莉`, `苏打`, `白桦`, `Mia`, `Chloe`, `Milo`, `Dean`.
- `mimo-v2.5-tts-voiceclone` requires `audio.voice` to be a base64 audio sample in mp3 or wav.
- `mimo-v2.5-tts-voicedesign` omits `audio.voice` and takes the voice description in the user message; `audio.optimize_text_preview` may preview an optimized script.
- Singing mode prefixes the assistant text with `(唱歌)`, `(sing)`, or `(singing)`; style tags such as `(怅然)` are allowed.

Response: `choices[0].message.audio.data` is base64 audio, `content` is empty, and `audio.transcript` and `audio.expires_at` are null. Streaming returns audio chunks in `choices[0].delta.audio.data`, one base64 PCM16 payload per `chat.completion.chunk`, with `finish_reason: stop` before the `data: [DONE]` marker. The frontend route republishes those chunks as SSE JSON frames with an `audio` field instead of forwarding the provider shape.

Cost and constraints:

- The pricing page lists TTS as free for a limited period; re-check before relying on that.
- Content moderation can block a request with 421.
- No timestamps and no SSML are documented. The caller must split narration into segments deliberately and align captions itself.
- The text to speak arrives in the assistant message, which is unusual for a chat API; do not reuse a normal chat message list.

Teaching-video voiceover candidate:

- Generate one audio segment per narration unit, using one consistent preset voice or a cloned teacher voice with consent.
- Cache audio by text hash, voice, and format so a video rebuild does not pay again.
- Because the API returns no timestamps, segment boundaries define caption timing; keep each segment short and review pacing on a sample before making the voiceover a deliverable.
- Record the model, voice, and format with every generated clip.

### 4.10 Errors and limits

| Status | Meaning |
|---|---|
| 400 | malformed body, unsupported multimodal format, missing `reasoning_content` in a tool round |
| 401 | bad key, wrong header, or a Token Plan key against a pay-as-you-go base URL |
| 402 | insufficient balance |
| 403 | region unsupported or key risk controlled |
| 404 | endpoint or model does not support the requested modality |
| 421 | content moderation block |
| 429 | rate limit or quota exhausted |
| 500 | internal error, retry |
| 503 | overload, retry |

## 5. DeepSeek Search and Fetch as the project search layer

The project uses the DeepSeek REST APIs for search regardless of the chat provider. The orchestrator flow is:

1. Build a query from the user question. Use `ori_question` for the full question and `query` for the search keywords.
2. Call `POST https://api.deepseek.com/v1/tools/search` with the DeepSeek key.
3. Keep results with `rerank_score` at or above 1.5, or the top `k` results. Feed `summary`, `content`, `title`, and `url` into the prompt as evidence blocks.
4. Optionally call `POST https://api.deepseek.com/v1/tools/fetch` on selected URLs for full Markdown content.
5. Build citations from `url`, `title`, and `site_name`. The API returns no citation id.
6. Cache results by normalized query and `count`; the course does not reimburse external calls and evaluation must run from cache.

Constraints to encode in the client:

- Search `count` is 1 to 50; `need_content` must be true when page bodies are needed.
- Search QPS is 100 and Fetch QPS is 25 per account; Fetch also has per-domain limits.
- Retry on 408, 429, and 5xx only.
- Do not use the Chat Completions `tools` field for search. It only accepts function tools.
- Do not use the Responses API `web_search` tool. It is ignored on `deepseek-flash`.

## 6. Unified thinking control

The product exposes one control with four levels. Each provider adapter maps it as follows.

| Unified level | DeepSeek request | Xiaomi MiMo request |
|---|---|---|
| `off` | `reasoning_effort="none"` or `thinking={"type":"disabled"}` | `thinking={"type":"disabled"}` |
| `low` | `reasoning_effort="low"` | `thinking={"type":"enabled"}` (no intensity level) |
| `high` | `reasoning_effort="high"` | `thinking={"type":"enabled"}` |
| `max` | `reasoning_effort="max"` | `thinking={"type":"enabled"}` |

Rules:

- Never omit the control. Both providers default to thinking on.
- Force `off` for every tool-calling turn on both providers.
- Force `off` for evaluation runs that need deterministic output, because temperature is ignored while thinking is on.
- MiMo cannot express intensity. The UI offers Off and On; the project-level value for On is `on`, and any `low`, `high`, or `max` request normalizes to `on`. The adapter sends `{"type": "enabled"}`.

## 7. JSON output and tool calling contract for the agent layer

JSON output:

1. Set `response_format={"type": "json_object"}` on both providers.
2. Put the JSON schema and an example in the prompt; the DeepSeek prompt must contain the word `json`.
3. Check `finish_reason` is not `length` before parsing.
4. Parse, validate with pydantic, and retry at most twice with the validation error appended. Then fall back to a safe answer or abstain.
5. Record the provider, model, retry count, and validation failure in the trace.
6. Do not use `json_schema` or the OpenAI SDK's `.beta.parse` helper; neither provider documents support.

Tool calls:

1. Apply `thinking.disable_for_tools` per provider. DeepSeek keeps thinking with `tool_choice: auto`; MiMo defaults to off and needs `reasoning_content` replay when enabled.
2. Send standard function tools. Keep tool names under 64 characters and within the allowed character set.
3. Use `tool_choice="auto"` only. MiMo strips other values; DeepSeek rejects `required` and named choices in thinking mode, and the adapter forces `auto` for DeepSeek thinking turns.
4. After a tool-call turn, append the full assistant message to history, including `reasoning_content` and `tool_calls`. Both providers return 400 when `reasoning_content` is missing on later tool turns while tools are present.
5. Validate `arguments` against the JSON Schema before executing the tool. Both providers may return invalid JSON or invented parameters.
6. Handle parallel tool calls: execute each call, append one `role: tool` message per call.
7. In streaming mode, accumulate tool-call fragments by `index` and emit the tool call only after `finish_reason == "tool_calls"`.

## 8. Configuration mapping

The committed `config/models.yaml` implements the current contract. The relevant shape is:

```yaml
providers:
  deepseek:
    base_url: https://api.deepseek.com
    api_key_env: DEEPSEEK_API_KEY
    max_tokens_field: max_tokens
    models:
      flash: deepseek-flash
  mimo:
    base_url: https://api.xiaomimimo.com/v1
    api_key_env: MIMO_API_KEY
    max_tokens_field: max_completion_tokens
    models:
      flash: mimo-v2.6-flash
      pro: mimo-v2.6-pro
    asr_model: mimo-v2.5-asr

search:
  provider: deepseek
  base_url: https://api.deepseek.com/v1
  api_key_env: DEEPSEEK_API_KEY
  default_count: 10
  need_content: true

thinking:
  mapping:
    deepseek: {"off": none, low: low, high: high, max: max}
    mimo: {"off": disabled, low: enabled, high: enabled, max: enabled}

tts:
  provider: mimo
  models:
    default: mimo-v2.5-tts
  default_voice: mimo_default
  default_format: wav

cache:
  enabled: true
  directory: data/caches/model
```

The per-provider output budget field is part of the provider block: `max_tokens` for DeepSeek and `max_completion_tokens` for MiMo. The loader validates providers, roles, thinking levels, TTS models, and cache settings, and fails closed on a missing key.

Cache behavior (`cache` section): the adapter caches non-stream chat results, streaming event sequences, ASR transcripts, TTS audio, and search/fetch payloads. Keys combine provider, model, and request parameters (audio bytes are hashed for ASR) and are content addressed with SHA-256. Values are JSON under `cache.directory`, resolved relative to the repository root or an explicit `base_dir`. Every cached method accepts `use_cache=False`; cache I/O errors and corrupt entries count as misses. Streaming entries replay the stored event sequence immediately, so they preserve content but not the original token timing.

## 9. Failure modes and provider-specific gotchas

DeepSeek:

- Thinking on by default with a 64K default output budget; a plain call is slow and silently ignores temperature.
- `tool_choice="required"` and named tools return 400 in thinking mode.
- Tool turns require echoing `reasoning_content` in every later request.
- `stream_options.include_usage` has no empty-choices usage chunk.
- JSON mode can return empty content.
- Search and Fetch are separate REST APIs under `/v1/tools/`, not chat tools.

Xiaomi MiMo:

- Thinking on by default; temperature and top_p are forced while it is enabled.
- Tool calls are unstable with thinking on; keep thinking off for tool turns by default. Enabling it requires echoing `reasoning_content` on later requests.
- `tool_choice` is `auto` only; forcing is impossible.
- The usage-only final chunk has `choices: []`.
- ASR accepts only mp3 and wav, base64 data URLs, at most 10 MB, and one clip per request.
- No local file upload; images, audio, and video must be public URLs or base64.
- Model ids are lowercase and were renamed twice in two quarters; keep them in config.

Both providers:

- No `json_schema`, no strict structured output.
- Images must be in `user` messages on DeepSeek.
- `reasoning_content` is a non-standard field; serializers that drop unknown fields will break tool rounds.
- The two APIs differ in output budget field names and base URL forms; a shared client needs a per-provider adapter.

## 10. Unverified items

Live smoke verification on 2026-10-29: `scripts/smoke_model_adapter.py` exercised DeepSeek flash chat, streaming, image input, search, and fetch, plus MiMo flash and pro chat, ASR, audio-file input, and TTS with the live keys; all ten steps passed. The model ids and request shapes in sections 3 and 4 are therefore exercised for the basic paths, while the limits and combinations below remain unverified.

- DeepSeek: images combined with thinking or with tools; `json_schema` on chat completions; `parallel_tool_calls`, `seed`, and `n`; exact SSE wire sample; whether `deepseek-v4-pro` rejects image blocks with an error.
- MiMo: whether `json_schema` returns 400 or is ignored; `max_tokens` alias; `seed`, `n`, `logprobs`, `stream_options`; maximum parallel tool calls and maximum media per request; ASR maximum duration and sample-rate requirements; thinking combined with `json_object`; `force_search` versus `forced_search` in the MiMo web search docs.
- MiMo audio and TTS: latency and token cost of audio-file omni calls compared with ASR; TTS speech quality, long-text behaviour, voice-clone quality and consent handling, and whether the free period persists. Streaming chunk format was verified on 2026-11-10 with a short live request: `stream: true` and `audio.format: pcm16` returned 13 `chat.completion.chunk` frames over `text/event-stream`, each `choices[0].delta.audio.data` carrying base64 PCM16 at 24 kHz mono and 16-bit little endian, with `finish_reason: stop` and a `data: [DONE]` marker. The first frame arrived in 0.623 s, the stream finished in 1.508 s, and 153600 bytes decoded to 3.2 s of audio. Only `mimo-v2.5-tts` offers low-latency streaming; `mimo-v2.5-tts-voicedesign` and `mimo-v2.5-tts-voiceclone` return one compatibility frame after inference finishes.
- Both: real quality and latency on the course corpus, cost under our workload, and behaviour when mixing images with tool loops. These need a small live smoke test rather than more document reading.

## 11. Sources

DeepSeek, all under `https://api-docs.deepseek.com/zh-cn/`:

- `quick_start/pricing`, `api/create-chat-completion`, `quick_start/rate_limit`, `quick_start/error_codes`
- `guides/vision`, `guides/thinking_mode`, `guides/json_mode`, `guides/tool_calls`, `guides/files_api`
- `guides/search`, `api/search`, `api/fetch`
- `guides/responses_api`, `guides/anthropic_api`, `guides/multi_round_chat`
- `updates`, `news/news261017`

Xiaomi MiMo, all under `https://mimo.mi.com/docs/zh-CN/`:

- `quick-start/summary/model`, `quick-start/summary/first-api-call`
- `api/chat/openai-api`, `api/model/list-models`, `api/guidance/rate-limit`, `api/guidance/error-codes`, `api/guidance/model-hyperparameters`
- `quick-start/usage-guide/text-generation/deep-thinking`, `.../structured-output`, `.../tool-calling/web-search`
- `quick-start/usage-guide/multimodal-understanding/image-understanding`, `.../audio-understanding`, `.../video-understanding`
- `quick-start/usage-guide/audio/Speech-Recognition`, `api/audio/Speech-Recognition`
- `price/pay-as-you-go`, `updates/deprecate`, `updates/model`, `news/latest/v2-6`
- `quick-start/faq/api-integration`

Page snapshots and the longer raw notes from the browser session were kept outside the repository during research. Model ids and limits are as reported on 2026-10-29 and must be re-checked against the provider documentation before a live run.
