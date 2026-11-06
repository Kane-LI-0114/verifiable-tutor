# ADR-0016: Minimal agent loop with typed course and web tools

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-06 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The delivered backend streams one ungrounded model call per turn ([chat.py](../../src/verifiable_tutor/api/chat.py)). The model adapter already accepts `tools`, parses streamed `tool_call` deltas, and reports `finish_reason="tool_calls"` ([adapter.py](../../src/verifiable_tutor/llm/adapter.py)), but no production caller passes tools, no tool registry exists, and the `tool_calls` table has no writer.

[ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md) decided LangGraph as the single orchestration runtime and rejected hand-rolled control flow. [ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md) decided a closed set of typed tools with no generic shell. The 2026-11-06 industry check ([research note](../research/2026-11-06-agent-loop-industry-check.md)) confirms the tool loop, a two-node `StateGraph` for fine-grained control, retrieval as a tool, and the AI SDK v1 protocol with step boundaries and tool parts. It also records two constraints: MiMo honors only `tool_choice: auto`, and OpenAI-compatible usage chunks differ by provider.

The lead requires a first runnable loop with the project's basic tools plus a web search tool that uses the DeepSeek Search and Fetch APIs, and requires one real test with DeepSeek Flash and one with MiMo Flash after implementation.

The local corpus is already ingested (12 documents, 342 pages, 359 chunks) and hybrid retrieval works. The web search and fetch clients exist and their configured endpoints match the 2026 DeepSeek documentation.

## Decision

**One two-node LangGraph workflow per chat turn.** The graph is a typed `StateGraph` with an `agent` node, a `tools` node, and a conditional edge between them. The graph is compiled per request because the tool registry, adapter, and budget are request-scoped; compilation cost is negligible at this size.

**No checkpointer in this slice.** The graph state is one request's in-memory state; there is no interrupt or resume path yet, and conversation persistence remains the existing `messages`, `message_steps`, and `tool_calls` rows. The SQLite checkpointer from ADR-0008 stays on the VT-12 path, where human approval and resumable tool execution need it. This is a recorded stage boundary, not a cancellation of the ADR-0008 decision.

**The model adapter stays outside LangChain.** Nodes call the existing adapter, and model deltas reach the browser through `get_stream_writer()` with `stream_mode="custom"`, because `stream_mode="messages"` cannot project a non-LangChain client. The graph owns control flow only.

**A closed, typed tool registry.** The first tool set is `search_course`, `read_course_page`, `web_search`, and `web_fetch`:

- `search_course` runs the existing hybrid retriever and returns page-anchored chunks with `doc_id`, `page_no`, `chunk_id`, and text.
- `read_course_page` returns the full text of one page so the model can quote before citing.
- `web_search` calls the DeepSeek Search API with `need_content=false` and returns titles, URLs, summaries, dates, and authority.
- `web_fetch` calls the DeepSeek Fetch API and returns page Markdown, truncated, with an untrusted marker.

Arguments are validated by Pydantic models with `extra="forbid"`. Unknown tools, invalid JSON, invalid arguments, and execution failures become failed tool results that are fed back to the model; they never become HTTP 500 responses. Tool output is truncated. `web_fetch` rejects non-HTTP(S), credentialed, over-long, loopback, private, and link-local URLs before calling the API. There is no generic shell and no Python execution tool in this slice.

**Budgets are project code, not framework settings.** At most 5 model calls and 8 tool calls per turn. The last allowed model call receives no tools and a system instruction to answer from the evidence or state what is missing. `recursion_limit` is only a safety net. Tool output is capped by configuration.

**Streaming stays on the AI SDK UI message stream v1.** Each model call is wrapped in `start-step` and `finish-step`. Tool activity uses a project `data-tool` custom part because the UI already renders tool calls from persisted metadata and the custom part keeps one typed representation for live and stored turns. The existing `data-step` part continues to carry the work chain, including `retrieve` when a course search runs. The adapter's usage event is recorded in the JSONL trace and is not persisted in this slice.

**Tool calls are persisted, tool messages are not.** `tool_calls` gains `tool_call_id`, `arguments_json`, `result_json`, and `duration_ms` in schema version 3. Within-turn `assistant(tool_calls)` and `tool` messages live only in graph state; the conversation history keeps user and assistant text, and the tool rows carry the audit trail. A legacy database is upgraded in place by adding the four columns.

