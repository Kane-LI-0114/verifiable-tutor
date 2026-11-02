# Technology selection

Scope: implementation technology for this repository. It tracks proposal v3 (dated 2026-11-01); proposal v1 remains the submitted artifact and proposal v2 is a previous draft. Platform constraints are owned by [tacc-notes.md](tacc-notes.md); this document owns the choices, the operational plan, and the verification list. The architectural choices are argued in [`docs/adr/`](adr/), and the repository layout is owned by [README.md](../README.md#repository-layout).

Status: decided on 2026-10-28, updated on 2026-10-29 for the external model APIs, the retry policy, Langfuse tracing, and LangGraph, and updated on 2026-11-01 for the required TACC model-serving backend and knowledge base ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)), aligned with proposal v3 (dated 2026-11-01). The model layer, its tests, its live smoke script, and the first FastAPI backend surface are implemented, and the Qwen knowledge-base job and its file round trip are verified on TACC; retrieval, the disclosure gate, orchestration, practice execution, the UI, and the evaluation harness are planned. Spikes 1 to 3 ran on 2026-10-29, spike 10 ran on 2026-11-02, and spikes 4 to 9 are unrun. The first FastAPI backend surface was implemented on 2026-11-02 (health, accounts and sessions, chat streaming with the AI SDK stream and JSONL trace, replay, voice, knowledge cards and builds, corpus page images, and the practice-run scaffold) with `tests/api/`; its decisions are recorded in [ADR-0012](adr/0012-fastapi-backend-structure-and-sessions.md).

## Decisions at a glance

