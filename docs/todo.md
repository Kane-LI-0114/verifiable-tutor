# Backlog: verifiable-tutor

| | |
|---|---|
| **Status** | Living document, updated as work lands |
| **Date** | 2026-11-06 |
| **Owner** | LI Jinchuan |
| **Scope** | The ordered backlog, priorities, and item state; the lead directives that set them |
| **Companions** | [prd.md](prd.md) owns requirements and acceptance; [adr/](adr/) owns decisions; [tech-selection.md](tech-selection.md) owns the build plan; [AGENTS.md](../AGENTS.md) owns the agent rules |

This file is the single home for what is not built yet, in what order, and in what state. It consolidates the 2026-11-06 capability audit against the five agent components (perception, planning, action, reflection, memory), the deferred list of [ADR-0015](adr/0015-local-knowledge-store-and-chunking.md), and the lead directives recorded below. The PRD owns requirement text; this file owns order and state. Link to a requirement instead of restating it.

## How this file is maintained

- IDs are stable. A landed item keeps its ID and moves to the Done table with the commit and the test that proves it. An ID is never reused.
- Update the item's Status in the same commit as the change, whether the change is code, a decision, or a test.
- New items take the next free ID and name a source: a PRD requirement, an ADR deferred item, or a lead directive.
- The order is the dependency order. Do not move an item ahead of a dependency without recording the reason in the change log.
- Review the Now table at the start of each work session. The Status column is the only state marker.
- A design question that blocks an item is settled in an ADR or a design note first, then implemented. The open questions are kept in [Design notes](#design-notes).
- This file supersedes the gap summary in the 2026-11-06 audit discussion. [AGENTS.md](../AGENTS.md) keeps the constraints on how work is done and points here for order and state.

## Evidence

The loop plan was checked against first-party sources on 2026-11-06. The verdicts, project fit, ten adjustments, and unverified items are in [docs/research/2026-11-06-agent-loop-industry-check.md](research/2026-11-06-agent-loop-industry-check.md). The adjustments that change scope are folded into VT-02, VT-05, VT-06, VT-07, VT-11, and VT-21.

## Lead directives

| ID | Date | Directive |
|---|---|---|
| D1 | 2026-11-06 | Intent routing and token usage accounting are higher priority than the rest of the backlog. |
| D2 | 2026-11-06 | Document context must not be a system message in the request body. A chat request carries the conversation id, and the conversation is related to a document id; a request may also carry a document id. The backend resolves the conversation to document relation, finds the document content by id, and injects it into the user part of the prompt. This is a proposal to refine, not a settled design. |
| D3 | 2026-11-06 | The chat composer must accept image files as attachments and must accept an image pasted directly into the text input. |

D2 replaces the current `document_context` system note, which names the document and page but carries no page text ([chat_document_context.md](../src/verifiable_tutor/prompts/chat_document_context.md), [chat.py](../src/verifiable_tutor/api/chat.py)). D3 extends a composer whose audio attachment and microphone controls are disabled in live mode ([composer.tsx](../src/verifiable_tutor/ui/web/src/components/chat/composer.tsx)).

## Where the audit stands

State on 2026-11-06, before the items below. The audit read the code, not the design documents.

| Component | State | Items |
|---|---|---|
| Perception | Text only. The open document is a doc id and page number, no page text. Hybrid retrieval exists but no prompt receives a chunk. No image ingress in chat; ASR is a separate endpoint and the composer microphone is disabled. | VT-01, VT-04, VT-09, VT-13 |
| Planning | One model call. No graph, no task decomposition, no intent or disclosure decision, no budget. | VT-01, VT-03, VT-07, VT-08 |
| Action | The adapter can send tools and parse tool calls, but no tool is defined and nothing dispatches one. No execution runner, no `tacc/exec`. | VT-06, VT-12 |
| Reflection | No online verification, repair, or abstention. Offline knowledge-base repair and citation rejection exist and stay offline. | VT-05, VT-16 |
| Memory | Short term only: a fixed 12-message window, persisted in SQLite. No token accounting, no compaction, no long-term learner state. | VT-02, VT-03, VT-22 |
| Evidence | Retrieval library and endpoint only. Citations, span verification, and the evidence panel data have no producer. | VT-04, VT-05 |
| Knowledge base | Local store, OCR, index, and Qwen job are implemented. No upload chain, no chunking evaluation. | VT-10, VT-14 |

## Backlog

Status values are Open, In progress, Blocked, and Done.

### Minimal vertical slice

The first runnable agent loop is the smallest set that closes perceive, decide, act, observe, and answer: VT-06 as one retrieval tool, a reduced VT-07 loop with a step cap, and the tool frame from VT-11. It does not need VT-04 first, because the tool returns chunks directly; VT-04 remains the document-scoped context path, and VT-05 can land after the loop runs. The slice landed on 2026-11-06 (ADR-0016): four tools, a two-node LangGraph loop, streamed tool frames, persisted tool calls, and live UI rendering; the remaining parts of VT-06, VT-07, and VT-11 stay open.

### Now (P0)

| ID | Item | Source | Priority | Status | Depends on | Note |
|---|---|---|---|---|---|---|
| VT-01 | Route each chat turn to one of the five intent classes, rule based first and model assisted second, and log the rule id with the decision. | FR-C3 ([5.3](prd.md#53-disclosure-policy)), D1 | P0 | Open | none | Rules in configuration, not code. Fail open to `other`. The trace records the class, the rule id, and whether the model was consulted. |
| VT-02 | Account for model tokens per call and per turn: persist prompt, completion, and total tokens with the provider, model, and role, and return them from the history API. | D1, NFR-6 ([6](prd.md#6-non-functional-requirements)), RQ4 | P0 | Open | none | The adapter already parses usage and drops it. This is the measurement layer the budget in VT-03 and the cost report need. Usage arrives on an empty-choices chunk on OpenAI and on the last content chunk on DeepSeek, so accept it on any chunk and allow a null for an interrupted stream; MiMo streaming usage is unverified. |
| VT-03 | Replace the fixed 12-message window with a token budget: count system, history, injected context, and answer reserve; compact or truncate when over budget; enforce the per-request model call and wall-clock caps. | FR-B9 ([5.2](prd.md#52-conversation-and-evidence)), tech-selection budget | P0 | Open | VT-02 | The plan is at most 6 model calls and 24K context tokens of the 32K window. Compaction strategy is chosen here: summary, drop oldest, or both. Usage is recorded per step. |
| VT-04 | Assemble the context of a chat turn from the conversation, its document relation, and retrieval: backend resolves the document, reads its content, retrieves top-k chunks, and injects them into the user part of the prompt; emits a `retrieve` step and persists the hits. | D2, [ADR-0015](adr/0015-local-knowledge-store-and-chunking.md) item 3, FR-B2, FR-B9 | P0 | Open | VT-03 | Settle the [D2 open questions](#d2-document-context-and-the-conversation-document-relation) and record the decision before coding. The current `document_context` request field and system note are replaced. |
| VT-05 | Turn retrieved chunks into stored citations: model returns doc id, page, and quoted span; the deterministic verifier checks the span against the page text; one repair round; otherwise abstain; `verified_at` is set only on a pass; the evidence panel consumes the page and boxes. | [ADR-0015](adr/0015-local-knowledge-store-and-chunking.md) item 2, FR-B3, FR-B4, FR-B5, NFR-7 | P0 | Open | VT-04 | The `citations` table and history API exist and are empty. One repair round, then an abstention that names the missing evidence. Verify the span against the chunk text the model was shown (rebuilt from blocks), then the page text, and record the normalization; a passing span is necessary, not sufficient for grounding. |

### Next (P0)

| ID | Item | Source | Priority | Status | Depends on | Note |
|---|---|---|---|---|---|---|
| VT-06 | Add the typed tool layer: a closed, versioned tool set, argument schemas, a dispatcher, a tool stream frame, and persistence in `tool_calls`; the first tools are retrieve, read page, and verify span. | FR-H1, FR-H3 ([5.6](prd.md#56-execution-and-tools)), [ADR-0009](adr/0009-typed-agent-tools-instead-of-a-shell.md) | P0 | In progress | none | Landed 2026-11-06: the registry and four tools ship with schema version 4 ordered work-chain events and streamed tool frames. The `verify_span` tool is still pending. No generic shell. An unknown tool call is rejected and shown in the work chain. |
| VT-07 | Replace the single model call with the LangGraph `StateGraph`: understand, retrieve, verify, decide, generate, cite; SQLite checkpointer; per-request budgets enforced at node boundaries; streamed node events. | FR-B9, [ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md), tech-selection | P0 | In progress | VT-03, VT-06 | Landed 2026-11-06: the two-node agent and tools graph runs locally with project budgets and custom-mode streaming. The six-node topology, `RemainingSteps` routing, and the SQLite checkpointer remain. |
| VT-08 | Add the disclosure gate and the deadline registry: five policy states from a versioned `config/deadlines.yaml`, the five intent classes from VT-01, refusal and hints before the deadline, full teaching after it, decision log with rule id and clock, fail closed on a bad registry. | FR-C1 to FR-C8 ([5.3](prd.md#53-disclosure-policy)) | P0 | Open | VT-01, VT-07 | The clock is injected. The gate is code, not a prompt instruction. |
| VT-09 | Accept images in the chat composer: file attachment and paste into the text input, both producing an attachment chip; define storage, limits, provider capability checks, and how an answer marks that it used an attachment. | D3, FR-B6 ([5.2](prd.md#52-conversation-and-evidence)) | P0 | Open | none | Settle the [D3 open questions](#d3-image-attachment-and-paste) first. An attached image is not in the corpus, so citation behavior must be decided, not assumed. |
| VT-10 | Add the document upload chain: the browser posts a file, the backend stages it, submits OCR, and runs chunk, embed, store, and summarize exactly as the ingest driver does; folder and document states appear in the UI. | [ADR-0015](adr/0015-local-knowledge-store-and-chunking.md) item 1, FR-K1 ([5.8](prd.md#58-knowledge-base)) | P0 | Open | none | The `+` upload item stays disabled until the round trip is verified. |
| VT-11 | Produce the complete work chain: all six step names and tool events with command lines, exit codes, and truncated output; persist and stream them; the UI components already render them. | FR-B9, FR-H3 ([5.6](prd.md#56-execution-and-tools)) | P0 | In progress | VT-06, VT-07 | Landed 2026-11-06: `generate` and `retrieve` steps, `data-tool` frames, and `start-step` and `finish-step` are emitted and persisted. `understand`, `verify`, `decide`, and `cite` remain. |
| VT-12 | Add the restricted subprocess runner, the `tacc/exec` job, the practice-run route, and the confirmation interrupt for user supplied code. | FR-E4, FR-H2, FR-H4 ([5.4](prd.md#54-study-aids-practice-self-test-and-teaching), [5.6](prd.md#56-execution-and-tools)), NFR-5, NFR-11 | P0 | Open | VT-06 | The practice route is a 503 today. The runner seam tests are part of the item. |
| VT-13 | Wire voice into the composer and the transcript: microphone transcription into the input, audio attachment only when a MiMo model is selected, and TTS playback of assistant messages. | FR-G1, FR-G2, FR-G3 ([5.5](prd.md#55-voice-and-audio)) | P0 | Open | none | The ASR and TTS adapters exist. The chat request body needs an audio path or a transcript handoff, and the capability rule lives in the request, not only in the prompt. |
| VT-14 | Evaluate chunking strategies on the retrieval question set and keep the winner: fixed window, recursive, structure aware, and semantic, reporting page-hit@k and nDCG per strategy. | [ADR-0015](adr/0015-local-knowledge-store-and-chunking.md) item 4 | P0 | Open | VT-04, VT-05 | Chunking is last on purpose: the citation format and the injection budget decide what the retrieval unit should be. `chunker_version` forces a rebuild on a rule change. |

### Later (P1 and P2)

| ID | Item | Source | Priority | Status | Depends on | Note |
|---|---|---|---|---|---|---|
| VT-15 | Trace graph nodes and tool spans in local Langfuse, fail open, with `config/observability.yaml`. | FR-I2 ([5.7](prd.md#57-observability-evaluation-and-delivery)), [ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md) | P1 | Open | VT-07 | Local development only. JSONL stays the canonical trace. |
| VT-16 | Build the evaluation harness and the benchmark data: 50 course questions, 10 policy scenarios, one practice pack, cached runs, RQ2 and RQ4 exports, failure analysis. | FR-I3, FR-I4, FR-I5, FR-E8, [benchmark-protocol.md](benchmark-protocol.md) | P1 | Open | VT-05 | The benchmark protocol has not been run. The harness consumes the cache so a rerun needs no paid call. |
| VT-17 | Generate practice questions and reference answers in the five types, verify reference answers by compilation and tests, and grade student answers with citations. | FR-E1, FR-E2, FR-E3, FR-E5, FR-E6, FR-E7 ([5.4](prd.md#54-study-aids-practice-self-test-and-teaching)) | P1 | Open | VT-12, VT-16 | The practice lab and the self-test share one question record. |
| VT-18 | Add the line-anchored explainer for a submitted solution, respecting the disclosure gate. | FR-F1, FR-F2 ([5.4](prd.md#54-study-aids-practice-self-test-and-teaching)) | P1 | Open | VT-08 | Each claim points at a line that exists in the submitted file. |
| VT-19 | Produce a grounded review outline and self-test from knowledge-base records, with every displayed citation passing the span verifier. | FR-D1, FR-D2, FR-K3 ([5.4](prd.md#54-study-aids-practice-self-test-and-teaching), [5.8](prd.md#58-knowledge-base)) | P1 | Open | VT-05, VT-17 | The Qwen records exist and are browsable. Nothing consumes them in a prompt today. |
| VT-20 | Add the instructor deadline registry editor. | FR-A5, section 3 P1 ([3](prd.md#3-scope)) | P1 | Open | VT-08 | The registry itself is VT-08. |
| VT-21 | Add DeepSeek web search augmentation for questions the corpus cannot answer, with source display and the same abstention rule. | [3](prd.md#3-scope) P1, [adapter.py](../src/verifiable_tutor/llm/adapter.py) | P1 | In progress | VT-06 | Landed 2026-11-06: `web_search` and `web_fetch` are typed agent tools and pass the dual-model smoke. Source display and citation integration remain. |
| VT-22 | Add long-term learner state: what a user has asked, which pages and citations were used, and which topics are weak; expose it to the planner as context, with a data lifecycle rule. | 2026-11-06 audit, no PRD requirement yet | P2 | Open | VT-02, VT-05 | No requirement exists. Define the schema, the consent and deletion rule, and whether it crosses conversations before implementing. |
| VT-23 | Add response cache TTL, eviction, and usage-aware keys. | Known gap in [AGENTS.md](../AGENTS.md) | P2 | Open | VT-02 | Today the cache never expires and has no eviction. |
| VT-24 | Evaluate an optional reranker on the fused results. | [3](prd.md#3-scope) P2, [ADR-0004](adr/0004-hybrid-retrieval-with-bge-m3.md) | P2 | Open | VT-14 | Report the ablation; do not add the dependency before the evaluation asks for it. |

## Design notes

These notes hold the open questions that block an item. They are not decisions; each one is settled in an ADR or a design note and then removed or linked from the item.

### D2 document context and the conversation document relation

The current design puts a system message in the prompt that names the open document and page and says the page text is unavailable. D2 replaces it: the conversation carries the relation, the backend resolves the document, and the content enters the user turn.

- Cardinality: one document per conversation, one per turn, or many? Switching documents in the preview should not silently change what an earlier turn cited.
- Lifecycle: when the association is created, whether it clears when the preview closes, and what a turn sees when no document is open.
- Scope of injected content: the open page only, the page plus neighbors, or hybrid retrieval filtered by document id. This decides whether the document relation is a filter on retrieval or a separate context source.
- Placement and persistence: D2 puts the content in the user part of the prompt. Decide whether the assembled content is stored with the message, stored as a separate turn context row, or rebuilt at request time. Replay and the JSONL trace need the resolved content, but the database should not duplicate page text per turn.
- Budget: injected document and retrieval text counts against VT-03.
- Access control: the backend verifies the document id against the corpus and the caller's role, and rejects an unknown id with a clear error.
- UI: the transport sends the document id, not a rendered prompt fragment; the current `document_context` field is replaced.
- Candidate shape to evaluate: a nullable `document_id` on `conversations`, a per-turn `document_id` on `messages`, or a `conversation_documents` relation table. The choice depends on the cardinality answer.

### D3 image attachment and paste

- Meaning of an image-format document: a photo of a slide, a scanned page, or a multi-page image document. The OCR path and the model path differ.
- Ingestion path: send image blocks to the selected multimodal provider, OCR the image on TACC and treat the text as corpus, or both. An attached image is not in the corpus, so an answer cannot cite it with a page and span. Decide how the answer labels that input, and whether OCR ingestion is required before a citation is allowed.
- Storage: a file under the data directory with a metadata row, or a SQLite BLOB. Include per-user isolation, retention, and deletion with the conversation.
- Limits: accepted mime types, count per turn, bytes per file, and the error copy when a provider cannot take images.
- Paste: clipboard image becomes an attachment chip with a thumbnail and a remove action; the keyboard and accessibility path equals the file picker path.
- Trace and replay: JSONL records a reference and a hash, not the image bytes.
- Acceptance sketch: a png or jpeg added by picker or paste produces a chip, reaches the model on the next turn, and the answer and trace record which attachment was used.

### VT-01 intent routing

- Rule set lives in configuration with a version, and rules run before the model.
- The model is consulted only when the rules are inconclusive, and its answer is logged with the escalation reason.
- Fail open to `other` on any rule or model failure; the decision log records the failure.

## ADR-0015 mapping

| ADR-0015 deferred item | This backlog |
|---|---|
| 1. Upload chain | VT-10 |
| 2. Citation system | VT-05 |
| 3. Chunk injection and the agent tool | VT-04 for the injection, VT-06 for the tool |
| 4. Chunking strategy optimization | VT-14 |

## Done

Foundations that exist and are tested. They are listed so the backlog is not read as a description of the whole system.

| Area | What exists | Tests |
|---|---|---|
| Accounts and sessions | Registration, verification code, reset, server-side sessions, roles, seeding | `tests/api/`, `tests/storage/` |
| Chat transport | Streamed turn, persisted messages and steps, JSONL trace, replay, document note | `tests/api/test_chat_stream.py`, `tests/api/test_chat_document_context.py` |
| Model layer | Provider selection, thinking passthrough, same-model retries, response cache, ASR, TTS, search and fetch clients | `tests/llm/` |
| Retrieval | FTS5 lexical arm, BGE-M3 dense arm, reciprocal rank fusion, query rewrite, `GET /api/knowledge/retrieve` | `tests/evidence/`, `tests/api/test_knowledge_retrieval.py` |
| Corpus and knowledge base | OCR jobs, page-first chunking, local store, Qwen knowledge-base job, record validation, card browser | `tests/knowledge/`, `tests/tacc/`, `tests/corpus/` |
| UI | Page structure, live auth and chat, history, replay, knowledge browse, evidence panel shell, tool and citation renderers | Vitest suites under `src/verifiable_tutor/ui/web/tests/` |
| Agent loop and tools | Two-node LangGraph loop, closed typed tool set for course and web use, schema version 4 ordered work-chain events, streamed tool frames, live and stored UI rendering, dual-model smoke | `tests/orchestrator/`, `tests/api/test_chat_agent.py`, `tests/storage/test_tool_calls.py`, `chat-live.test.tsx` |

## Out of scope

- Multi-course support, recorded as future development in [prd.md](prd.md#future-development).
- A public deployment and hostile-user isolation. The demo has two to three trusted users ([NFR-11](prd.md#6-non-functional-requirements)).
- Strong sandboxing on TACC ([ADR-0009](adr/0009-typed-agent-tools-instead-of-a-shell.md)).
- P2 candidates that are not yet items: live practice generation, a CUDA and attention pack, the teaching-video voiceover pipeline, notifications.

## Change log

| Date | Change |
|---|---|
| 2026-11-06 | Created from the five-component gap audit and lead directives D1, D2, and D3. Imported the four ADR-0015 deferred items and mapped them to VT-10, VT-05, VT-04 with VT-06, and VT-14. |
| 2026-11-06 | Recorded the minimal vertical slice: VT-06 can start without VT-04 and VT-07 without VT-05, because the retrieval tool returns chunks directly. The two dependency cells were adjusted. |
| 2026-11-06 | Folded the industry check into VT-02, VT-05, VT-06, VT-07, VT-11, and VT-21, and added the Evidence section that links the check. |
| 2026-11-06 | Landed the minimal loop: VT-06, VT-07, and VT-11 move to In progress, VT-21 gets the web tools, and the Done table records the agent loop. Both DeepSeek Flash and MiMo Flash passed the live smoke. |
| 2026-11-06 | Adopted ordered work-chain events (ADR-0017): reasoning and tool calls persist in `message_events`, the UI renders them in order inside the expanded chain, and schema version moves to 4. |
| 2026-11-06 | Made `thinking.disable_for_tools` per provider (ADR-0018): DeepSeek keeps thinking with tools when `tool_choice` is auto, MiMo stays off by default, and the loop replays `reasoning_content`. |
| 2026-11-06 | Restricted the MiMo thinking control to Off and On; stored `low` or `max` selections normalize to On, and the API trace records the normalized level. |
| 2026-11-06 | Associated each work-chain event with its step (ADR-0019): schema v5 adds `message_events.step_id`, the UI groups events into one section per actual step, and a step with no events keeps its section. |
| 2026-11-06 | Grouped work-chain events by step id: a reasoning segment attaches to the tool-call step it precedes, and same-name rows with different ids render as separate sections. |
