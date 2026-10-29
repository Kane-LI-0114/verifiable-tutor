# Technology selection

Scope: implementation technology for this repository. It does not change the frozen two-page proposal. Platform constraints are owned by [tacc-notes.md](tacc-notes.md); this document owns the choices, the operational plan, and the verification list. The architectural choices are argued in [`docs/adr/`](adr/), and the repository layout is owned by [README.md](../README.md#repository-layout).

Status: decided on 2026-10-28 and updated on 2026-10-29 for the external model APIs, the retry policy, Langfuse tracing, and LangGraph. The model layer, its tests, and its live smoke script are implemented; the remaining subsystems are planned, and the two committed spike jobs have no recorded results yet.

## Decisions at a glance

| Area | Decision | Why |
|---|---|---|
| Python runtime | 3.12 everywhere: 3.12.14 in the course public environment, 3.12.13 locally through uv | One version for both legs removes a whole class of skew |
| Dependency and environment strategy | Hash-pinned `requirements.txt` plus `uv.lock`, installed by an idempotent bootstrap into `$HOME`; the GPU stack stays on the read-only public environment; `Dockerfile` is for local development only | The platform has no custom-image support and a 1 GiB submit cap ([ADR-0001](adr/0001-pinned-python-environment-without-docker.md)) |
| Backend | FastAPI and uvicorn in one process, serving both the API and the built UI on one origin; server-sent events through `StreamingResponse` | Both are pinned in the public environment; one origin survives SSH tunnelling and offline demos |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS 4, shadcn/ui, AI Elements, `@ai-sdk/react`, streamdown, KaTeX, Shiki | Mainstream chatbot stack with ready components for the timeline and citations ([ADR-0003](adr/0003-react-spa-with-ai-elements.md)) |
| Corpus and OCR | PaddleOCR-VL-1.6 on vLLM, PP-DocLayoutV2 layout on CPU, page images through pypdfium2, per-page JSONL with page numbers and block boxes, resumable one-hour jobs | Page numbers and block boxes are what the evidence requirement and citation panel need ([ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md)) |
| Retrieval | SQLite FTS5 BM25 plus BGE-M3 dense vectors, fused with reciprocal rank fusion; an English query variant feeds the BM25 arm for Chinese queries | Multilingual, no vector database, and the proposal's ablation arms are preserved ([ADR-0004](adr/0004-hybrid-retrieval-with-bge-m3.md)) |
| Embedding model | BGE-M3 primary; Qwen3-Embedding-0.6B fallback; Qwen3-Embedding-4B upgrade path | Fits the RTX 3090 and CPU query embedding, MIT licensed, strong cross-lingual retrieval |
| Model client | `openai` SDK against external OpenAI-compatible providers: DeepSeek `deepseek-flash` for chat, Xiaomi MiMo `mimo-v2.6-flash` and `mimo-v2.6-pro` when selected; temperature 0; replay and mock backends behind one interface | External APIs remove the shared-Qwen queue and cold start; keys stay in `.env` and settings in `config/models.yaml` ([ADR-0005](adr/0005-external-model-apis-as-primary.md)) |
| Model failure handling | Retry the selected model up to `defaults.max_retries`; never switch models or providers automatically; after exhaustion return a timeout or unavailable message and let the user retry | Keeps each answer attributable to the model the user selected and makes failures explicit ([ADR-0006](adr/0006-same-model-retries-without-cross-model-fallback.md)) |
| Orchestration | LangGraph typed `StateGraph` as the single orchestration runtime: policy, retrieval, evidence verification, generation, citation checks, and teaching and practice flows are nodes; SQLite checkpointer per user and session; FastAPI hosts the graph with no LangGraph Platform | Explicit graph, persistence, streaming, and human in the loop come from the framework while tests stay at graph seams ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)) |
| Local tracing | Langfuse OSS v4 self-hosted with Docker Compose on the laptop, for local development only; JSONL stays canonical for replay and TACC evaluation | Model call and graph step provenance with local data, a framework-native LangGraph integration, and fail-open behavior; never installed on TACC ([ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md)) |
| Accounts and access | Email and password accounts restricted to course student domains, server-side cookie sessions signed with a secret from `.env`, scrypt password hashing, a student and an instructor role, and QQ Mail SMTP with an authorization code for registration codes and reset links | A course design needs a basic user system and no third-party identity provider; the detailed requirements are in [prd.md](prd.md), the QQ Mail procedure in [email-local.md](email-local.md) |
| Tool execution | The model calls typed LangGraph tools only; execution tools use one restricted subprocess runner (no shell interpolation, per-user scratch directory, environment allowlist without secrets, resource limits, timeout and process group kill); no generic shell | No strong sandbox is available on TACC, and typed tools keep every action auditable and visible in the work chain ([ADR-0009](adr/0009-typed-agent-tools-instead-of-a-shell.md)) |
| Grading assistant | A separate TA-side workflow over an assignment package and a batch of TA-uploaded submissions; per-criterion score recommendations with evidence, a review workbench, an audit log, and CSV export after approval | Human oversight keeps grades accountable, and the model, tool, and trace layers are reused ([ADR-0010](adr/0010-ta-grading-agent.md)) |
| Grading execution | Untrusted student code runs only in a local Docker sandbox (no network, read-only root, non-root user, one writable directory, CPU, memory, process, and time limits); TACC runs no grading code | The TACC job container gives process-level limits only, which are insufficient for third-party code ([ADR-0011](adr/0011-grading-execution-sandbox.md)) |
| Voice input and output | Audio-file attachments are supported only when a MiMo model is selected; the selected tier handles the audio. The composer microphone uses MiMo `mimo-v2.5-asr`, and assistant text can be synthesized with the MiMo TTS family for playback and as a teaching-video voiceover candidate | DeepSeek has no audio; one provider covers both audio directions ([ADR-0005](adr/0005-external-model-apis-as-primary.md), [model-providers.md](model-providers.md)) |
| Policy gate | YAML deadline registry validated by pydantic, rule and embedding intent routing, injected clock, JSONL decision log, fail closed to abstention | Deterministic and resistant to prompt injection |
| Practice lab | Subprocess runner with timeouts and resource limits against the public MPI toolchain; a generated solution is accepted only after its tests pass | Mirrors the assignment environment |
| Storage | SQLite for metadata, grading records, FTS5, and caches; NumPy arrays for vectors; JSONL for traces and replay | No external service, and everything is copyable between `USERDIR` and the laptop |
| Tests | pytest with the red and green loop, run inside the project environment on TACC | The framework decision that AGENTS.md left open |
| Evaluation | Benchmark JSONL, an evaluation harness that writes JSON, plots generated locally | matplotlib is absent from the public environment |
| Jobs and demo | `tacc/serve` for the optional Qwen baseline, `tacc/ocr`, `tacc/index`, `tacc/client`; the live demo currently runs from a local backend and UI, TACC provides the OCR, index, and evaluation evidence, and replay is the fallback; grading runs locally in Docker and adds no TACC job; the TACC-hosted demo is open pending the TA reply | The one-hour policy cap, per-job service addresses, and demo risk |