| Area | Decision | Why |
|---|---|---|
| Python runtime | 3.12 everywhere: 3.12.14 in the course public environment, 3.12.13 locally through uv | One version for both legs removes a whole class of skew |
| Dependency and environment strategy | Hash-pinned `requirements.txt` plus `uv.lock`, installed by an idempotent bootstrap into `$HOME`; the GPU stack stays on the read-only public environment; `Dockerfile` is for local development only | The platform has no custom-image support and a 1 GiB submit cap ([ADR-0001](adr/0001-pinned-python-environment-without-docker.md)) |
| Backend | FastAPI and uvicorn in one process, serving both the API and the built UI on one origin; server-sent events through `StreamingResponse`; run on the developer laptop | Both are pinned in the public environment; one origin keeps the local demo, the replay path, and the offline run on one port ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS 4, shadcn/ui, AI Elements, `@ai-sdk/react`, streamdown, KaTeX, Shiki | Mainstream chatbot stack with ready components for the timeline and citations ([ADR-0003](adr/0003-react-spa-with-ai-elements.md)) |
| Corpus and OCR | PaddleOCR-VL-1.6 on vLLM, PP-DocLayoutV2 layout on CPU, page images through pypdfium2, per-page JSONL with page numbers and block boxes, resumable one-hour jobs | Page numbers and block boxes are what the evidence requirement and citation panel need ([ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md)) |
| Retrieval | SQLite FTS5 BM25 plus BGE-M3 dense vectors, fused with reciprocal rank fusion; an English query variant feeds the BM25 arm for Chinese queries | Multilingual, no vector database, and the proposal's ablation arms are preserved ([ADR-0004](adr/0004-hybrid-retrieval-with-bge-m3.md)) |
| Embedding model | BGE-M3 primary; Qwen3-Embedding-0.6B fallback; Qwen3-Embedding-4B upgrade path | Fits the RTX 3090 and CPU query embedding, MIT licensed, strong cross-lingual retrieval |
| Model client | `openai` SDK against external OpenAI-compatible providers: DeepSeek `deepseek-flash` for chat, Xiaomi MiMo `mimo-v2.6-flash` and `mimo-v2.6-pro` when selected; temperature 0; replay and mock backends behind one interface. Qwen on TACC is a required offline knowledge-base backend, not a chat provider | External APIs remove the shared-Qwen queue and cold start; TACC model serving is required by the 2026-11-01 staff email ([ADR-0005](adr/0005-external-model-apis-as-primary.md), [ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) |
| Knowledge base | Qwen on TACC builds cited knowledge cards from course chunks; one submitted GPU job per document shard; the local backend polls, downloads, validates, and stores the records in `data/kb/` and SQLite | The required TACC model-serving demonstration and a product feature ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md), [knowledge-schema.md](knowledge-schema.md)) |
| Model failure handling | Retry the selected model up to `defaults.max_retries`; never switch models or providers automatically; after exhaustion return a timeout or unavailable message and let the user retry | Keeps each answer attributable to the model the user selected and makes failures explicit ([ADR-0006](adr/0006-same-model-retries-without-cross-model-fallback.md)) |
| Orchestration | LangGraph typed `StateGraph` as the single orchestration runtime: policy, retrieval, evidence verification, generation, citation checks, and teaching and practice flows are nodes; SQLite checkpointer per user and session; FastAPI hosts the graph with no LangGraph Platform | Explicit graph, persistence, streaming, and human in the loop come from the framework while tests stay at graph seams ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)) |
| Local tracing | Langfuse OSS v4 self-hosted with Docker Compose on the laptop, for local development only; JSONL stays canonical for replay and TACC evaluation | Model call and graph step provenance with local data, a framework-native LangGraph integration, and fail-open behavior; never installed on TACC ([ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md)) |
| Accounts and access | Email and password accounts restricted to course student domains, server-side cookie sessions signed with a secret from `.env`, scrypt password hashing, a student and an instructor role, and QQ Mail SMTP with an authorization code for registration codes and reset links | A course design needs a basic user system and no third-party identity provider; the detailed requirements are in [prd.md](prd.md), the QQ Mail procedure in [email-local.md](email-local.md) |
| Tool execution | The model calls typed LangGraph tools only; execution tools use one restricted subprocess runner (no shell interpolation, per-user scratch directory, environment allowlist without secrets, resource limits, timeout and process group kill); no generic shell | No strong sandbox is available on TACC, and typed tools keep every action auditable and visible in the work chain ([ADR-0009](adr/0009-typed-agent-tools-instead-of-a-shell.md)) |
| Voice input and output | Audio-file attachments are supported only when a MiMo model is selected; the selected tier handles the audio. The composer microphone uses MiMo `mimo-v2.5-asr`, and assistant text can be synthesized with the MiMo TTS family for playback and as a teaching-video voiceover candidate | DeepSeek has no audio; one provider covers both audio directions ([ADR-0005](adr/0005-external-model-apis-as-primary.md), [model-providers.md](model-providers.md)) |
| Policy gate | YAML deadline registry validated by pydantic, rule and embedding intent routing, injected clock, JSONL decision log, fail closed to abstention | Deterministic and resistant to prompt injection |
| Practice lab and self-test | Generated questions in the types the student asks for (single choice, multiple choice, true or false, short answer, code) or in a type the agent chooses; reference answers verified by the public MPI toolchain and tests in a TACC job, cached; the agent grades student answers, and code answers execute as TACC jobs under the team account | The self-test and the practice lab are one capability; reference verification keeps answers checkable, and the demo has two to three trusted users, so no hostile-user isolation is claimed ([ADR-0009](adr/0009-typed-agent-tools-instead-of-a-shell.md), [prd.md](prd.md)) |
| Storage | SQLite for metadata, FTS5, caches, knowledge cards, and build state; NumPy arrays for vectors; JSONL for traces, replay, and downloaded knowledge records | No external service, and everything is copyable between `USERDIR` and the laptop |
| Tests | pytest with the red and green loop, run inside the project environment on TACC | The framework decision that AGENTS.md left open |
| Evaluation | Benchmark JSONL, an evaluation harness that writes JSON, plots generated locally | matplotlib is absent from the public environment |
| Jobs and demo | The backend, UI, and stores run on the laptop; `tacc/ocr`, `tacc/index`, `tacc/exec`, and `tacc/client` are submitted jobs; `tacc/serve` is the required Qwen knowledge-base job, submitted from the UI and downloaded into the local knowledge base; TACC is a required model-serving backend with no SSH forwarding ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) | The one-hour cap, the 2026-11-01 TA requirement, and demo risk |

## Environment strategy

The full argument is in [ADR-0001](adr/0001-pinned-python-environment-without-docker.md); this section records the mechanics that implementers need.

### Two layers, no image

- GPU layer: the course public environment. vLLM 0.26.0, PyTorch 2.11.0+cu128, Transformers 5.10.4, Python 3.12.14, 199 packages total. It is read-only and must not be modified.
- Project layer: everything the project adds, pinned in `requirements.txt` with hashes and in `uv.lock`. The expected delta is `pypdfium2` for page rendering, `pytest` for tests, the PaddleOCR client plus `paddlepaddle` CPU wheel for the OCR job, and the LangGraph dependency group (`langgraph`, `langchain-core`, `langgraph-checkpoint-sqlite`) for the agent backend ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)). The Langfuse SDK is a local development extra only and is never installed on TACC ([ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md)). The public environment already provides FastAPI, uvicorn, pydantic, openai, httpx, NumPy, PyYAML, sse-starlette, and Pillow.

### Bootstrap, and why jobs do not reinstall

The bootstrap is idempotent and cached in persistent storage:

1. Compute a key from `sha256(requirements.txt)` and the public environment version.
2. If `$HOME/vt-deps/<key>/.ready` exists, prepend `$HOME/vt-deps/<key>` to `PYTHONPATH` and continue in about a second.
3. Otherwise download the `uv` static binary into `$HOME/bin` if missing, run `uv pip install --python <public python> --target "$HOME/vt-deps/<key>" -r requirements.txt`, write `.ready`, and continue.

