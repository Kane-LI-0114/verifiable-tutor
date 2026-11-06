# Verifiable AI Tutoring on TACC

*A course-grounded agent with evidence-checked answers, executable practice labs, and enforced course policy*

Project repository for CSIT6000V Advanced AI Computing and Systems (Fall 2026) by LI Jinchuan, TIAN Yujia, and XIE Yifeng: a course-grounded tutoring agent served from the developer laptop, with TACC as a required model-serving backend reached through job submission.

## Status

**Technology selected; model layer, Qwen knowledge-base round trip, and the first FastAPI backend surface implemented; PRD v0.10 drafted.** The substantive content is the course project proposal v1 (submitted), the v2 draft, and the current v3, the product requirements in [docs/prd.md](docs/prd.md), the domain vocabulary in [GLOSSARY.md](GLOSSARY.md), the technology selection record, fourteen ADRs (including the local offline Swagger UI, the persisted conversation turn metadata, the FastAPI backend structure and sessions, LangGraph orchestration, local Langfuse tracing, typed agent tools, and the required TACC model-serving backend with the knowledge base), the local tracing and email runbooks, the knowledge-base schema, configuration and local driver, the Qwen knowledge-base job under `tacc/serve/` with its chunk, request and validation helpers, and the model layer: configuration loading, the unified DeepSeek and MiMo adapter, its pytest suite, and a live smoke script. The Qwen knowledge-base round trip is verified on TACC (job 28067, 2026-11-02: 8 of 8 records valid). The first backend surface is implemented: the FastAPI app factory with health; accounts with scrypt hashing, email verification, password reset, and server-side cookie sessions; streamed chat with the AI SDK UI message stream and JSONL session traces; conversation history with persisted turn metadata (work steps, thinking, model profile, citations, tool calls); session replay; voice transcription and speech; knowledge cards and the Qwen build lifecycle; corpus page images; the practice-run scaffold; and the `tests/api/` suite. A committed offline Swagger UI bundle under [docs/api/](docs/api/) documents the API and is served at `/docs` and `/api-docs/`. The physical SQLite schema the backend creates is documented in the generated [docs/physical-data-model.md](docs/physical-data-model.md), kept separate from the logical ER model in the PRD. Hybrid retrieval over the local chunk store exists as a retriever and a `GET /api/knowledge/retrieve` entry point; the disclosure gate, the LangGraph runtime, the TACC OCR and index jobs' production wiring, chunk injection into the chat prompt, citation persistence, benchmark data, and the evaluation report do not exist yet. The React UI is wired live for authentication, the server-side session, conversation history, streamed chat, and replay, with an offline preview demo selectable with `?preview=1` or a `VITE_PREVIEW=1` build ([docs/ui-structure.md](docs/ui-structure.md)). Citations, practice execution, the knowledge-card and build pages, the deadline registry, and voice still use preview structures; the knowledge-base browser and the document preview are wired live. Everything else described below as behavior is planned; planned directories appear in the layout table as `placeholder (.gitkeep)` or `planned`. Multi-course deployment is out of scope for this deliverable and is recorded as future development in the PRD.

## What it is

A tutoring agent for one course whose outputs are checkable in three ways: text claims against cited page spans, code artifacts against executable tests, and disclosure against a dated policy. The scope is deliberately narrow: this course's own materials, assignments, and deadlines. The full argument, including motivation and design rationale, is in [proposal/proposal_v3.md](proposal/proposal_v3.md) (current; the submitted v1 is [proposal/proposal.md](proposal/proposal.md) and v2 is a previous draft); this README is the entry point, not a second proposal.

## Use cases

Students can:
- Ask course questions and receive answers that cite the exact page and quoted span.
- Ask by voice: record in the composer for transcription, or attach an audio file for MiMo 2.6 to analyze; play assistant answers as speech.
- Request a review outline or self-test questions on a topic; answer them and receive graded feedback with citations.
- Practise with a generated exercise at the scale and environment of the corresponding assignment, receiving a reference solution, tests, and a stepwise explanation; code answers run as TACC jobs.
- Submit their own solution and receive line-anchored teaching.
- Browse the course knowledge base built by Qwen on TACC; the agent uses the cards for review outlines and self-tests.