## Environment strategy

The full argument is in [ADR-0001](adr/0001-pinned-python-environment-without-docker.md); this section records the mechanics that implementers need.

### Two layers, no image

- GPU layer: the course public environment. vLLM 0.26.0, PyTorch 2.11.0+cu128, Transformers 5.10.4, Python 3.12.14, 199 packages total. It is read-only and must not be modified.
- Project layer: everything the project adds, pinned in `requirements.txt` with hashes and in `uv.lock`. The expected delta is `pypdfium2` for page rendering, `pytest` for tests, the PaddleOCR client plus `paddlepaddle` CPU wheel for the OCR job, and the LangGraph dependency group (`langgraph`, `langchain-core`, `langgraph-checkpoint-sqlite`) for the agent backend ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)). The Langfuse SDK is a local development extra only and is never installed on TACC ([ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md)). The public environment already provides FastAPI, uvicorn, pydantic, openai, httpx, NumPy, PyYAML, sse-starlette, and Pillow.
- Grading layer: Docker on the laptop only. Untrusted student code runs in one container per submission ([ADR-0011](adr/0011-grading-execution-sandbox.md)); nothing in this layer exists on TACC, which has no Docker or root.

### Bootstrap, and why jobs do not reinstall

The bootstrap is idempotent and cached in persistent storage:

1. Compute a key from `sha256(requirements.txt)` and the public environment version.
2. If `$HOME/vt-deps/<key>/.ready` exists, prepend `$HOME/vt-deps/<key>` to `PYTHONPATH` and continue in about a second.
3. Otherwise download the `uv` static binary into `$HOME/bin` if missing, run `uv pip install --python <public python> --target "$HOME/vt-deps/<key>" -r requirements.txt`, write `.ready`, and continue.

The first job on a fresh account pays the install and download cost; later jobs do not. The cache survives because `$HOME` and `USERDIR` persist across jobs while `TACC_WORKDIR` does not. If a target directory turns out to be unreliable under the PRoot runtime, the fallback is a virtual environment created from the public interpreter, with the same key and marker logic.

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

Output contract:

- `USERDIR/corpus/pages.jsonl`: one record per page with `doc_id`, `pdf_sha256`, `page_no`, image geometry, model and pipeline version, markdown, plain text, blocks with reading order and boxes, figures with crops, tables, formulas, status, and timings.
- `USERDIR/corpus/pages/<doc>.p<NNN>.md`: page markdown for human inspection.
- `USERDIR/corpus/images/<doc>.p<NNN>.webp`: page image for the citation panel.
- `USERDIR/corpus/figures/`: cropped figures referenced by the block records.

Resume and time rules: fsync every 25 pages, a sidecar of completed page keys, a 50-minute stop for new pages, exit 0 with partial output. The first run is expected to need one or two one-hour jobs for 342 pages; the throughput is unmeasured and is a spike item.

Chunking happens after OCR and is owned by `src/verifiable_tutor/corpus/`: page and section aware chunks carry `doc_id`, `page_no`, section title, and source block ids, so every quote can be traced to a page and a box.

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
- The build runs locally. `npm ci && npm run build` writes to `src/verifiable_tutor/ui/static/`, which is generated and ignored by Git; `package-lock.json` is committed. The TACC job receives the built assets in its task directory.
- Evidence panel: page WebP plus highlight rectangles from the OCR block boxes, no PDF viewer, no CDN, self-hosted KaTeX fonts, system CJK font stack.
- Chinese and English UI strings are kept in one translation resource with a header toggle.

## Backend, policy, practice, and storage

- Backend budget per request: at most 6 model calls, at most 24K context tokens of the 32K window, a per-call timeout, and a hard wall-clock ceiling. The orchestrator records every step transition in the trace.
- Model providers and secrets: `config/models.yaml` owns provider endpoints, model ids, role routing, request parameters, retry and timeout values, the response cache, and the BGE-M3 embedding settings. `.env` owns only `DEEPSEEK_API_KEY` and `MIMO_API_KEY`; [.env.example](../.env.example) is the committed template. The loader resolves the key variables at startup and fails closed when one is missing ([ADR-0005](adr/0005-external-model-apis-as-primary.md)).
- Voice and audio: an audio file attached to a message is supported only when the selected model is a MiMo 2.6 tier; flash handles it when flash is selected and pro handles it when pro is selected. Selecting DeepSeek with an audio attachment raises a capability error. The composer microphone calls MiMo ASR and inserts the transcript into the text box; the next chat turn uses the selected text provider. Assistant text can be spoken by MiMo TTS, cached by text, voice, and format. The TTS path is also the candidate for teaching-video voiceover; it has no timestamp output, so the video pipeline must split narration into segments and align captions itself.
- Policy gate: the deadline registry is a versioned YAML file in `config/`, validated by pydantic. The clock is injected, so tests can place a request before release, during an extension window, and after the deadline. Unclassifiable or unregistered requests abstain rather than guess. Every decision is logged with the state, the rule, and the registry version.
- Practice lab: generated solutions are written to a temporary directory, compiled with the public MPI toolchain, and run with a timeout and resource limits; a solution is accepted only after the pack's tests pass. Verified solutions are cached.
- Storage: SQLite at `USERDIR/state/` for metadata, caches, and the decision log; `USERDIR/index/` for vectors and BM25 tables; `USERDIR/traces/` for JSONL traces and replay logs. `data/caches/` and `data/index/` remain the local mirrors for development.

## Jobs and demo modes

The platform allows one GPU job per node at a time for our purposes: the Qwen baseline, when used, occupies both GPUs, so OCR and embedding jobs run before evaluation windows, not beside it.