The first job on a fresh account pays the install and download cost; later jobs do not. Measured on 2026-10-29: the first install took 1957 s for 105 distributions and 1.4 GB, and the next job hit the cache in 32 ms, so the first run belongs in a dedicated warmup job. The cache survives because `$HOME` and `USERDIR` persist across jobs while `TACC_WORKDIR` does not. If a target directory turns out to be unreliable under the PRoot runtime, the fallback is a virtual environment created from the public interpreter, with the same key and marker logic.

### Data staging

- Course PDFs, 12 files, 342 pages, and about 58 MB, are uploaded once with `tcloud upload` into `USERDIR`.
- OCR output, page images, the index, embedding caches, and model weights live under `USERDIR` or `$HOME/models`.
- Task directories hold code only. They are re-synchronised with `rsync --delete` on every submit and are capped at 1 GiB.
- Model weights are downloaded once with `hf download --local-dir "$HOME/models/<name>"`, because `HF_HOME` points at a job-local temporary directory that disappears with the job.

## Corpus and OCR pipeline

The decision and alternatives are in [ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md). The pipeline is three stages in one resumable job directory, `tacc/ocr/`:

1. Render: pypdfium2 at 200 DPI writes one WebP per page plus the PDF text layer when one exists. The loop owns the page number.
2. Layout: PP-DocLayoutV2 through the PaddleOCR client on CPU, for block boxes and reading order.
3. Recognition: PaddleOCR-VL-1.6 under vLLM on one RTX 3090, driven block by block or page by page according to the recipe.

Output contract (field-level schema: [corpus-schema.md](corpus-schema.md)):

- `USERDIR/corpus/pages.jsonl`: one `vt-page-record/1` object per page with `doc_id`, `pdf_sha256`, `page_no`, image geometry, model and pipeline versions, markdown, plain text, `blocks[]` with ids, reading order, labels, pixel and normalised boxes, `layout_boxes[]` with detector scores, page image references, status, timings, and validation problems.
- `USERDIR/corpus/document/<doc_id>-ocr.md`: the assembled document with `<!-- page: N -->` markers.
- `USERDIR/corpus/pages/<doc>.p<NNN>.png` and `USERDIR/corpus/images/<doc>.p<NNN>.webp`: rendered page and citation image.
- Figure crops are not emitted yet; the page WebP plus `bbox_norm` covers the citation overlay (see the schema note).

Resume and time rules: fsync every 25 pages, a sidecar of completed page keys, a 50-minute stop for new pages, exit 0 with partial output. The first run is expected to need one or two one-hour jobs for 342 pages; the throughput is unmeasured and is recorded by the first full corpus build, which is a production work item rather than a spike.

Chunking happens after OCR and is owned by `src/verifiable_tutor/corpus/`: page and section aware chunks follow the proposed `vt-chunk-record/1` shape in [corpus-schema.md](corpus-schema.md), carrying `doc_id`, `page_no`, section title, source block ids, the union box, and provenance, so every quote can be traced to a page and a box.

The old PaddleOCR transcripts are not inputs to the system. They remain usable only as a human quality reference when the OCR results look wrong.

