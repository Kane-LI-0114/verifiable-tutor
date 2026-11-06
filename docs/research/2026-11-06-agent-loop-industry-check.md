# Agent loop plan: industry and community check

| | |
|---|---|
| **Status** | Complete, first pass |
| **Date** | 2026-11-06 |
| **Scope** | The ten claims recorded in the 2026-11-06 plan: agent loop shape, Chat Completions wire format, LangGraph StateGraph, retrieval as a tool, citation verification, token accounting, conversation state, AI SDK UI message stream, provider function calling, and closed typed tools |
| **Method** | Primary sources only: provider API documentation, framework documentation and the published package source, package registries, the MCP specification, and the AI SDK protocol documentation. Each claim is checked against at least one first-party source. Project files are read for fit and marked as project sources, never as research evidence. Where a repo assumption could not be confirmed, it is marked UNVERIFIED and the primary source is reported as it stands. A second reviewer re-checked the three riskiest areas; [Independent cross-check](#independent-cross-check) records the result |
| **Access date** | 2026-11-06, all URLs below were fetched on that date |

## Verdict summary

| # | Claim | Verdict | Confidence | Key source |
|---|---|---|---|---|
| 1 | The minimal agent loop is model tool call, tool execution, result to model, answer, with a step cap | Holds | High | OpenAI function calling guide, "The tool calling flow"; Anthropic "The agentic loop (client tools)" |
| 2 | Keep the OpenAI-compatible Chat Completions `tools` / `tool_choice` format and streaming `tool_calls` deltas as the adapter foundation | Holds with changes | High | OpenAI migration guide; DeepSeek chat completion reference; MiMo chat completion reference |
| 3 | A small LangGraph `StateGraph` (agent node, tool node, conditional edge, step cap) instead of a hand-written loop | Holds with changes | High | LangGraph graph API, "Recursion limit"; `langgraph.prebuilt.ToolNode` docstring in 1.1.1 |
| 4 | Retrieval as a `retrieve_course_material` tool, with document-scoped injection kept separate | Holds | High | LangChain retrieval, "RAG architectures" and "Agentic RAG" |
| 5 | Deterministic citation verification (normalized span match on the cited page, one repair round, otherwise abstain) | Holds with changes | Medium | Anthropic Citations, "Comparison with prompt-based approaches" and "Citation indices" |
| 6 | Stream usage from the provider with `stream_options.include_usage` and persist prompt and completion tokens | Holds with changes | High for DeepSeek, medium overall | OpenAI Python SDK 3.41.0 `ChatCompletionStreamOptionsParam`; DeepSeek `stream_options`; MiMo chunk schema |
| 7 | Keep tool messages out of the replayed conversation history and persist tool traces in a table | Holds with changes | Medium | DeepSeek "Inserting Tool Calls Mid-Conversation"; Anthropic context editing, "Tool result clearing" |
| 8 | AI SDK UI message stream v1 with a custom `data-step` part to stream progress and tool activity | Holds with changes | High | AI SDK 5 stream protocol; AI SDK 7 stream protocol |
| 9 | DeepSeek and Xiaomi MiMo both support OpenAI-style function calling with the pinned models | Holds with changes | High | DeepSeek Models and Pricing; MiMo Models; MiMo and DeepSeek chat completion references |
| 10 | A closed set of typed tools, with no generic shell, matches current safety practice | Holds | High | MCP specification, "Security and Trust & Safety" and Server Tools; OpenAI function calling, "Best practices for defining functions" |

No repository assumption is contradicted. `langgraph` 1.2.18 and `langgraph-checkpoint-sqlite` 3.1.2 both exist on PyPI, the dependency list in ADR-0008 matches the published metadata, and the model ids `deepseek-flash`, `mimo-v2.6-flash`, and `mimo-v2.6-pro` are all current. Two assumptions inside the plan itself do not survive: that the pinned AI SDK line is current, and that the step cap is something the framework will enforce for you.

## Findings by theme

### Agent loop and function calling

**Claim 1. The minimal loop still has four steps plus a cap.**

- Source: https://platform.openai.com/docs/guides/function-calling (page "Function calling", section "The tool calling flow"), no publication date shown on the page, accessed 2026-11-06.
- Quote: "Tool calling is a multi-step conversation between your application and a model via the OpenAI API. The tool calling flow has five high level steps: 1. Make a request to the model with tools it could call. 2. Receive a tool call from the model. 3. Execute code on the application side with input from the tool call. 4. Make a second request to the model with the tool output. 5. Receive a final response from the model (or more tool calls)".
- Reading: the four-part loop in the claim is the same loop the provider documents. Step 5 is where the cap lives: the provider keeps returning tool calls for as long as the application keeps sending results back, so the stop condition is application policy, not protocol. The loop has moved onto the provider only when provider-run built-in tools are used; for a tool the application executes, the loop is still the caller's. The Responses migration guide (https://platform.openai.com/docs/guides/migrate-to-responses) describes the Responses API as offering "an agentic loop by default", which is the server-side variant, not a replacement for this shape.

- Source: https://docs.claude.com/en/docs/agents-and-tools/tool-use/how-tool-use-works (section "The agentic loop (client tools)"), no date shown, accessed 2026-11-06.
- Quote: "The canonical shape is a `while` loop keyed on `stop_reason`" and "while `stop_reason == \"tool_use\"`, run the tools and continue the conversation". The same page notes that Anthropic's own server-side loop "has an iteration limit".
- Reading: Anthropic also treats the loop as application code and pairs it with an iteration limit. Neither provider specifies a number.

- Source (step cap default in practice): https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/run_config.py, line 45, `DEFAULT_MAX_TURNS = 10`, no release date checked; the constant is in the current `main` branch, accessed 2026-11-06. The published doc describes the parameter at https://openai.github.io/openai-agents-python/ref/run/ : "`max_turns`: The maximum number of turns to run the agent for. A turn is defined as one AI invocation (including any tool calls that might occur)."
- Reading: a first-party agent runtime defaults to 10 AI invocations per run and raises `MaxTurnsExceeded`. The project's planned 6 model calls is stricter than that default and is inside normal practice.

**Claim 2. Chat Completions `tools` / `tool_choice` plus streaming `tool_calls` deltas as the adapter foundation.**

- Source: https://platform.openai.com/docs/guides/migrate-to-responses (page "Migrate to the Responses API"), no date shown, accessed 2026-11-06.
- Quote: "While Chat Completions remains supported, Responses is recommended for all new projects."
- Reading: the wire format is supported but no longer the recommended default on OpenAI. The recommendation targets OpenAI models; the project calls DeepSeek and MiMo, and Chat Completions is the only shape both of them document under the same field names.

- Source: https://api-docs.deepseek.com/api/create-chat-completion (API reference, request body, `tools` and `tool_choice`), page footer "Copyright 2026 DeepSeek", accessed 2026-11-06.
- Quote: "A list of tools the model may call. Currently, only functions are supported as a tool." and on streaming deltas: "The first chunk of each tool call carries the `id`, `type` and `function` fields; subsequent chunks only carry the `function` arguments."
- Reading: the exact OpenAI-compatible shape the adapter already encodes, including the incremental argument accumulation.

- Source: https://mimo.mi.com/static/docs/api/chat/openai-api-post.md (MiMo OpenAI Chat Completion API, `tool_choice`), no date shown, accessed 2026-11-06.
- Quote: "When a value other than `auto` is passed to `tool_choice`, the backend will remove this field by default, and the model response behavior will still be equivalent to the `auto` mode". The documented enum is `auto` only.
- Reading: `tool_choice` is not portable. The adapter already forces `auto` for MiMo, which is the only value MiMo accepts.

- Source: same MiMo page, streaming chunk object, `tool_calls`, which carries `index`, `id`, `type`, and `function.arguments`.
- Reading: the fields are documented, but the page does not state that the chunks are incremental and must be accumulated by `index`. That part is UNVERIFIED for MiMo (see "Unverified items").

### Orchestration frameworks

**Claim 3. A small `StateGraph` rather than a hand-written loop, because ADR-0008 decided LangGraph.**

- Source: https://docs.langchain.com/oss/python/langgraph/graph-api (section "Recursion limit"), no date shown, accessed 2026-11-06.
- Quote: "The recursion limit caps how many super-steps one run may execute. When the limit is exceeded, LangGraph raises `GraphRecursionError`." and "Starting in version 1.1.4, the default is 10,007 super-steps."
- Reading: the framework has a recursion limit, but the default is effectively no cap. A cap passed as `recursion_limit` counts super-steps, and one loop lap costs two super-steps (agent node, tool node), so 6 model calls is roughly `recursion_limit` 12, not 6.

- Source: https://docs.langchain.com/oss/python/langgraph/graph-api-control-flow (section "Handle recursion with RemainingSteps"), no date shown, accessed 2026-11-06.
- Quote: "`RemainingSteps` is a Python-only managed value for how many steps remain before the recursion limit. Use it to route to a completion path before LangGraph raises `GraphRecursionError`".
- Reading: this is the documented way to turn the cap into a graceful "wrap up" branch instead of an exception. It replaces a hand-rolled counter in the state.

- Source: `langgraph.prebuilt.ToolNode` docstring in the published `langgraph-prebuilt` 1.1.1 wheel (PyPI: https://pypi.org/project/langgraph-prebuilt/1.1.1/), file `langgraph/prebuilt/tool_node.py`, accessed 2026-11-06.
- Quote: "Use `ToolNode` when building custom workflows that require fine-grained control over tool execution". The same docstring adds: "For standard ReAct-style agents, use `create_agent` instead."
- Reading: the project's graph is a custom workflow with named domain nodes, so `ToolNode` plus explicit conditional edges is the documented fit. A standard ReAct agent would be the wrong shape here.

- Source: same wheel, `langgraph/prebuilt/chat_agent_executor.py`, decorator on `create_react_agent`, accessed 2026-11-06.
- Quote: "create_react_agent has been moved to `langchain.agents`. Please update your import to `from langchain.agents import create_agent`." The decorator category is `LangGraphDeprecatedSinceV10`.
- Reading: the older prebuilt ReAct entry point is deprecated in the exact version line the project pins. ADR-0008's rejection of prebuilt ReAct graphs is now the framework's own direction, not only a project preference.

- Source: https://reference.langchain.com/python/langchain/agents/factory/create_agent, no date shown, accessed 2026-11-06.
- Quote: "Creates an agent graph that calls tools in a loop until a stopping condition is met."
- Reading: `create_agent` is the current prebuilt path. Its stopping condition is "no more tool calls", so it still does not give the project a hard budget; that stays in project code either way.

- Source: https://docs.langchain.com/oss/python/langgraph/streaming (section "Use with any LLM"), no date shown, accessed 2026-11-06.
- Quote: "You can use `stream_mode=\"custom\"` to stream data from any LLM API ... even if that API does **not** implement the LangChain chat model interface." The example uses `get_stream_writer()` and a raw `openai` client.
- Reading: this is the mechanism that makes ADR-0008's "nodes call the existing adapter, not LangChain chat model wrappers" work with streaming. With a non-LangChain client, `stream_mode="messages"` has nothing to project, so token deltas must go through the custom writer.

- Source: same page, opening note, accessed 2026-11-06.
- Quote: "For new applications, we recommend event streaming ... the typed-projection API introduced in LangGraph v1.2."
- Reading: the pinned 1.2.x line is the version that introduced it, so the recommendation applies to the project as soon as LangGraph is installed. The older `stream_mode` API is documented but no longer the recommended entry point.

### Retrieval as a tool

**Claim 4. Retrieval as a tool, with the document-scoped path kept separate.**

- Source: https://docs.langchain.com/oss/python/langchain/retrieval (section "RAG architectures", table and "Agentic RAG"), no date shown, accessed 2026-11-06.
- Quote: "The only thing an agent needs to enable RAG behavior is access to one or more tools that can fetch external knowledge, such as documentation loaders, web APIs, or database queries." The table distinguishes "2-Step RAG" ("Retrieval always happens before generation") from "Agentic RAG" ("An LLM-powered agent decides when and how to retrieve during reasoning").
- Reading: both patterns are current and the framework does not rank one above the other. The claim keeps both, which matches the documented "Hybrid" row: "Combines characteristics of both approaches with validation steps".

- Source: same page, latency note under the table, accessed 2026-11-06.
- Quote: "Latency is generally more predictable in 2-Step RAG, as the maximum number of LLM calls is known and capped."
- Reading: the project takes the latency cost of the agentic path. The per-turn model call budget is what restores the predictability this note attributes to 2-step RAG, which is an argument for enforcing the budget, not for dropping the tool.

- Source: https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview (section "When Claude uses tools"), no date shown, accessed 2026-11-06.
- Quote: "It calls a tool when the request maps to that tool's described capability and the answer isn't already in context."
- Reading: with `tool_choice: auto`, the retrieval decision moves to the model. The tool description therefore carries the routing policy, and a vague description silently becomes a routing bug.

### Citation verification

**Claim 5. Deterministic span verification with one repair round and abstention.**

- Source: https://docs.claude.com/en/docs/build-with-claude/citations (section "Comparison with prompt-based approaches"), no date shown, accessed 2026-11-06.
- Quote: "Because the API parses citations into the response formats described in the following sections and extracts `cited_text` directly, citations are guaranteed to contain valid pointers to the provided documents."
- Reading: Anthropic's citations design does not trust the model to produce the quote. The model emits a location, and the API extracts `cited_text` itself, so a cited span is a substring of the supplied document by construction. The claim's verifier is the same idea implemented in project code, because no such API is available on the pinned providers.

- Source: same page, section "Citation indices", accessed 2026-11-06.
- Quote: "Document indices are 0-indexed from the list of all document content blocks in the request" and "Page numbers are 1-indexed with exclusive end page numbers".
- Reading: the guarantee is about pointer validity and index base, not about semantic support. The worked parsing example says: "Check that each field has a value and at least one citation. The API doesn't guarantee either." A span check is a necessary condition, not a sufficient one, and the plan should not describe a passing span as proof of grounding.

- Source: https://api-docs.deepseek.com/quick_start/pricing (feature table, row "Tool Calls" and "Json Output"), accessed 2026-11-06, and https://mimo.mi.com/static/docs/quick-start/summary/model.md (capability list), accessed 2026-11-06.
- Reading: neither provider lists a citations feature. DeepSeek's feature rows are JSON output, tool calls, Responses API, Anthropic API, prefix completion, FIM, and vision. MiMo's are full-modal understanding, text generation, deep thinking, streaming output, function call, structured output, and web search. The verifier is therefore the only guarantee the project has, which is an argument for keeping it deterministic and for logging every failure.

- Source (project, not research): [ADR-0015](../adr/0015-local-knowledge-store-and-chunking.md) says chunks are rebuilt from `blocks`, not from `page.text`, and carry `block_ids` and a union `bbox_norm`.
- Reading: the verifier must check the quoted span against the same text the model was shown. If the model quotes chunk text that came from `blocks` while the verifier normalizes `page.text`, headers and footers differ and valid quotes fail. Case folding and whitespace collapsing are not specified by any source; they are project policy and should be recorded as such.

### Token accounting and streaming usage

**Claim 6. `stream_options.include_usage` plus persisted prompt and completion tokens.**

- Source: installed `openai` 3.41.0, `openai/types/chat/chat_completion_stream_options_param.py`, identical to https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/chat/chat_completion_stream_options_param.py, accessed 2026-11-06.
- Quote: "If set, an additional chunk will be streamed before the `data: [DONE]` message. The `usage` field on this chunk shows the token usage statistics for the entire request, and the `choices` field will always be an empty array." The same docstring warns: "If the stream is interrupted, you may not receive the final usage chunk which contains the total token usage for the request."
- Reading: the OpenAI shape is a final chunk with empty `choices`. The warning means usage is best effort: a cancelled turn or a dropped connection produces no numbers, and the persistence layer needs a null case rather than a required column.

- Source: https://api-docs.deepseek.com/api/create-chat-completion (`stream_options.include_usage`), accessed 2026-11-06.
- Quote: "Note that no separate usage-only chunk is emitted: the statistics ride on the last content chunk, whose `choices` array always contains exactly one element that carries no new content and a non-null `finish_reason`."
- Reading: DeepSeek deliberately breaks the OpenAI shape. A parser that only reads usage from a chunk with empty `choices` gets nothing from DeepSeek, and a parser that only reads the last content chunk gets nothing from OpenAI. The adapter must accept usage on any chunk.

- Source: https://mimo.mi.com/static/docs/api/chat/openai-api-post.md (streaming chunk object, `usage`), accessed 2026-11-06.
- Reading: the chunk schema includes `usage` as an object or null with `prompt_tokens`, `completion_tokens`, `total_tokens`, and a `prompt_tokens_details.cached_tokens` field, but the page documents no `stream_options` parameter at all. MiMo streaming usage is therefore UNVERIFIED in shape and timing.

- Source: https://platform.openai.com/docs/guides/function-calling (section "Token Usage"), accessed 2026-11-06.
- Quote: "functions are injected into the system message in a syntax the model has been trained on. This means callable function definitions count against the model's context limit and are billed as input tokens."
- Reading: a tool loop changes the input token curve even when the conversation does not grow. Per-call accounting is the only way to see that.

- Source (project, not research): [todo.md](../todo.md) VT-02 records that "The adapter already parses usage and drops it", and `src/verifiable_tutor/api/chat.py` ignores `StreamEvent(kind="usage")` in its frame loop.
- Reading: the transport exists; the sink does not. That is a wiring gap, not a design question.

### Conversation state and memory

**Claim 7. Tool messages out of the replayed history, traces in a table.**

- Source: https://api-docs.deepseek.com/guides/tool_calls (section "Inserting Tool Calls Mid-Conversation"), accessed 2026-11-06.
- Quote: "The Chat Completion API does not support inserting tool calls mid-conversation but does support inserting `system` messages mid-conversation".
- Reading: on the Chat Completions shape the result message is bound to the call by id. DeepSeek documents the `tool` message field `tool_call_id` as "Tool call that this message is responding to" and marks it required (https://api-docs.deepseek.com/api/create-chat-completion). Replaying a tool exchange from an earlier turn is not something the wire format invites, so dropping them is compatible with the protocol, not a lossy hack.

- Source: https://docs.claude.com/en/docs/build-with-claude/context-editing (section "Tool result clearing"), no date shown, accessed 2026-11-06.
- Quote: "The `clear_tool_uses_20250919` strategy clears tool results when conversation context grows beyond your configured threshold. This is particularly useful for agentic workflows with heavy tool use. Older tool results (such as file contents or search results) are no longer needed once Claude has processed them."
- Reading: the industry pattern is to drop old tool results and keep the conversation. The claim applies it unconditionally to prior turns instead of above a threshold, which is stricter but in the same direction. Anthropic's version replaces cleared results with placeholder text so the model knows something was removed; the project should decide whether the assistant text alone is enough.

- Source: https://platform.openai.com/docs/guides/migrate-to-responses (section "Additional differences"), accessed 2026-11-06.
- Quote: "In Chat Completions, conversation state must be managed manually."
- Reading: there is no server-side thread to lean on. Transcript assembly is project code either way, so the choice of what to replay is a project decision with no framework default to inherit.

- Source (project, not research): `src/verifiable_tutor/storage.py` constrains `messages.role` to `system`, `user`, and `assistant`, and `api/chat.py` filters replayed history to `user` and `assistant`. The `tool_calls` table stores `name`, `command_json`, `exit_code`, `output`, and `status`, keyed to a message by `position`.
- Reading: the schema already forbids storing tool messages, so the claim describes the current shape rather than changing it. The gap is the reverse direction: within a turn, the loop must hold assistant `tool_calls` and `tool` results somewhere, and there is no column for the provider `tool_call_id` or for parsed arguments. That is a schema change the loop forces.

### UI streaming protocol

**Claim 8. AI SDK UI message stream v1 with a custom `data-step` part.**

- Source: https://v5.ai-sdk.dev/docs/ai-sdk-ui/stream-protocol (AI SDK 5 documentation, the pinned line), accessed 2026-11-06.
- Quote: "When you provide data streams from a custom backend, you need to set the `x-vercel-ai-ui-message-stream` header to `v1`." and "The `data-*` type pattern allows you to define custom data types that your frontend can handle specifically."
- Reading: the header and the custom `data-step` part are exactly what the documentation specifies for a non-TypeScript backend. The claim holds on the pinned version.

- Source: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol (AI SDK 7 documentation, current), accessed 2026-11-06.
- Quote: the same instruction, "you need to set the `x-vercel-ai-ui-message-stream` header to `v1`", with the same `data-weather` example for a custom `data-*` part.
- Reading: the protocol version did not change across the majors, so the backend encoder survives an AI SDK upgrade. The part vocabulary did grow: the v7 page adds `reset-step`, `tool-approval-request`, `tool-output-denied`, `steering-message`, and a `custom` part with provider metadata. Step boundaries are not a v7-only feature: the installed `ai` 5.0.285 types already include `start-step` and `finish-step`, so the pinned line can emit them today.

- Source: https://v5.ai-sdk.dev/docs/ai-sdk-ui/stream-protocol (section "Finish Step Part"), accessed 2026-11-06.
- Quote: "This part is necessary to correctly process multiple stitched assistant calls, e.g. when calling tools in the backend, and using steps in `useChat` at the same time."
- Reading: a tool loop is precisely multiple backend model calls inside one assistant message. The project emits `start`, `text-*`, `reasoning-*`, `data-step`, `finish`, and `[DONE]`, and no step boundaries. That is the one structural gap in claim 8.

- Source: same page, sections "Tool Input Start Part", "Tool Input Delta Part", "Tool Input Available Part", "Tool Output Available Part", accessed 2026-11-06.
- Quote: `{"type":"tool-input-start","toolCallId":"...","toolName":"..."}`, `{"type":"tool-input-delta","toolCallId":"...","inputTextDelta":"..."}`, `{"type":"tool-input-available","toolCallId":"...","toolName":"...","input":{...}}`, `{"type":"tool-output-available","toolCallId":"...","output":{...}}`.
- Reading: the protocol has native parts for exactly the tool activity in claim 8. A custom `data-step` part can carry it, but then the frontend has to render tool state itself instead of using the parts `useChat` already understands.

- Source: npm registry dist-tags for `ai` and `@ai-sdk/react`, https://registry.npmjs.org/ai and https://registry.npmjs.org/@ai-sdk%2Freact, accessed 2026-11-06.
- Reading: `latest` is `ai` 7.0.163 and `@ai-sdk/react` 4.0.167, while the `ai-v5` tag is `ai` 5.0.285 and `@ai-sdk/react` 2.0.288, which is what the project pins. The pin is the last release of the v5 line, two majors behind. Vercel still publishes the tag, so the pin is supported, but it is a maintenance liability rather than a current choice.

### Provider support

**Claim 9. DeepSeek and MiMo function calling with the pinned models.**

- Source: https://api-docs.deepseek.com/quick_start/pricing (Model Details), page footer "Copyright 2026 DeepSeek", accessed 2026-11-06.
- Quote: the model id `deepseek-flash` is listed with "MODEL VERSION DeepSeek-V4.1-Flash-1017", "CONTEXT LENGTH 1M", "MAXIMUM: 384K" output, and the feature row "Tool Calls" checked.
- Reading: the id in `config/models.yaml` exists and supports tools. The 384K output ceiling matches the `max_tokens` range the config records.

- Source: https://mimo.mi.com/static/docs/quick-start/summary/model.md (Text Generation Model table), accessed 2026-11-06.
- Quote: `mimo-v2.6-pro` and `mimo-v2.6-flash` share the capability list "Full-modal Understanding, Text Generation, Deep Thinking, Streaming Output, Function Call, Structured Output, Web Search", with "Context Window: 1M" and "Maximum Output: 128K".
- Reading: both pinned MiMo ids exist and advertise function calling. 128K output matches the `max_completion_tokens` default and maximum of 131072 in the project config.

- Source: https://api-docs.deepseek.com/api/create-chat-completion (`tool_choice`), accessed 2026-11-06.
- Quote: "`required` and named tool choices are not supported in thinking mode; the API returns a 400 error. Disable thinking mode first to use them."
- Reading: the restriction is narrower than "no tools in thinking mode". DeepSeek allows tools with thinking while `tool_choice` stays `auto`, and rejects only `required` and named choices. The project's `disable_for_tools: true` is therefore stricter than the provider requires, and the reason to keep it is different: thinking plus tools also changes what has to be replayed, as the MiMo note below shows.

- Source: https://mimo.mi.com/static/docs/api/chat/openai-api-post.md (`thinking` and `tools` descriptions), accessed 2026-11-06.
- Quote: "During the multi-turn tool calls process in thinking mode, the model returns a `reasoning_content` field alongside `tool_calls`. To continue the conversation, it is recommended to keep all previous `reasoning_content` in the `messages` array for each subsequent request to achieve the best performance."
- Reading: if the project ever enables thinking with tools on MiMo, claim 7's "keep tool messages out of history" collides with the provider's recommendation to keep `reasoning_content`. With thinking disabled for tool turns, the collision does not arise.

- Source: https://platform.openai.com/docs/guides/migrate-to-responses (section "Additional differences"), accessed 2026-11-06.
- Quote: "Starting with GPT-5.4, Chat Completions does not support tool calling with `reasoning_effort` values other than `none`."
- Reading: the reasoning-plus-tools conflict is general enough that OpenAI resolved it by requiring a different API. The restriction is not inherited here, because both project providers document tool calls together with thinking. The project still disables thinking for tool turns, which avoids the reasoning replay requirement MiMo documents.

### Tool safety

**Claim 10. A closed set of typed tools, no generic shell.**

- Source: https://modelcontextprotocol.io/specification/2026-07-28/server/tools (warning above "Capabilities"), specification dated 2026-07-28, accessed 2026-11-06.
- Quote: "For trust & safety and security, there **SHOULD** always be a human in the loop with the ability to deny tool invocations." The page also asks applications to "Provide UI that makes clear which tools are being exposed to the AI model" and to "Insert clear visual indicators when tools are invoked".
- Reading: the specification's baseline is visibility plus a denial path, and it states that baseline for tool invocations generally, not for a subset. ADR-0009 applies the interrupt to execution tools and relies on visibility for read-only ones, which is narrower than the spec's SHOULD and should be presented as a deliberate narrowing rather than as compliance.

- Source: https://modelcontextprotocol.io/specification/latest (section "Security and Trust & Safety"), accessed 2026-11-06.
- Quote: "Tools represent arbitrary code execution and must be treated with appropriate caution. In particular, descriptions of tool behavior such as annotations should be considered untrusted, unless obtained from a trusted server."
- Reading: a closed tool set with in-process handlers removes the untrusted-server problem entirely, because the descriptions are project constants. This is a stronger position than the spec assumes.

- Source: https://modelcontextprotocol.io/specification/2026-07-28/server/tools (section "Tool"), accessed 2026-11-06.
- Quote: "`inputSchema`: JSON Schema defining expected parameters ... **MUST** be a valid JSON Schema object (not `null`)", defaulting to 2020-12 when no `$schema` is present.
- Reading: if the project's typed tools are ever exposed over MCP, the argument schemas already required by ADR-0009 map one to one. Until then MCP is not needed for a single-process tool set.

- Source: https://platform.openai.com/docs/guides/function-calling (section "Best practices for defining functions"), accessed 2026-11-06.
- Quote: "Keep the number of initially available functions small for higher accuracy." and "Aim for fewer than 20 functions available at the start of a turn at any one time".
- Reading: a closed set of a handful of domain tools is well inside the guidance, and every extra tool costs input tokens on every call.

- Source: https://docs.claude.com/en/docs/agents-and-tools/tool-use/define-tools (section "Best practices for tool definitions"), accessed 2026-11-06.
- Quote: "Consolidate related operations into fewer tools. Rather than creating a separate tool for every action (`create_pr`, `review_pr`, `merge_pr`), group them into a single tool with an `action` parameter."
- Reading: the pressure runs toward fewer, coarser tools. A per-page read tool and a per-span verify tool may be justified by auditability, but that is a deliberate trade against the default advice.

## Independent cross-check

A second reviewer checked the three highest-risk areas against the same primary sources. The verdicts above survived, with these confirmations and one sharpening.

- LangGraph pins are real and one patch behind. `langgraph` 1.2.18 (uploaded 2026-10-26) and `langgraph-checkpoint-sqlite` 3.1.2 (2026-10-12) exist on PyPI; the current releases are 1.2.20 (2026-11-05) and 3.1.3 (2026-10-30). `create_react_agent` is deprecated in LangGraph v1 in favor of `langchain.agents.create_agent`; `StateGraph` plus `ToolNode` remains the documented fine-grained path, which is the shape ADR-0008 already chose. Sources: https://pypi.org/pypi/langgraph/json, https://docs.langchain.com/oss/python/migrate/langgraph-v1.md.
- AI SDK protocol parts are confirmed in the pinned line. The installed `ai` 5.0.285 typings include `tool-input-start`, `tool-input-delta`, `tool-input-available`, `tool-output-available`, `tool-output-error`, `start-step`, and `finish-step`; `text-delta` and `reasoning-delta` use the `delta` field. The v1 header is unchanged. Source: `src/verifiable_tutor/ui/web/node_modules/ai/dist/index.d.ts`, https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol.
- Provider function calling is confirmed, with one portability limit. DeepSeek documents `tools`, `tool_choice` (`none`/`auto`/`required`/named), streaming `tool_calls` deltas, and `stream_options.include_usage`. MiMo documents function calling but honors only `tool_choice: auto`; a non-`auto` value is silently removed, and streaming usage is undocumented. The most consequential mismatch for the plan is that a forced tool call is portable only on DeepSeek. The adapter already hardcodes `auto` for MiMo, so the project does not depend on the unsupported behavior, but no verifier step may rely on `tool_choice: required` on MiMo. Sources: https://api-docs.deepseek.com/api/create-chat-completion, https://mimo.mi.com/static/docs/api/chat/openai-api-post.md.
- DeepSeek Search and Fetch endpoints are current. The configured `https://api.deepseek.com/v1/tools/search` and `/v1/tools/fetch` match the 2026 guide, so the unused client remains a viable P1 path. Source: https://api-docs.deepseek.com/guides/search.

## Project fit

| Area | Verdict | Where | Why |
|---|---|---|---|
| Single model call today | Deviation | `src/verifiable_tutor/api/chat.py` (`begin_turn` calls `adapter.chat_stream` once) | The loop does not exist. This is planned as VT-07, so it is a known gap, not a surprise |
| Provider call boundary | Match | `src/verifiable_tutor/llm/adapter.py` (`_prepare_chat`, `_events_from_chunks`) | Already sends `tools` and `tool_choice`, forces `auto` for MiMo, disables thinking for tool turns, and forwards `tool_calls` deltas with their `index` so a caller can accumulate them |
| DeepSeek Search and Fetch client | Match | `config/models.yaml`, `src/verifiable_tutor/llm/adapter.py` | The configured `/v1/tools/search` and `/v1/tools/fetch` endpoints match the 2026 guide, so the unused client remains a viable P1 path |
| Streaming token usage | Deviation | `api/chat.py` `_frame_stream` ignores `StreamEvent(kind="usage")` | The provider numbers are parsed and dropped. VT-02 is the sink |
| Usage final-chunk shape | Risk | `llm/adapter.py` `_events_from_chunks` | It only reads `chunk.usage` when present, which covers both the OpenAI empty-`choices` chunk and the DeepSeek last content chunk. It does not handle an interrupted stream, where OpenAI may never send one, so a required token column would break a cancelled turn |
| Tool message storage | Match | `storage.py` `messages.role` CHECK, `api/chat.py` `_history` | The schema already forbids `tool` rows, so claim 7 is the current shape |
| Tool trace schema | Risk | `storage.py` `tool_calls` (`name`, `command_json`, `exit_code`, `output`, `status`) | No `tool_call_id` and no parsed `arguments`. A loop cannot correlate a result with the model's call, and replay cannot rebuild the exchange |
| Within-turn tool messages | Risk | `orchestrator/` is a `.gitkeep` placeholder | They can only live in graph state and the checkpointer. Nothing in SQLite can hold them, so a crashed turn loses the exchange unless the JSONL trace has it |
| Citation record | Match | `storage.py` `citations` (`doc_id`, `page_no`, `quoted_span`, `bbox_norm`, `verified_at`) | The columns the verifier needs already exist and are empty |
| Verifier input text | Risk | `docs/adr/0015` (chunks rebuilt from `blocks`), `corpus/chunker.py` | Verifying against `page.text` while the model quotes chunk text will fail valid quotes, because headers and footers are dropped from chunks |
| UI stream encoder | Deviation | `api/streaming.py` (no `start-step`, `finish-step`, or `tool-*` parts) | The encoder is correct for a single call and incomplete for a multi-call turn |
| UI part consumption | Match | `ui/web/src/lib/chat/ui-message.ts` (`TutorDataParts` = `{ step: WorkStepData }`) | `data-step` is typed and rendered. Adding `data-tool` is a local type change with no protocol change |
| AI SDK version | Risk | `ui/web/package.json` (`ai` 5.0.285, `@ai-sdk/react` 2.0.288) | Two majors behind `latest` (7.0.163 / 4.0.167). The protocol is stable, but upgrade cost accrues |
| LangGraph dependency | Deviation | `pyproject.toml` (no `langgraph`), `docs/adr/0008` (pins 1.2.18, checkpoint-sqlite 3.1.2) | Neither package is installed. Both pins exist on PyPI, so the ADR is accurate, and `pyproject.toml` is simply not updated yet |
| SQLite checkpointer | Risk | `docs/adr/0008` fallback clause, PyPI metadata for 3.1.2 | `sqlite-vec` is a declared dependency of the checkpointer, not an extra. The native extension is the same risk ADR-0008 already names for the PRoot runtime |
| Checkpoint growth | Risk | `docs/adr/0008` (one thread per user and session) | LangGraph documents unbounded checkpoint growth and recommends pruning. Nothing in the project prunes |
| LangGraph event streaming | Risk | `docs/adr/0008` (event streams to AI SDK frames) | With the adapter outside LangChain, `stream_mode="messages"` will not see model tokens. The documented route is `get_stream_writer` with custom mode |
| Local, no inbound service | Match | `docs/adr/0011`, `docs/adr/0008` (no LangGraph Platform) | LangGraph runs in process. None of the hosted-agent advice in the OpenAI or LangChain docs applies, and none of it is needed |
| TACC offline batch | Match, with a boundary | `docs/adr/0011`, AGENTS.md | The loop, the verifier, and token accounting all run on the laptop. TACC stays a batch backend, so the loop adds no job latency |
| MCP | Not applicable yet | `docs/adr/0009` closed tool set | MCP is the current standard for third-party tools, and the safety rules transfer. A single-process typed tool set does not need the protocol, and ADR-0009's interrupt covers the human-in-the-loop requirement |

## Recommended adjustments

Ordered by dependency. Each item names the source that motivates it.

1. **Add step boundaries and native tool parts to the stream encoder.** Wrap each model call in `start-step` and `finish-step`, and emit `tool-input-start`, `tool-input-delta`, `tool-input-available`, and `tool-output-available` alongside the existing `data-step`. Use `tool-output-error` for a failed call; `tool-output-denied` arrives with the v7 upgrade. If the UI keeps its own tool renderer, add a `data-tool` part and type it in `TutorDataParts`. The local check that these parts exist before the upgrade is the installed typing file `src/verifiable_tutor/ui/web/node_modules/ai/dist/index.d.ts` (`ai` 5.0.285). Motivated by the AI SDK 5 protocol (https://v5.ai-sdk.dev/docs/ai-sdk-ui/stream-protocol), section "Finish Step Part": the part "is necessary to correctly process multiple stitched assistant calls, e.g. when calling tools in the backend".

2. **Enforce the cap twice: `recursion_limit` plus `RemainingSteps` for the graph, and a model-call counter for the budget.** Do not treat `recursion_limit` as the model-call budget. The default is 10,007 super-steps and each loop lap costs two. Calibrate the model-call number against the OpenAI Agents SDK default of 10 per run, and keep 6 if cost matters more than depth. Motivated by the LangGraph "Recursion limit" (https://docs.langchain.com/oss/python/langgraph/graph-api) and "RemainingSteps" (https://docs.langchain.com/oss/python/langgraph/graph-api-control-flow) sections, and by `DEFAULT_MAX_TURNS = 10` in https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/run_config.py.

3. **Stream model deltas through `get_stream_writer()` in custom mode.** `stream_mode="messages"` projects LangChain chat model output, and the adapter is not a LangChain chat model by ADR-0008's own design. Prefer the v1.2 typed event streaming over `stream_mode` where possible. Motivated by the LangGraph streaming sections "Use with any LLM" and the v1.2 recommendation (https://docs.langchain.com/oss/python/langgraph/streaming).

4. **Persist usage on the first chunk that carries it, and allow a null.** Accept usage on an empty-`choices` chunk (OpenAI) or on the last content chunk (DeepSeek), and record that a cancelled stream may have none. Add provider, model, role, prompt, completion, and total columns keyed to the message or call. Motivated by the OpenAI SDK docstring (https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/chat/chat_completion_stream_options_param.py) and the DeepSeek `include_usage` note (https://api-docs.deepseek.com/api/create-chat-completion).

5. **Add `tool_call_id` and `arguments_json` to `tool_calls`, and keep the provider call id in graph state.** The model's `id` is the only key that binds a result to a call when several calls arrive in one response. Motivated by the DeepSeek streaming delta contract (https://api-docs.deepseek.com/api/create-chat-completion) and OpenAI's "it is best practice to assume there are several" calls (https://platform.openai.com/docs/guides/function-calling).

6. **Decide the parallel tool call policy explicitly.** Neither provider documents `parallel_tool_calls`. Either fan out and join, or reject more than one call per response with a visible error. Motivated by the absence of `parallel_tool_calls` in https://api-docs.deepseek.com/api/create-chat-completion and https://mimo.mi.com/static/docs/api/chat/openai-api-post.md, and by the OpenAI best practice to assume several calls.

7. **Verify spans against chunk text, and record the normalization as project policy.** Normalize with NFKC, collapse whitespace including line breaks introduced by block boundaries, and casefold. Check the chunk text first and the page text second, and log which one matched. Motivated by Anthropic's extract-don't-trust design (https://docs.claude.com/en/docs/build-with-claude/citations) and by ADR-0015's decision that chunks come from `blocks` (project source).

8. **Enable strict schemas where they are documented and free, and validate arguments in code everywhere.** MiMo documents `strict: true` with a subset of JSON Schema. DeepSeek documents strict mode as a Beta that requires the `/beta` base URL, so it is a base URL change rather than a flag. OpenAI's strict mode requires `additionalProperties: false` and every property in `required`. Validate the parsed arguments before dispatch regardless. Motivated by the MiMo `strict` field (https://mimo.mi.com/static/docs/api/chat/openai-api-post.md), the DeepSeek strict mode note (https://api-docs.deepseek.com/guides/tool_calls), the OpenAI strict mode section (https://platform.openai.com/docs/guides/function-calling), and the DeepSeek warning that the model "does not always generate valid JSON".

9. **Prune checkpoints per thread.** One thread per user and session accumulates state indefinitely, and the framework documentation names this as a known growth problem. Motivated by the LangGraph persistence troubleshooting entry "Checkpoints growing unboundedly" (https://docs.langchain.com/oss/python/langgraph/persistence).

10. **Plan the AI SDK upgrade as a separate change.** Keep the v1 header and the `data-*` parts, which survive, and treat the v6 and v7 additions as additive. Motivated by the npm dist-tags (https://registry.npmjs.org/ai) and the unchanged v1 header in the v7 protocol page (https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol).

## Unverified items and how to verify them

| Item | Status | What the primary source shows | How to verify |
|---|---|---|---|
| MiMo streaming usage semantics | UNVERIFIED | The chunk schema has `usage`, but no `stream_options` parameter is documented | One paid MiMo streaming call with tools; inspect whether any chunk carries non-null `usage` and whether it is the last one |
| MiMo incremental `tool_calls` deltas | UNVERIFIED | The chunk schema has `index`, `id`, and `function.arguments`, but the page does not say the chunks are partial | One paid MiMo streaming call with a tool; confirm that arguments arrive in fragments that must be concatenated by `index` |
| Parallel tool calls on DeepSeek and MiMo | UNVERIFIED | No `parallel_tool_calls` field appears in either reference | A prompt that invites two calls; observe whether one response carries two entries in `tool_calls` |
| `sqlite-vec` under the PRoot runtime | UNVERIFIED | PyPI declares `sqlite-vec>=0.1.6` as a dependency of `langgraph-checkpoint-sqlite` 3.1.2 | The TACC import spike ADR-0008 already schedules: import `langgraph`, open a `SqliteSaver`, write and read one checkpoint |
| LangGraph 1.2 typed event streaming surface | UNVERIFIED locally | The docs describe event streaming as "the typed-projection API introduced in LangGraph v1.2", and the project pins 1.2.18, but nothing is installed | After the install, import and call `stream_events` once in a unit test |
| LangGraph pin freshness | Confirmed, one patch behind | PyPI shows `langgraph` 1.2.18 uploaded 2026-10-26 and 1.2.20 uploaded 2026-11-05; `langgraph-checkpoint-sqlite` 3.1.2 uploaded 2026-10-12 and 3.1.3 uploaded 2026-10-30 | Decide whether to move to 1.2.20 and 3.1.3 before the lock is written, since the pins must move together |
| DeepSeek strict mode | UNVERIFIED against the project base URL | The guide says strict mode needs `base_url="https://api.deepseek.com/beta"`, while `config/models.yaml` uses `https://api.deepseek.com` | One paid call to the beta base URL with a strict schema, or leave strict off for DeepSeek |
| Whether `data-step` survives an AI SDK upgrade | Confirmed in principle, not in code | The v7 protocol page keeps `data-*` and the v1 header | A component test after the upgrade; the backend encoder should not change |
| Token counts for a tool loop | UNVERIFIED | No source states how tool schemas and results shift the per-turn totals for these two providers | One paid loop run with a recorded transcript, then compare the summed usage to the JSONL trace |

## Sources

All URLs accessed 2026-11-06.

Provider documentation:

- OpenAI, Function calling, https://platform.openai.com/docs/guides/function-calling (sections "The tool calling flow", "Best practices for defining functions", "Token Usage", "Tool choice", "Strict mode", "Parallel function calling")
- OpenAI, Migrate to the Responses API, https://platform.openai.com/docs/guides/migrate-to-responses (sections "Additional differences", "Migrating from Chat Completions")
- OpenAI Python SDK, `ChatCompletionStreamOptionsParam`, installed version 3.41.0, mirrored at https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/chat/chat_completion_stream_options_param.py
- OpenAI Agents SDK, run reference, https://openai.github.io/openai-agents-python/ref/run/ and the `DEFAULT_MAX_TURNS` constant at https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/run_config.py
- Anthropic, Tool use with Claude, https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview (sections "How tool use works", "When Claude uses tools")
- Anthropic, How tool use works, https://docs.claude.com/en/docs/agents-and-tools/tool-use/how-tool-use-works (section "The agentic loop (client tools)")
- Anthropic, Define tools, https://docs.claude.com/en/docs/agents-and-tools/tool-use/define-tools (section "Best practices for tool definitions")
- Anthropic, Citations, https://docs.claude.com/en/docs/build-with-claude/citations (sections "Comparison with prompt-based approaches", "Citation indices", "Token costs")
- Anthropic, Context editing, https://docs.claude.com/en/docs/build-with-claude/context-editing (sections "Overview", "Tool result clearing")
- DeepSeek, Your First API Call, https://api-docs.deepseek.com/
- DeepSeek, Models and Pricing, https://api-docs.deepseek.com/quick_start/pricing (section "Model Details")
- DeepSeek, Create Chat Completion, https://api-docs.deepseek.com/api/create-chat-completion (parameters `stream_options`, `tools`, `tool_choice`, `strict`; response and streaming chunk schemas)
- DeepSeek, Tool Calls guide, https://api-docs.deepseek.com/guides/tool_calls (sections "Thinking Mode", "Inserting Tool Calls Mid-Conversation", "strict Mode (Beta)")
- DeepSeek, Search and Fetch, https://api-docs.deepseek.com/guides/search (endpoint and response schema)
- Xiaomi MiMo, Models, https://mimo.mi.com/static/docs/quick-start/summary/model.md (section "Text Generation Model")
- Xiaomi MiMo, OpenAI Chat Completion API, https://mimo.mi.com/static/docs/api/chat/openai-api-post.md (parameters `tools`, `tool_choice`, `thinking`, `strict`; chunk schema)
- Xiaomi MiMo, OpenAI Responses API, https://mimo.mi.com/static/docs/api/chat/responses-post.md (tool support)

Framework documentation and package source:

- LangGraph, Graph API, https://docs.langchain.com/oss/python/langgraph/graph-api (sections "Super-steps", "Recursion limit")
- LangGraph, Build sequences, branches, and loops, https://docs.langchain.com/oss/python/langgraph/graph-api-control-flow (sections "Impose a recursion limit", "Handle recursion with RemainingSteps")
- LangGraph, Streaming, https://docs.langchain.com/oss/python/langgraph/streaming (sections "Use with any LLM", streaming mode table, opening recommendation)
- LangGraph, Persistence, https://docs.langchain.com/oss/python/langgraph/persistence (sections "Checkpointer vs. store", "Checkpoints growing unboundedly")
- `langgraph-prebuilt` 1.1.1 wheel, https://pypi.org/project/langgraph-prebuilt/1.1.1/ (`langgraph/prebuilt/tool_node.py`, `langgraph/prebuilt/chat_agent_executor.py`)
- LangGraph, Migration guide for v1, https://docs.langchain.com/oss/python/migrate/langgraph-v1.md (sections "Deprecations", `create_react_agent` to `create_agent`)
- LangChain, Agents, https://docs.langchain.com/oss/python/langchain/agents (opening definition; "Context management")
- LangChain, `create_agent` reference, https://reference.langchain.com/python/langchain/agents/factory/create_agent
- LangChain, Retrieval, https://docs.langchain.com/oss/python/langchain/retrieval (sections "RAG architectures", "Agentic RAG", "Hybrid RAG")

Specifications and protocols:

- Model Context Protocol, Specification (latest), https://modelcontextprotocol.io/specification/latest (section "Security and Trust & Safety")
- Model Context Protocol, Server Tools, https://modelcontextprotocol.io/specification/2026-07-28/server/tools (sections "Capabilities", "Tool", warning on human in the loop)

Frontend protocol and packages:

- AI SDK 5, Stream Protocols, https://v5.ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- AI SDK 7, Stream Protocols, https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- npm registry, `ai` dist-tags, https://registry.npmjs.org/ai
- npm registry, `@ai-sdk/react` dist-tags, https://registry.npmjs.org/@ai-sdk%2Freact
- PyPI, `langgraph` metadata, https://pypi.org/pypi/langgraph/json and https://pypi.org/project/langgraph/1.2.18/
- PyPI, `langgraph-checkpoint-sqlite` metadata, https://pypi.org/pypi/langgraph-checkpoint-sqlite/json and https://pypi.org/project/langgraph-checkpoint-sqlite/3.1.2/
- PyPI, `langchain-core` metadata, https://pypi.org/pypi/langchain-core/json

Project sources, cited for fit only:

- [docs/adr/0003-react-spa-with-ai-elements.md](../adr/0003-react-spa-with-ai-elements.md)
- [docs/adr/0008-langgraph-as-agent-orchestration-runtime.md](../adr/0008-langgraph-as-agent-orchestration-runtime.md)
- [docs/adr/0009-typed-agent-tools-instead-of-a-shell.md](../adr/0009-typed-agent-tools-instead-of-a-shell.md)
- [docs/adr/0015-local-knowledge-store-and-chunking.md](../adr/0015-local-knowledge-store-and-chunking.md)
- [docs/todo.md](../todo.md), items VT-02, VT-05, VT-06, VT-07
- [src/verifiable_tutor/llm/adapter.py](../../src/verifiable_tutor/llm/adapter.py)
- [src/verifiable_tutor/api/streaming.py](../../src/verifiable_tutor/api/streaming.py)
- [src/verifiable_tutor/api/chat.py](../../src/verifiable_tutor/api/chat.py)
- [src/verifiable_tutor/storage.py](../../src/verifiable_tutor/storage.py)
- [config/models.yaml](../../config/models.yaml)
- [src/verifiable_tutor/corpus/chunker.py](../../src/verifiable_tutor/corpus/chunker.py)
- [src/verifiable_tutor/ui/web/src/lib/chat/ui-message.ts](../../src/verifiable_tutor/ui/web/src/lib/chat/ui-message.ts)
- [src/verifiable_tutor/ui/web/package.json](../../src/verifiable_tutor/ui/web/package.json)
- [pyproject.toml](../../pyproject.toml)