**Verification includes a real dual-model smoke.** Unit and HTTP tests use a fake adapter and a fake tool registry. After the suite passes, `scripts/smoke_agent_loop.py` runs one course turn and one web turn with `deepseek/flash` and the same with `mimo/flash`, and probes `search_course`, `web_search`, and `web_fetch` directly. A failed provider is reported and is not replaced by the other provider (ADR-0006).

## Consequences

**Positive:**

- The first closed perceive, decide, act, observe, answer loop exists, with typed tools and a visible work chain.
- The tool loop uses the decided runtime and the decided execution boundary, so later evidence, policy, and practice nodes extend the graph instead of replacing it.
- Tool calls are auditable in SQLite and in the JSONL trace, and the same data drives live rendering, history, and replay.
- The web tools reuse the cached adapter clients, so repeated smoke and evaluation runs make no new paid search calls.
- The schema change is additive and migration is covered by tests.

**Negative:**

- A LangGraph dependency group enters the local environment and `uv.lock`; the TACC import spike is still unrun and no TACC job uses the graph.
- The first slice leaves citations, span verification, token accounting, document-conversation association, and the checkpointer to later items.
- The graph adds a layer of indirection over what is still a short loop.
- Tool-call preambles are streamed and persisted as part of the answer text, which can read less cleanly than a final-only answer.

**Neutral:**

- `web_fetch` is fetched by DeepSeek's servers, not the laptop; the URL guard is defense in depth for a future local fetch backend.
- The logical PRD entity relationship diagram is unchanged; only the physical `tool_calls` table gains columns.
- The AI SDK version remains 5.0.285; the protocol version is stable and the step and tool parts used here exist in that line.

## Alternatives considered

**A hand-written `while` loop instead of LangGraph.** For: less code and no dependency. Against: ADR-0008 makes LangGraph the single orchestration runtime, and a second control-flow implementation would be thrown away when the graph lands.

**LangChain `create_agent` or the deprecated `create_react_agent`.** For: the fastest standard ReAct loop. Against: opaque control flow and hidden budgets, which ADR-0008 rejected; the project needs named domain nodes and a visible work chain.

**`ToolNode` from `langgraph-prebuilt`.** For: the framework's standard tool executor. Against: it expects LangChain message and tool objects, while the project's adapter and tool registry are plain OpenAI-style dicts; a small custom tools node keeps the adapter boundary intact.

**MCP for the tool protocol.** For: the current standard for third-party tools. Against: a single-process closed tool set does not need a protocol, and ADR-0009 already defines the safety boundary.

**Provider-hosted code execution or citations.** For: less project code. Against: DeepSeek and MiMo do not document a hosted Python or citations tool for these models; the project's citations must point at its own course pages.

**Pre-injecting retrieval into the prompt instead of a retrieval tool.** For: fewer model calls and predictable latency. Against: the lead requires the agent to choose tools and the work chain to show the action; the tool path also leaves the document-scoped injection free for VT-04.

**No web tools until the corpus pipeline is complete.** For: smaller security and cost surface. Against: the lead requires the DeepSeek Search and Fetch integration in this slice.

## Follow-up

- VT-05: structured citations, deterministic span verifier, one repair round, abstention, evidence panel producer.
- VT-02: persist prompt and completion tokens, allow the interrupted-stream null case, and enforce the context budget.
- VT-04: conversation-document relation and document content injection, replacing the `document_context` note.
- VT-12: SQLite checkpointer, interrupt for user supplied code, and the `tacc/exec` practice path.
- ADR-0008: TACC LangGraph import spike and the in-memory fallback decision.
- Optional: a safe `calculate` tool with an AST whitelist, discussed on 2026-11-06, if the course questions need deterministic arithmetic.

## References

- Orchestration decision: [ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)
- Tool boundary: [ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md)
- Same-model retries: [ADR-0006](0006-same-model-retries-without-cross-model-fallback.md)
- Industry check: [2026-11-06 agent loop check](../research/2026-11-06-agent-loop-industry-check.md)
- DeepSeek Chat Completions: https://api-docs.deepseek.com/api/create-chat-completion
- DeepSeek Search and Fetch: https://api-docs.deepseek.com/guides/search
- AI SDK UI message stream protocol: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- PRD requirements: [../prd.md](../prd.md) FR-B2, FR-B9, FR-H1, FR-H3
- Backlog items: [../todo.md](../todo.md) VT-06, VT-07, VT-11, VT-21