If the Paddle stack cannot be installed at all, the first fallback is dots.ocr through the same vLLM server (native support in 0.26.0, evaluated on 2026-10-28 and recorded in [ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md#alternatives-considered)); the last resort is whole-page prompts without block boxes.

## Retrieval

See [ADR-0004](adr/0004-hybrid-retrieval-with-bge-m3.md) for the argument. Operational points:

- BM25 uses SQLite FTS5, so no extra package is needed; the index is built from page chunks.
- BGE-M3 dense vectors are computed once in `tacc/index/` on one GPU, written as a NumPy array plus a row map, and searched exactly with a single matrix multiplication. At an estimated 3,000 to 6,000 chunks this is milliseconds.
- Fusing uses reciprocal rank fusion with configurable weights. Reranking is a later experiment, not a first-version dependency.
- A Chinese query gets one English variant from the configured text model for the BM25 arm; the variant is cached by query hash, and the cost is reported in RQ4.
- Ablation arms are BM25 only, dense only, and hybrid. Optional arms are Qwen3-Embedding-0.6B and a small reranker, added only if the 50-question bake-off shows a gain.
- The span verifier is deterministic: a quoted span is accepted only if it occurs in the cited page's OCR text after whitespace and case normalisation; one repair round, then abstention.

## UI and streaming protocol

The stack and the alternatives are in [ADR-0003](adr/0003-react-spa-with-ai-elements.md). Implementation points:

- The FastAPI adapter emits the AI SDK UI message stream protocol. Events used by this project: `start`, `text-start`, `text-delta`, `text-end`, `data-step` for the progress timeline, `source-document` for citations, `finish`, and `error`.
- The same event stream is recorded to JSONL per session. Replay re-emits recorded events at a speed factor, so the offline demo runs the production frontend path with no model.
- The build runs locally. `npm ci && npm run build` writes to `src/verifiable_tutor/ui/static/`, which is generated and ignored by Git; `package-lock.json` is committed. The local backend serves the build, and no TACC job serves the UI ([ADR-0010](adr/0010-tacc-as-offline-compute.md)).
- Evidence panel: page WebP plus highlight rectangles from the OCR block boxes, no PDF viewer, no CDN, self-hosted KaTeX fonts, system CJK font stack.
- Chinese and English UI strings are kept in one translation resource with a header toggle.

## Implemented backend surface (2026-11-02)

The local backend exists and is tested with `tests/api/`. It follows the conventions in [fastapi-reference.md](fastapi-reference.md), and the structural decisions are recorded in [ADR-0012](adr/0012-fastapi-backend-structure-and-sessions.md).

- Application: `src/verifiable_tutor/api/` holds the only app factory, the routers, the dependency wiring, the AI SDK UI message stream encoder, and the chat and replay services. `src/verifiable_tutor/auth/` holds scrypt hashing, the signed server-side session cookie, the email seam, and the instructor seed logical service. `src/verifiable_tutor/knowledge/service.py` holds the card reader and the build lifecycle. `settings.py`, `storage.py`, and `trace.py` at the package root own app settings, SQLite, and the JSONL trace.
- Configuration: `config/app.yaml` owns non-secret app settings; `.env` holds the session secret, the SMTP authorization code, and provider keys. `SESSION_SECRET` is required and the app fails closed without it.
- Storage: SQLite at `data/app/app.sqlite3` (accounts, login sessions, codes, conversations, messages, build state) and JSONL traces under `data/app/traces/`; both are runtime state, and `data/app/` contents are gitignored.
- Chat: the request body is project-owned; the response is the AI SDK UI message stream v1 with `data-step` parts, the `x-conversation-id` response header, and a `[DONE]` terminator. Replay re-emits the recorded frames with scaled gaps.
- Knowledge: builds submit the existing `scripts/tacc/run_kb_job.py` driver through a subprocess runner seam; cards are read from `data/kb/records/`. A build is unavailable until `knowledge.pages_path` points at local page records.
- Practice: the run route is a documented 503 until `tacc/exec` exists. Retrieval, the disclosure gate, LangGraph orchestration, and the React UI remain planned.
- Commands: install, run, seed, and test commands are recorded in [AGENTS.md](../AGENTS.md#toolchain-and-commands).

## Backend, policy, practice, and storage

- Backend budget per request: at most 6 model calls, at most 24K context tokens of the 32K window, a per-call timeout, and a hard wall-clock ceiling. The orchestrator records every step transition in the trace.
- Model providers and secrets: `config/models.yaml` owns provider endpoints, model ids, role routing, request parameters, retry and timeout values, the response cache, and the BGE-M3 embedding settings. `.env` owns only `DEEPSEEK_API_KEY` and `MIMO_API_KEY`; [.env.example](../.env.example) is the committed template. The loader resolves the key variables at startup and fails closed when one is missing ([ADR-0005](adr/0005-external-model-apis-as-primary.md)).
- Voice and audio: an audio file attached to a message is supported only when the selected model is a MiMo 2.6 tier; flash handles it when flash is selected and pro handles it when pro is selected. Selecting DeepSeek with an audio attachment raises a capability error. The composer microphone calls MiMo ASR and inserts the transcript into the text box; the next chat turn uses the selected text provider. Assistant text can be spoken by MiMo TTS, cached by text, voice, and format. The TTS path is also the candidate for teaching-video voiceover; it has no timestamp output, so the video pipeline must split narration into segments and align captions itself.
- Policy gate: the deadline registry is a versioned YAML file in `config/`, validated by pydantic. The clock is injected, so tests can place a request before release, during an extension window, and after the deadline. Unclassifiable or unregistered requests abstain rather than guess. Every decision is logged with the state, the rule, and the registry version.
- Practice lab and self-test: generated questions and reference answers are written to a temporary directory, compiled with the public MPI toolchain, and run with a timeout and resource limits in the `tacc/exec` job; a question is shown only after its reference answer passes. Student code answers are executed the same way, per request, with a pending, running, and scored state in the UI, and the results are cached. Verified answers are cached. The demo users are two to three trusted accounts, so the exec job relies on the TACC job container and the runner limits, not on hostile-user isolation.
- Storage: local SQLite for metadata, caches, and the decision log; JSONL traces under the local data directory; `data/corpus/`, `data/index/`, and `data/caches/` hold the local mirror of the TACC artifacts. The TACC jobs write to `USERDIR`, and the backend downloads the outputs ([ADR-0010](adr/0010-tacc-as-offline-compute.md)).

## Jobs and demo modes

The platform allows one GPU job per node at a time for our purposes: the Qwen knowledge-base job, OCR, index, and the optional evaluation windows run one after another, not beside the Qwen job.

| Job directory | Resources | Purpose | Output |
|---|---|---|---|
| `tacc/serve/` | 2 GPUs, 8 CPUs, 59 min | Required Qwen knowledge-base job: one job per document shard; the job loads Qwen with vLLM at TP=2 and 32K context, reads the request and input chunks from `USERDIR`, writes knowledge records and progress, and exits | `records.jsonl` and `progress.json` in `USERDIR/kb/`; no endpoint |
| `tacc/ocr/` | 1 GPU, 8 CPUs, 59 min | Render, layout, and OCR the corpus | Page records, page images, figure crops in `USERDIR` |
| `tacc/index/` | 1 GPU, 8 CPUs, 59 min | Embed chunks and build the BM25 table | Vectors, row map, FTS5 database in `USERDIR` |
| `tacc/client/` | 4 CPUs, 59 min | Offline evaluation harness: run the benchmark over the corpus and index artifacts in `USERDIR` and the cached model responses | Evaluation JSON, traces, logs in `USERDIR` |
| `tacc/exec/` | 4 CPUs, 59 min | Per-request execution of reference tests and student code answers for practice and self-test; the local backend submits, polls, and downloads | Test results, stdout and stderr, exit codes in `USERDIR` |

Every job above is a submitted batch job: the local backend writes a request or input when needed, submits the job, polls it, downloads the result, and caches it. No SSH forwarding or inbound service is used ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).

Access facts measured on 2026-10-28: compute node addresses are private, there is no inbound path from a laptop, and tcloud has no port publishing. The 2026-11-01 clarification states that SSH port forwarding is not supported, so all TACC access is job submission and `USERDIR` exchange; the facts stay recorded in [tacc-notes.md](tacc-notes.md#access-from-outside-2026-10-28). The SPA is built with a relative `/api` base so the same build works when served by the local backend or by a local static server.

Demo modes:

1. **Local backend and UI with required TACC model serving (delivered).** The same code runs on the laptop; interactive answers call the external API; query embedding uses a local BGE-M3 copy or cached query vectors; the corpus and index are local mirrors. The demo must show one knowledge-base build end to end: start it from the UI, wait for the Qwen job, download and validate the records, browse the cards, and use them in a review outline ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).
2. **Replay (fallback).** No model, no TACC: recorded event streams play back through the real frontend and backend replay endpoint.

Evaluation results and report artifacts come from the TACC jobs. The local backend can rerun the harness from the mirrored artifacts for development. The course TACC requirement is met by two model-serving jobs, the BGE-M3 index job and the Qwen knowledge-base job, and the report cites the job ids, logs, timings, and record hashes.

## Where the backend runs

The course project brief does not state a hosting location for the backend. Its requirements are functional: build a frontend for task input, visible progress, and review; build a backend with an agent workflow, a model API, and tool and data integration; evaluate representative cases; and deliver the code repository, final report, demo, and presentation. The required execution path runs from task to user interface to application backend to visible result, and the model-serving backend appears in the architecture diagram without a host. Grading weights the project at 60 percent, split between the code repository at 30 percent and the presentation at 30 percent, and no deployment host is scored (course project brief and lecture 0 slides, in the course workspace outside this repository).

Two course sources point at TACC. The brief is titled "Course Project: build an Agent System on TACC", and the TACC tutorial frames the project as "serve Qwen on GPUs and call it from your program", with a GPU service job and a CPU client job submitted through the tcloud SDK.

The staff clarification recorded on 2026-10-28 says TACC and the provided Qwen model are not mandatory, and that external LLM APIs and external computing resources are acceptable ([tacc-notes.md](tacc-notes.md)).

The submitted proposal v1 commits to a TACC CPU job for the agent backend ([proposal v1 section 3](../proposal/proposal.md#3-proposed-system)). Proposal v3 records the current topology: the backend and UI run locally, TACC is a required model-serving backend, and Qwen is the offline knowledge-base backend ([proposal v3 section 3](../proposal/proposal_v3.md#3-proposed-system)).

Clarification of 2026-11-01: the 2026-10-30 offline-only reading is superseded. The project must use TACC as at least one model-serving backend and demonstrate a working end-to-end workflow; SSH port forwarding is not supported, and the suggested pattern is a local frontend with job submission (submit, wait, use the result). The delivered topology is therefore a local backend and UI with two TACC model-serving jobs, the BGE-M3 index job and the Qwen knowledge-base job, both reached only through job submission ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md), [tacc-notes.md](tacc-notes.md#staff-clarification-2026-11-01)).

## Repository additions

The authoritative directory table is in [README.md](../README.md#repository-layout). Planned additions, in the terms AGENTS.md uses:

- `src/verifiable_tutor/corpus/`: OCR output to chunks, page-image manifest, corpus hashing.
- `src/verifiable_tutor/llm/`: model client, replay and mock backends, caches, token accounting.
- `src/verifiable_tutor/knowledge/`: knowledge-base build orchestration, record validation, local storage, and build state.
- `scripts/tacc/run_kb_job.py`: local submit, poll, and download interface for one knowledge-base job.
- `docs/knowledge-schema.md`: request, progress, and record contracts for the knowledge base.
- `src/verifiable_tutor/ui/web/`: React source; build output in `src/verifiable_tutor/ui/static/` (ignored).
- `tacc/serve/`: the required Qwen knowledge-base job.
- `tacc/ocr/` and `tacc/index/`: the two batch job directories above.
- `tacc/exec/`: the per-request execution job for reference tests and self-test code answers.
- `config/models.yaml`: provider endpoints, model ids, role routing, request parameters, response cache, and embedding settings; secrets stay in `.env`.
- `config/knowledge.yaml`: Qwen job resources, shard size, prompt version, paths, polling, and cache key for the knowledge base.

## Rejected alternatives

| Alternative | Strongest argument for it | Why not chosen |
|---|---|---|
| Custom Docker image | The cleanest reproducibility and handover | No image field in the SDK, no Docker or root on the platform |
| SDK conda environment with pinned dependencies | Supported by design and activated automatically | Empty proxy configuration, conda 4.9.2, uncertain success |
| LangChain agents, LlamaIndex Workflows, or another high-level agent framework | Faster first prototype with tools and memory built in | Opaque control flow and implicit budgets; the project adopted only LangGraph's explicit `StateGraph` runtime for auditability, streaming, and checkpointing ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)) |
| Vector database (FAISS, Chroma, Qdrant) | Better scaling and index management | A few thousand vectors: one NumPy matrix multiplication is enough; no service to deploy |
| `pdf.js` in the browser | Full document view, no server rendering | Large bundle, CJK cmaps, and a second rendering path; server-rendered page images are simpler |
| Jinja2 and HTMX | No Node and no build step | Cannot reach the target chatbot look at acceptable cost |
| Next.js | Server components and the stack of mainstream products | Needs a Node server at runtime, which the platform lacks |
| Vue and Nuxt UI | No ramp-up for the team | Loses the ready step timeline, citation chips, and sources components; about five person-days more |
| unittest only | Zero install on TACC | The project environment is installed anyway; pytest gives the fixtures and reporting the evaluation harness needs |
| External OCR service | No install and high quality | Cost and offline reproducibility, and the project wants a real OCR model on TACC |
| dots.ocr or dots.mocr as the OCR pipeline | One model with native vLLM 0.26.0 support: the simplest deployment, no PaddlePaddle or layout model | Lower shared-protocol text accuracy than PaddleOCR-VL-1.6, 3.04B weights mean 43 to 85 minutes for the corpus and two jobs, no official recipe, and JSON repair is required; kept as the first fallback if the Paddle stack cannot be installed |
| MinerU as the OCR pipeline | Mature pipeline with a good schema | Heavier stack and AGPL weights on one variant |
| Qwen3-Embedding-4B as the default | Better Chinese to English retrieval numbers | Eight GB of weights and several times the embedding time, unproven need |
| Qwen service as the primary interactive text backend | Exact alignment with proposal v1 and no external API cost | Queue, cold start, address churn, and shared GPU contention slow interactive iteration; Qwen is now required as an offline knowledge-base backend instead ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) |
| Qwen job per chat turn | A direct TACC model-serving path | A seven to eight minute cold start per turn makes chat unusable; the knowledge-base job satisfies the required model serving without pretending to be interactive ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) |
| SSH port forwarding to a TACC Qwen endpoint | Low latency and a familiar serving pattern | The 2026-11-01 staff email does not support SSH port forwarding; all access is job submission ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) |
| Batch pre-generation without UI integration | The simplest implementation | It is not a working end-to-end workflow in the application; the demo must build the knowledge base from the UI and use its records ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)) |