Instructors and TAs can:
- Maintain the deadline registry that drives the disclosure policy.
- Trigger knowledge-base builds and watch the TACC Qwen job from the UI.

## Disclosure policy

A five-state policy decides what the agent may reveal. The states are pre-release, active, extension window, post-deadline, and unknown; the gate that enforces them is planned, not implemented.

| Policy state | What the agent does |
|---|---|
| Pre-release, active, extension window | Refuses complete homework solutions and offers hints. Explains a user-provided solution only at the level provided and never fills in missing parts. |
| Post-deadline | Replaces refusal with full teaching plus a verified solution. |
| Unknown | Abstains rather than guesses; insufficient evidence also leads to abstention. |

The gate is code, not a prompt: a versioned registry of release and due dates with extensions, an intent classifier, and a log of every decision. The proposal covers the policy in [section 2](proposal/proposal_v3.md#2-task-definition-and-outputs) and [section 3](proposal/proposal_v3.md#3-proposed-system).

## Architecture

The planned system has four moving parts: a React browser UI served by the agent backend, the local FastAPI backend and its stores, a model-client abstraction over external OpenAI-compatible APIs (DeepSeek primary, Xiaomi MiMo selectable, with no automatic cross-model fallback), and a required TACC model-serving path. TACC runs two submitted model jobs: the BGE-M3 index job and the Qwen knowledge-base enrichment job. The Qwen job reads course chunks and a request from `USERDIR`, writes cited knowledge cards as JSONL, and exits; the local backend polls, downloads, validates, and stores them. TACC is reached only through job submission, with no SSH forwarding or inbound service ([ADR-0011](docs/adr/0011-tacc-as-required-model-serving-backend.md)). The agent workflow is a LangGraph `StateGraph` ([ADR-0008](docs/adr/0008-langgraph-as-agent-orchestration-runtime.md)), and local development traces model calls and graph steps into a self-hosted Langfuse instance ([ADR-0007](docs/adr/0007-langfuse-for-local-model-call-tracing.md), [docs/langfuse-local.md](docs/langfuse-local.md)). The retrieval index is built on TACC with BGE-M3, and query embedding runs on the laptop ([ADR-0004](docs/adr/0004-hybrid-retrieval-with-bge-m3.md)). The project environment is a pinned layer installed into the user workspace; the platform does not support custom images ([ADR-0001](docs/adr/0001-pinned-python-environment-without-docker.md)).

![System containers and components](proposal/figs/fig2_components_v3.png)

The Qwen knowledge-base job loads Qwen3.8-27B-AWQ-INT4 with vLLM at TP=2 and 32K context inside one submitted job per document shard and exits; no endpoint is exposed. Interactive text generation uses external APIs configured in `config/models.yaml` with keys in `.env` ([ADR-0005](docs/adr/0005-external-model-apis-as-primary.md)); Qwen is the required offline text-processing backend ([ADR-0011](docs/adr/0011-tacc-as-required-model-serving-backend.md)). The figure source is [proposal/figs/fig2_components_v3.dot](proposal/figs/fig2_components_v3.dot).

The planned subsystems inside the backend (the agent loop and model layer are implemented; the rest are planned):
- Agent loop (implemented 2026-11-06): a two-node LangGraph graph calls the model, executes a closed typed tool set (course search, page reading, DeepSeek search, DeepSeek fetch), returns the results to the model, and streams step, tool, text, and reasoning frames; tool calls persist in schema version 3 ([ADR-0016](docs/adr/0016-minimal-agent-loop-and-typed-tools.md)).
- Accounts: email and password sign-in restricted to course student domains, with a verification code, password reset, scrypt hashing, and server-side sessions; a student and an instructor role. The requirements are in [docs/prd.md](docs/prd.md) and the QQ Mail procedure in [docs/email-local.md](docs/email-local.md).
- Evidence: a TACC OCR job parses PDF files, one file per request, into page records with page numbers, block boxes, reading order, and page images ([ADR-0002](docs/adr/0002-ocr-on-tacc-with-paddleocr-vl.md), [docs/corpus-schema.md](docs/corpus-schema.md)); `scripts/tacc/parse_pdf.py` runs the whole local-to-TACC round trip and returns per-page JSONL plus one document markdown; hybrid retrieval fuses SQLite FTS5 BM25 with BGE-M3 dense embeddings and an optional reranker ([ADR-0004](docs/adr/0004-hybrid-retrieval-with-bge-m3.md)); a deterministic span verifier requires every quoted span to occur on its cited page, with one repair round or abstention.
- Practice lab and self-test: generated questions in the types the student asks for or the agent chooses, with cited reference answers; reference tests and student code answers execute as TACC jobs, and the agent grades the answers with citations. The first pack is MPI/GEMM with the same toolchain, Makefile, public datasets, and an sdk-test-style harness; a generated reference solution is accepted only after it compiles and passes the pack's tests.
- Knowledge base: a TACC Qwen job builds cited knowledge cards for course chunks; the backend polls the job, downloads and validates the records, and stores them locally for browsing, review outlines, and self-tests ([ADR-0011](docs/adr/0011-tacc-as-required-model-serving-backend.md), [docs/knowledge-schema.md](docs/knowledge-schema.md)).
- Policy gate: the code-level gate described above, plus the versioned deadline registry it reads.
- Teaching explainer: cites page spans, code lines, and test outcomes, and never invents missing content before the deadline.
- Model client and trace logger: external OpenAI-compatible APIs are primary for interactive text (DeepSeek, and Xiaomi MiMo when the user or config selects it, including audio). A failed call retries the selected model and then shows a timeout or unavailable message; it never switches models, configured in `config/models.yaml` with keys in `.env`; Qwen on TACC is the required offline knowledge-base backend, not a chat provider; every call is labelled and cached; audio-file input is supported when a MiMo 2.6 model is selected, the composer microphone uses MiMo ASR, and assistant text can be spoken with MiMo TTS ([model-providers.md](docs/model-providers.md)); traces, tests, and results follow the required execution path from task to visible result ([ADR-0005](docs/adr/0005-external-model-apis-as-primary.md)).

The browser UI is a React single-page application with shadcn and AI Elements components, served as static assets by the backend on one origin. The page structure, routes, component map, and preview fixtures are in [docs/ui-structure.md](docs/ui-structure.md); the preview build makes no API request. Streaming uses the AI SDK UI message stream protocol, so the same frontend path serves live and replay sessions ([ADR-0003](docs/adr/0003-react-spa-with-ai-elements.md)). The job topology, batch windows, and demo modes are in [docs/tech-selection.md](docs/tech-selection.md#jobs-and-demo-modes).

## Repository layout

All paths are repository-relative. Planned roles are statements of intent, not descriptions of implemented behavior.

| Path | Intended role | State |
|---|---|---|
| `src/verifiable_tutor/auth/` | Accounts, authentication, sessions, and roles | present: accounts, sessions, email seam, seeding |
| `src/verifiable_tutor/api/` | FastAPI application, routers, dependencies, and the AI SDK UI message stream adapter; serves the API and the built UI on one origin | present: factory, routers, chat and replay services, stream encoder |
| `src/verifiable_tutor/policy/` | Code-level disclosure gate and deadline registry | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/orchestrator/` | Request routing and context budget | present: two-node LangGraph loop, typed tool registry, course and web tools |
| `src/verifiable_tutor/evidence/` | Hybrid retrieval (query plan, FTS5 and dense arms, reciprocal rank fusion) and the deterministic span verifier | present: retrieval; verifier pending |
| `src/verifiable_tutor/practice/` | Practice pack generation and executable tests | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/teaching/` | Line-anchored explanations | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/eval/` | Evaluation harness | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/corpus/` | Page records, the page-first chunker, and the local knowledge store | present: chunker, store, pages |
| `src/verifiable_tutor/knowledge/` | Knowledge-base build orchestration, record validation, local storage, and build state; present: chunk, request and schema validation helpers, card reader, and build lifecycle | present: helpers, cards, builds |
| `src/verifiable_tutor/llm/` | Model configuration loader, unified provider adapter, and file-backed response cache; replay and mock backends pending | present: config, adapter, cache, search and fetch used by the agent tools |
| `src/verifiable_tutor/prompts/` | Model prompt texts in one editable home: the chat system prompt and the knowledge-base job template, loaded by the code that sends them | present: chat and kb prompts |
| `src/verifiable_tutor/ui/web/` | React UI source: routes, layout, page components, preview fixtures, and Vitest tests; built assets are written to the ignored `src/verifiable_tutor/ui/static/` | present: live API wiring and preview build |
| `tacc/serve/` | Required Qwen knowledge-base job: one submitted GPU job per document shard, records written to `USERDIR` | present: job, worker, prompt |
| `tacc/env-spike/` | Committed CPU spike: environment bootstrap, FTS5, and platform checks | present: spike job |
| `tacc/ocr-smoke/` | Committed GPU spike: PaddleOCR-VL smoke on representative pages | present: spike job |
| `tacc/pdf-parse/` | Committed GPU job: parses one complete PDF file end to end (enumerate, render, layout, recognition, document markdown) | present: demo path spike |
| `tacc/ocr/` | TACC GPU job for page rendering, layout, and OCR; batch manifest, private jobhome, one images archive | present: batch job |
| `tacc/index/` | TACC GPU job for BGE-M3 chunk embeddings (vectors, row map, summary) | present: index job |
| `tacc/exec/` | TACC CPU job that runs reference tests and self-test code answers | planned (not created yet) |
| `tacc/client/` | TACC CPU job for the offline evaluation harness | placeholder (`.gitkeep`) |
| `benchmarks/questions/`, `benchmarks/policy_scenarios/`, `benchmarks/results/` | Course questions, policy scenarios, recorded results | placeholder (`.gitkeep`) |
| `benchmarks/self_test/` | Self-test generation and grading benchmark data for RQ2 | planned (not created yet) |
| `data/corpus/`, `data/index/`, `data/caches/`, `data/kb/` | OCR output and page images, dense plus BM25 index, cached embeddings and retrieval snapshots, knowledge-base records and build state | placeholder (`data/kb/` holds verified local records; all data contents are gitignored) |
| `config/` | Runtime configuration: `models.yaml` owns provider endpoints, model ids, roles, request parameters, cache, and embedding settings; `knowledge.yaml` owns Qwen job resources, shard size, prompt version, paths, and polling; `app.yaml` owns the allowed registration domains, cookie flags, local data paths, and replay speed | present: model, knowledge, and app config |
| `scripts/` | Utility scripts: TACC bootstrap, submit helper, shared OCR stage helpers, the local PDF parse request interface, the local knowledge-base driver, the live model smoke, the API documentation build and vendor scripts, and the physical data model build script | present: scripts |
| `tests/` | Test suites under `tests/llm/` (configuration, chat, streaming, transcription, search, fetch), `tests/knowledge/` (chunks, request, schema), `tests/tacc/` (Qwen job worker, driver validation), `tests/api/` (HTTP contracts, accounts, chat, replay, voice, knowledge, corpus, SPA deep links), `tests/storage/` (schema upgrade, turn metadata), and `tests/docs/` (generated data model drift); the UI tests live inside the Vite project at `src/verifiable_tutor/ui/web/tests/` | present: tests |
| `pyproject.toml`, `uv.lock` | Python packaging, dependencies, pytest configuration, and locked local environment | present: packaging |
| `start.sh` | One-command local start: install UI dependencies when needed, build the SPA, and run the backend on one origin; flags for the Vite dev server, skipping the build, and the backend port | present: start script |
| `examples/` | Usage examples | placeholder (`.gitkeep`) |
| `docs/figures/` | PRD diagram sources and renders (use case, containers, sequence examples, ER), the generated physical schema diagram, and future report figures | present: PRD diagrams and the physical schema diagram |
| `docs/prd.md` | Product requirements, scope, acceptance criteria, and milestones | present: PRD |
| `docs/todo.md` | Ordered backlog, priorities, and item state, with the lead directives of 2026-11-06 | present: backlog |
| `docs/research/` | Dated research notes that check a plan against first-party sources; evidence, not a source of truth | present: 2026-11-06 agent loop check |
| `GLOSSARY.md` | Domain vocabulary used across the docs and code | present: glossary |
| `docs/tech-selection.md`, `docs/adr/` | Technology decisions and the ADRs that argue them | present: decisions |
| `docs/fastapi-reference.md` | FastAPI conventions for the local backend, distilled from the official documentation, for agents writing backend code | present: reference |
| `docs/api/` | Committed offline Swagger UI API documentation: deterministic `openapi.json`, generated `index.html`, pinned vendored Swagger UI assets, and regeneration instructions | present: API docs bundle |
| `docs/physical-data-model.md` | Generated physical SQLite data model: tables, columns, types, keys, checks, indexes, and the versioned migration, distinct from the logical PRD ER model | present: generated data model |
| `docs/ui-structure.md` | Browser UI page structure: routes, layout regions, component map, preview states, data coverage, and TDD seams | present: UI structure |
| `docs/corpus-schema.md` | Field-level contract for page, block, document and chunk records | present: schema |
| `docs/knowledge-schema.md` | Request, progress, and record contracts for the knowledge-base build | present: schema |
| `docs/paddleocr-vl-api.md` | PaddleOCR-VL request and response construction across the local, serving, and hosted paths | present: API notes |
| `docs/langfuse-local.md` | Local development tracing runbook | present: runbook |
| `docs/email-local.md` | Registration and reset email runbook | present: runbook |
| `docs/tacc-notes.md` | Platform constraints, budgets, and mechanics | present: notes |
| `proposal/` | Proposal sources: v1 `proposal.md`, v2 `proposal_v2.md`, and v3 `proposal_v3.md`, `build_proposal.py`, figure `.dot` sources, rendered PDFs, DOCX files, and v3 previews | present: proposal sources |

## Evaluation plan

All evaluation work is planned and the repository contains no results. The project is task-oriented (the course brief's task learning and adaptation direction): it quantifies tutoring-task performance against baselines, and reports efficiency as a secondary metric in RQ4. Four research questions, detailed in [proposal section 4](proposal/proposal_v3.md#4-evaluation-plan):

- RQ1 evidence fidelity: citation span accuracy (deterministic) and faithfulness (human-checked support rate).
- RQ2 practice and self-test verifiability: the share of generated questions whose reference answer compiles and passes course-style tests, environment alignment, cost per question, and grading consistency on a small constructed sample.
- RQ3 disclosure correctness: behavior across the five policy states, including a deadline extension, and an adversarial set (false "deadline passed" claims, TA impersonation, role-play, pasted "official" solutions) against a prompt-only baseline.
- RQ4 cost: end-to-end latency, model calls per request, TACC queue and cold-start time for the knowledge-base job, and a retrieval ablation over BM25, dense, and hybrid variants.

The benchmark is planned to hold fifty course questions, ten policy scenarios, one MPI/GEMM practice pack, and a shared self-test grading set, with later-released sessions held out; runs use temperature 0, cached retrieval snapshots and responses, and an injected clock. The required TACC workflow is reported separately: one knowledge-base build runs end to end, and its job id, queue, cold-start, build time, coverage, and schema validity go into the report.

## Roadmap

The four one-week workstreams from proposal v3 Table 1 (planned):

| Workstream | W1 | W2 | W3 | W4 |
|---|---|---|---|---|
| Corpus and OCR pipeline | X | | | |
| Hybrid index and retrieval | X | X | | |
| Span verifier | | X | | |
| Policy engine and registry | | X | X | |
| Practice pack and tests | | | X | |
| Explainer | | | X | |
| UI and replay mode | | | X | X |
| Evaluation, report, demo | | | | X |

Deliverables: the code repository, the evaluation report, the tested demo, and the final presentation.

Multi-course support is out of scope for this deliverable and is recorded as future development in [docs/prd.md](docs/prd.md#future-development).

## Documentation

- [proposal/proposal_v3.md](proposal/proposal_v3.md): readable Markdown text of the current proposal, generated by `proposal/build_proposal.py --version 3`.
- [proposal/proposal_v2.md](proposal/proposal_v2.md): Markdown text of the previous draft, kept for history.
- [proposal/proposal.md](proposal/proposal.md): Markdown text of the submitted v1 proposal, kept frozen.
- [docs/prd.md](docs/prd.md): product requirements, scope, acceptance criteria, and milestones.
- [GLOSSARY.md](GLOSSARY.md): the project's domain vocabulary.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.pdf): the two-page proposal prepared for submission on 2026-11-01, exported from the v3 DOCX with LibreOffice.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.docx): editable v3 DOCX.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.pdf): previous draft PDF.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.docx): previous draft DOCX.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.pdf): the submitted v1 PDF, kept frozen.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx): the submitted v1 DOCX, kept frozen.
- [docs/figures/](docs/figures/): PRD diagram sources (`.dot`) and rendered PNGs: use cases, containers, sequence examples including the knowledge-base build, and the entity relationship model.
- [docs/tech-selection.md](docs/tech-selection.md): technology choices, job topology, demo modes, and the week-one verification spikes.
- [docs/fastapi-reference.md](docs/fastapi-reference.md): agent-facing FastAPI reference for the local backend: the planned layout, implementation rules, streaming, sessions, testing, and the official documentation behind each rule.
- [docs/api/](docs/api/): committed offline Swagger UI for the local API: deterministic OpenAPI schema, generated page with pinned vendored assets, and the regeneration and upgrade procedure.
- [docs/physical-data-model.md](docs/physical-data-model.md): the generated physical SQLite data model with its Graphviz diagram, guarded against drift by `tests/docs/`, and explicitly separate from the logical PRD ER model.
- [docs/corpus-schema.md](docs/corpus-schema.md): page, block, document and chunk record fields produced by the OCR pipeline.
- [docs/knowledge-schema.md](docs/knowledge-schema.md): request, progress, and knowledge-record contracts for the Qwen knowledge-base build.
- [docs/benchmark-protocol.md](docs/benchmark-protocol.md): the RQ2 self-test generation and grading benchmark: baseline, shared set, simulated answers, ground truth, and metrics.
- [docs/paddleocr-vl-api.md](docs/paddleocr-vl-api.md): PaddleOCR-VL request and response construction for the local pipeline, the recognition service, the self-hosted parsing service, and the hosted official API.
- [docs/model-providers.md](docs/model-providers.md): agent-facing API notes for DeepSeek and Xiaomi MiMo, model switching, image and audio input, thinking control, web search, JSON output, and tool calling.
- [docs/adr/](docs/adr/): decision records for the environment, the OCR pipeline, the UI stack, the retrieval model, the model backend, retry behaviour, local model-call tracing, the orchestration runtime, typed agent tools, the local backend, the required TACC model-serving backend with the knowledge base, the FastAPI backend structure and sessions, the local offline Swagger UI, and the persisted conversation turn metadata with its generated physical data model.
- [docs/langfuse-local.md](docs/langfuse-local.md): runbook for the optional local Langfuse instance used for development tracing.
- [docs/email-local.md](docs/email-local.md): runbook for registration and password reset email over QQ Mail SMTP.
- [config/models.yaml](config/models.yaml): provider endpoints, model ids, role routing, request parameters, and embedding settings. [config/knowledge.yaml](config/knowledge.yaml): Qwen knowledge-base job resources, shard size, prompt version, paths, and polling. Secrets stay in the ignored `.env`; [.env.example](.env.example) is the committed template.
- [docs/tacc-notes.md](docs/tacc-notes.md): platform constraints, budgets, and measured platform mechanics.
- [AGENTS.md](AGENTS.md): agent and contributor guide covering sources of truth, commands, and conventions.

## Team

- LI Jinchuan (21188271)
- TIAN Yujia (21201619)
- XIE Yifeng (21322152)

CSIT6000V Advanced AI Computing and Systems, Fall 2026. Instructor: Prof. Kai Chen. Proposal v1 dated October 27, 2026; v2 draft dated October 30, 2026; v3 dated November 1, 2026, for submission on 2026-11-01. Repository: https://github.com/Kane-LI-0114/verifiable-tutor