| Job directory | Resources | Purpose | Output |
|---|---|---|---|
| `tacc/serve/` | 2 GPUs, 8 CPUs, 59 min | Optional baseline: the course Qwen service command; our copy sets the 59-minute policy request | `SERVICE_BASE_URL` in the log |
| `tacc/ocr/` | 1 GPU, 8 CPUs, 59 min | Render, layout, and OCR the corpus | Page records, page images, figure crops in `USERDIR` |
| `tacc/index/` | 1 GPU, 8 CPUs, 59 min | Embed chunks and build the BM25 table | Vectors, row map, FTS5 database in `USERDIR` |
| `tacc/client/` | 4 CPUs, 59 min | Agent backend plus the static UI, and the evaluation harness run | Traces, evaluation JSON, logs in `USERDIR` |

Access facts measured on 2026-10-28: compute node addresses are private, there is no inbound path from a laptop, and tcloud has no port publishing. An SSH local forward through `gw.turing.ust.hk:30041` reaches arbitrary cluster addresses and ports, though gateway to job-container reachability is still unverified. The only forwarding use the course documents explicitly is a local client reaching the provided model service on `NODE:8000`; forwarding to a student-run web service is not described anywhere, and the student commands contain a general sentence against self-set-up forwarding that conflicts with the service instruction. The exact wording is recorded in [tacc-notes.md](tacc-notes.md#access-from-outside-2026-10-28). The SPA is built with a relative `/api` base so the same build works when served by the backend or by a local static server.

Demo modes, in order of current planning:

1. **Local backend and UI (current primary).** The same code runs on the laptop; text generation calls the external API directly, and query embedding uses either a local BGE-M3 copy or cached query vectors; the corpus and index are mirrored from `USERDIR`. This is the development and demo mode until the TA replies, because it removes queue, job-lifetime, and network risk from the live demo. The report states that this mode was used.
2. **TACC-hosted backend and UI (open).** The `tacc/client` job serves the API and the static UI on one origin; the laptop forwards a local port to the node port with `ssh -p 30041 -N -L 127.0.0.1:8080:<node>:8080 <user>@gw.turing.ust.hk`. The backend calls the external text API through the cluster egress and runs BGE-M3 for query embedding in the same job. This matches the proposal's execution path and needs no CORS, but it needs an authorization answer for the web-port forward and a passed tunnel spike.
3. **Replay (last resort).** No model, no TACC: recorded event streams play back through the real frontend and backend replay endpoint.

Evaluation results and report artifacts always come from the TACC jobs, whatever mode the live demo uses. The questions about forwarding to a student web port and about whether the final demo must run the backend on TACC were sent to the TA on 2026-10-29; the reply sets whether the TACC-hosted mode becomes the primary one.

## Where the backend runs

The course project brief does not state a hosting location for the backend. Its requirements are functional: build a frontend for task input, visible progress, and review; build a backend with an agent workflow, a model API, and tool and data integration; evaluate representative cases; and deliver the code repository, final report, demo, and presentation. The required execution path runs from task to user interface to application backend to visible result, and the model-serving backend appears in the architecture diagram without a host. Grading weights the project at 60 percent, split between the code repository at 30 percent and the presentation at 30 percent, and no deployment host is scored (course project brief and lecture 0 slides, in the course workspace outside this repository).

Two course sources point at TACC. The brief is titled "Course Project: build an Agent System on TACC", and the TACC tutorial frames the project as "serve Qwen on GPUs and call it from your program", with a GPU service job and a CPU client job submitted through the tcloud SDK.

The staff clarification recorded on 2026-10-28 says TACC and the provided Qwen model are not mandatory, and that external LLM APIs and external computing resources are acceptable ([tacc-notes.md](tacc-notes.md)).

The submitted proposal commits to a TACC CPU job for the agent backend ([proposal section 3](../proposal/proposal.md#3-proposed-system)). That is a project commitment, not a course requirement.

Reading on 2026-10-29: the backend is built and demoed locally first, and the TACC CPU job remains the evidence path for the evaluation and the report. A local backend that calls the external model API and uses a local or cached embedding path is acceptable for live use, provided the report states which mode the demo used. The TA was asked on 2026-10-29 whether forwarding to a student web port is allowed and whether the final demo must run the backend on TACC; the reply decides whether the TACC-hosted mode is added.

## Repository additions

The authoritative directory table is in [README.md](../README.md#repository-layout). Planned additions, in the terms AGENTS.md uses:

- `src/verifiable_tutor/corpus/`: OCR output to chunks, page-image manifest, corpus hashing.
- `src/verifiable_tutor/llm/`: model client, replay and mock backends, caches, token accounting.
- `src/verifiable_tutor/ui/web/`: React source; build output in `src/verifiable_tutor/ui/static/` (ignored).
- `src/verifiable_tutor/grading/`: assignment package ingestion, the grading graph, the Docker sandbox runner, the audit log, and the CSV export.
- `tacc/ocr/` and `tacc/index/`: the two batch job directories above.
- `config/models.yaml`: provider endpoints, model ids, role routing, request parameters, response cache, and embedding settings; secrets stay in `.env`.

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
| Qwen service as the primary text backend | Exact alignment with the frozen proposal and no external API cost | Queue, cold start, address churn, and shared GPU contention slow iteration and demo reliability; kept as an optional baseline ([ADR-0005](adr/0005-external-model-apis-as-primary.md)) |
| Unattended automatic grading | No TA effort at all | A wrong grade would be final, evidence optional, and appeals impossible; the assistant recommends and the TA approves ([ADR-0010](adr/0010-ta-grading-agent.md)) |
| Running student code in the TACC job container for grading | The closest environment to the course assignments | TACC gives no strong sandbox for untrusted code, and the one-hour job and queue make interactive grading impractical; grading runs in a local Docker sandbox ([ADR-0011](adr/0011-grading-execution-sandbox.md)) |

## Verification spikes

No job has been submitted yet. These run in week one, in this order, and each has an exit criterion. They respect the fairness rule: one job at a time and no repeated short submissions.

1. **CPU mechanics job** (4 CPUs, about 15 minutes). In one job: download `uv`, install the project delta into `$HOME/vt-deps/<key>`, import pypdfium2, create an FTS5 table, print `scontrol show job "$SLURM_JOB_ID"`, `df -h /mnt/home`, and the MPI toolchain paths. Exit criterion: the environment is reusable by a second job without reinstall.
2. **GPU OCR smoke job** (1 GPU, about 20 minutes). Serve PaddleOCR-VL-1.6 through vLLM, process 10 representative pages (table, formula, two-column, figure-only), and write the JSONL schema. Exit criterion: page records validate, block boxes look sane, and the measured startup plus per-page time fits a one-hour budget for 342 pages.
3. **Corpus job** (1 GPU, 59 minutes, resumable). Run the full 342 pages; if it does not finish, run a second job and confirm resume without duplicates. Exit criterion: all pages have records and images in `USERDIR`.
4. **Index job** (1 GPU, 59 minutes). Embed the chunks with BGE-M3, build the FTS5 table, and run the 50-question bake-off over BM25, dense, and hybrid. Exit criterion: page-hit@5 and nDCG are recorded and the primary model choice is confirmed or overturned.
5. **Tunnel job** (4 CPUs, about 20 minutes). Serve a stub page on port 8080. First check from the login node whether the gateway can reach `<node>:8080`; then forward `127.0.0.1:8080` to the node and load the page in a browser, including one refresh. Exit criterion: the page loads through the tunnel, a killed and restarted tunnel recovers, and the demo mode is fixed afterwards. Ask the TA about the forwarding policy before the demo.
6. **End-to-end smoke** (1 CPU job plus external API calls, about 30 minutes). Ten benchmark questions through the full pipeline with the span verifier and the policy gate, using cached responses for repeat runs. Exit criterion: traces, tests, and results follow the required execution path.
7. **LangGraph import spike** (4 CPUs, about 15 minutes). Install the LangGraph dependency group through the bootstrap, import `langgraph` and `langgraph-checkpoint-sqlite` under the public interpreter, and run a two node graph with the SQLite checkpointer. Exit criterion: the import and the graph run inside one job; otherwise record the in-memory saver fallback ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)).
8. **Local Langfuse spike** (laptop, no TACC job). Bring up the Docker Compose stack from [langfuse-local.md](langfuse-local.md), emit one trace with a session id, and confirm the health endpoints, the web UI, and `TELEMETRY_ENABLED=false`. Exit criterion: one trace is visible and the backend still answers with tracing disabled.
9. **Grading sandbox spike** (laptop, no TACC job). Build one assignment image, run a benign submission and a deliberately hostile one (network access, a read of `$HOME` or the repository, a write outside the mount, and a fork storm) in the Docker sandbox from [ADR-0011](adr/0011-grading-execution-sandbox.md), and confirm the limits and rejections. Exit criterion: the hostile submission cannot reach the network or host files, the runner kills a timeout, and the evidence records the image digest.

## Risks and open questions

- `uv` and a target install under PRoot are the largest environment risk. Fallbacks: a virtual environment from the public interpreter, then the SDK conda environment.
- The PaddlePaddle CPU wheel may fail to install. Fallback: pure vLLM whole-page prompts, page-level citations only.
- Gateway to job-container port reachability is unverified; the SSH forward plumbing works and arbitrary target ports are not restricted. No document addresses student forwarding to a web port directly; the general prohibition and the model-service instruction conflict. If the TA disallows it or the spike fails, the demo uses the local backend and UI with text generation through the external API and a local or cached embedding path.
- Cluster capacity was tight on 2026-10-28: no idle nodes, several drain and down. Start the service and backend jobs early and keep replay ready; do not assume a node on demand.
- External model APIs add an outage, cost, and data-egress risk. Every call is cached and labelled; evaluation must run from cache, and a benchmark run needs an explicit paid-call budget. A local demo needs an embedding path for BGE-M3: a local copy of the model or cached query vectors.
- TTS has no timestamps and its free period is temporary, so teaching-video voiceover needs a quality and pacing check before it becomes a deliverable.
- The first OCR and embedding runs may exceed one hour. Mitigation: resume, per-document shards, and 50-minute self-stop.
- The optional Qwen baseline address changes with every job; when it is used, the client writes it from the current log into the task configuration before submission.
- Group storage is 100 GB shared by three accounts; the expected footprint is a few GB for weights, about 58 MB of PDFs, a few hundred MB of OCR output and page images, and small index files.
- The comparison between OCR output and PDF text is not a correctness oracle; human spot checks on figure-heavy slides remain part of RQ1.
- The frontend build depends on the laptop Node toolchain; a clean machine needs Node and `npm ci` before it can serve the UI.
- LangGraph adds a dependency group that must be pinned and import-verified on TACC, and its SQLite checkpointer depends on the native sqlite-vec extension, which may fail under PRoot; the fallback is the in-memory saver plus the JSONL session store ([ADR-0008](adr/0008-langgraph-as-agent-orchestration-runtime.md)).
- The local Langfuse stack adds a six container Docker Compose dependency, about 5 to 10 GB of disk, and a startup step to the development loop; it is local only and the application must fail open when it is down ([ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md), [langfuse-local.md](langfuse-local.md)).
- Grading adds a Docker dependency on the laptop and one image per assignment. The local image reproduces the course assignment environment, it is not the environment itself, so the report states the alignment per assignment ([ADR-0011](adr/0011-grading-execution-sandbox.md)).
- Grading quality depends on the assignment package and on a small constructed sample; RQ5 is reported as a small-sample result, not as a validated automatic grader ([ADR-0010](adr/0010-ta-grading-agent.md)).
- The schema is single-course by design. Multi-course support is recorded as future development in [prd.md](prd.md#future-development) and would be a data model migration, not a configuration switch.
- The TA was asked on 2026-10-29 whether the final demo must run the backend on TACC and whether forwarding to a student web port is allowed; no reply is recorded yet. Until the reply, the local backend is the demo mode and TACC stays the evaluation evidence path.

## References

- Platform constraints and budgets: [tacc-notes.md](tacc-notes.md)
- Model providers and secrets: [config/models.yaml](../config/models.yaml), [.env.example](../.env.example), [ADR-0005](adr/0005-external-model-apis-as-primary.md), and [ADR-0006](adr/0006-same-model-retries-without-cross-model-fallback.md)
- Repository layout and directory ownership: [README.md](../README.md#repository-layout)
- Agent rules: [AGENTS.md](../AGENTS.md)
- Course project brief, public environment guide, and package lists: course workspace, outside this repository