## Verification spikes

Spikes 1 to 3 ran on 2026-10-29 and passed every exit criterion; the measurements are in [tacc-notes.md](tacc-notes.md#verification-spike-results-2026-10-29). Spikes 4 to 9 are unrun. Spike 10 ran on 2026-11-02 and passed (job 28067: 434 s cold start, 43.9 s for eight chunks, 8 of 8 records valid). These run in this order, and each has an exit criterion. They respect the fairness rule: one job at a time and no repeated short submissions. The full 342-page corpus build is a production work item, not a spike: its acceptance is that every page has a record and an image in `USERDIR` and a resumed run adds no duplicates, and it runs when `tacc/ocr/` is implemented. The end-to-end knowledge-base workflow is an acceptance target of the delivered product, not a spike: it is verified when the shipped feature is demonstrated ([prd.md](prd.md#8-acceptance-and-evaluation-targets)).

1. **CPU mechanics job** (4 CPUs, about 15 minutes). In one job: download `uv`, install the project delta into `$HOME/vt-deps/<key>`, import pypdfium2, create an FTS5 table, print `scontrol show job "$SLURM_JOB_ID"`, `df -h /mnt/home`, and the MPI toolchain paths. Exit criterion: the environment is reusable by a second job without reinstall. Status: passed on 2026-10-29 as job 27872 with 11 of 11 checks. The first install took 1957 s and later jobs hit the cache in 32 ms, so a first-run warmup job is mandatory before any GPU work.
2. **GPU OCR smoke job** (1 GPU, about 20 minutes). Serve PaddleOCR-VL-1.6 through vLLM, process 10 representative pages (table, formula, two-column, figure-only), and write the JSONL schema. Exit criterion: page records validate, block boxes look sane, and the measured startup plus per-page time fits a one-hour budget for 342 pages. Status: passed on 2026-10-29 as job 27879 with 8 of 8 checks: 10 of 10 pages and 171 blocks without validation problems, median 4.26 s per page, vLLM startup 281 s, and a projected 1,934 s for 342 pages.
3. **Whole-document PDF parse job** (1 GPU, about 10 minutes). Parse one complete PDF file the way the demo will: copy the file into the job workspace, enumerate every page, render each page, run layout and recognition for every page, and assemble one document markdown with page markers. Exit criterion: every page parses, the per-page JSONL validates, and one document markdown exists. Status: passed on 2026-10-29 as job 27884: `course_project.pdf`, 8 of 8 pages, 121 blocks, median 3.905 s per page, a 10,003 byte document markdown with 8 page markers, and a 414 s job body.
4. **Index job** (1 GPU, 59 minutes). Embed the chunks with BGE-M3, build the FTS5 table, and run the 50-question bake-off over BM25, dense, and hybrid. Exit criterion: page-hit@5 and nDCG are recorded and the primary model choice is confirmed or overturned.
5. **Offline artifact round trip** (laptop plus one CPU job, about 20 minutes). Run a small OCR and index subset through the batch jobs, download the artifacts into `data/corpus/` and `data/index/`, and start the local backend against the mirror. Exit criterion: the backend answers one benchmark question from TACC-produced artifacts with no TACC job running, and the corpus hash and job ids match the job logs ([ADR-0010](adr/0010-tacc-as-offline-compute.md)).
6. **End-to-end smoke** (laptop plus external API calls, about 30 minutes). Ten benchmark questions through the local backend with the span verifier and the policy gate, using cached responses for repeat runs. Exit criterion: traces, tests, and results follow the required execution path.
7. **LangGraph import spike** (4 CPUs, about 15 minutes). Install the LangGraph dependency group through the bootstrap, import `langgraph` and `langgraph-checkpoint-sqlite` under the public interpreter, and run a two node graph with the SQLite checkpointer. Exit criterion: the import and the graph run inside one job; otherwise record the in-memory saver fallback ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)).
8. **Local Langfuse spike** (laptop, no TACC job). Bring up the Docker Compose stack from [langfuse-local.md](langfuse-local.md), emit one trace with a session id, and confirm the health endpoints, the web UI, and `TELEMETRY_ENABLED=false`. Exit criterion: one trace is visible and the backend still answers with tracing disabled.
9. **Self-test execution spike** (1 CPU job plus external API calls, about 20 minutes). Submit one `tacc/exec` job that compiles a generated reference answer, runs its tests, and executes one sample code answer; poll the job from the local backend, download the results, and measure queue plus run time. Exit criterion: the results are downloadable, cached, and the measured latency is recorded; the report states the trusted-user assumption.
10. **Qwen knowledge-base job and file round trip** (2 GPUs, 59 minutes, one document shard). The local driver writes the request manifest and a small chunk batch to `USERDIR`, submits one `tacc/serve` job, and polls it; the job starts vLLM with Qwen, reads the input, writes records and progress to `USERDIR`, and exits; the driver downloads and validates the result. Exit criterion: the Qwen model call chain runs inside one job, the records validate against [knowledge-schema.md](knowledge-schema.md), the local backend downloads and stores them, and queue, cold-start, and build time are recorded. Status: passed on 2026-11-02 as job 28067 on 10-0-3-10: the course `serve.sh` launcher was ready after 434 s, eight page-level chunks produced eight schema-valid records in 43.9 s, every citation quote was found on its page, and no repair was needed ([tacc-notes.md](tacc-notes.md#qwen-knowledge-base-job-spike-10-2026-11-02)).

## Risks and open questions

- `uv` and a target install under PRoot are verified (2026-10-29): the target install works and imports all four project packages, but the first install takes about 33 minutes and PyPI needed retries. The bootstrap retries, sets a longer HTTP timeout, and serialises concurrent installs. Fallbacks: a virtual environment from the public interpreter, then the SDK conda environment.
- The PaddlePaddle CPU wheel installs and imports under PRoot (2026-10-29, paddle 3.2.1), and PP-DocLayoutV2 runs on CPU. The remaining fallback is pure vLLM whole-page prompts with page-level citations only.
- Two PRoot network quirks are recorded on 2026-10-29: `hf download` against the HF mirror hits TLS certificate verification errors, so layout weights come through the PaddleX modelscope path, and the first install must not be combined with GPU work because it can consume most of a one-hour job.
- The 2026-11-01 clarification states that SSH port forwarding is not supported: no tunnel is built, no job port is reached from the laptop, and all TACC access is job submission and `USERDIR` exchange ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).
- Cluster capacity was tight on 2026-10-28: no idle nodes, several drain and down. Submit the batch jobs early, keep the local mirror current, and keep replay ready; do not assume a node on demand.
- External model APIs add an outage, cost, and data-egress risk. Every call is cached and labelled; evaluation must run from cache, and a benchmark run needs an explicit paid-call budget. A local demo needs an embedding path for BGE-M3: a local copy of the model or cached query vectors.
- TTS has no timestamps and its free period is temporary, so teaching-video voiceover needs a quality and pacing check before it becomes a deliverable.
- The first OCR and embedding runs may exceed one hour. Mitigation: resume, per-document shards, and 50-minute self-stop.
- The Qwen knowledge-base job paid a 434 s vLLM cold start on 2026-11-02 (job 28067) and must fit one hour: shard by document, keep outputs resumable, and pre-build the demo knowledge base. Malformed records are repaired once; a failed shard is retried ([knowledge-schema.md](knowledge-schema.md)).
- Group storage is 100 GB shared by three accounts; the expected footprint is a few GB for weights, about 58 MB of PDFs, a few hundred MB of OCR output and page images, and small index files.
- The comparison between OCR output and PDF text is not a correctness oracle; human spot checks on figure-heavy slides remain part of RQ1.
- The frontend build depends on the laptop Node toolchain; a clean machine needs Node and `npm ci` before it can serve the UI.
- LangGraph adds a dependency group that must be pinned and import-verified on TACC, and its SQLite checkpointer depends on the native sqlite-vec extension, which may fail under PRoot; the fallback is the in-memory saver plus the JSONL session store ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)).
- The local Langfuse stack adds a six container Docker Compose dependency, about 5 to 10 GB of disk, and a startup step to the development loop; it is local only and the application must fail open when it is down ([ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md), [langfuse-local.md](langfuse-local.md)).
- The schema is single-course by design. Multi-course support is recorded as future development in [prd.md](prd.md#future-development) and would be a data model migration, not a configuration switch.
- Self-test code execution depends on the TACC queue: a per-request `tacc/exec` job can wait minutes and the one-hour job cap bounds the batch size. The demo has two to three trusted users, the UI shows pending, running, and scored states, and the measured queue and run time goes into the report.
- The self-test execution path does not claim hostile-user isolation. The demo accounts belong to the team; a real deployment would need a sandboxed execution environment ([ADR-0009](adr/0009-typed-agent-tools-instead-of-a-shell.md)).
- The demo mode and the TACC boundary are settled by the 2026-11-01 requirement: the backend and UI run locally, TACC is a required model-serving backend, and every TACC call is a submitted job ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)). The knowledge-base build is the required end-to-end demonstration.

## References

- Platform constraints and budgets: [tacc-notes.md](tacc-notes.md)
- Knowledge-base records and build settings: [knowledge-schema.md](knowledge-schema.md), [config/knowledge.yaml](../config/knowledge.yaml)
- Model providers and secrets: [config/models.yaml](../config/models.yaml), [.env.example](../.env.example), [ADR-0005](adr/0005-external-model-apis-as-primary.md), and [ADR-0006](adr/0006-same-model-retries-without-cross-model-fallback.md)
- Repository layout and directory ownership: [README.md](../README.md#repository-layout)
- Agent rules: [AGENTS.md](../AGENTS.md)
- Course project brief, public environment guide, and package lists: course workspace, outside this repository
