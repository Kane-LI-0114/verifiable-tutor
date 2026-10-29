# Agent guide

This file tells an AI agent how to work in this repository: what exists now, which files are the sources of truth, which commands are safe, which conventions to follow, and the workflow that feature work must follow. For the reader-facing project description, use [README.md](README.md); for what each directory is for, use [README.md#repository-layout](README.md#repository-layout).

## Current state

- Substantive content: the course project proposal, the product requirements in [docs/prd.md](docs/prd.md), the domain vocabulary in [GLOSSARY.md](GLOSSARY.md), the documentation entry points (`README.md`, `AGENTS.md`), the setup docs under `docs/agents/`, the platform notes in [docs/tacc-notes.md](docs/tacc-notes.md), the technology selection in [docs/tech-selection.md](docs/tech-selection.md), nine decision records under `docs/adr/`, the local tracing and email runbooks in [docs/langfuse-local.md](docs/langfuse-local.md) and [docs/email-local.md](docs/email-local.md), the PaddleOCR-VL request and response reference in [docs/paddleocr-vl-api.md](docs/paddleocr-vl-api.md), the RQ2 benchmark protocol in [docs/benchmark-protocol.md](docs/benchmark-protocol.md), the PRD use case, container, and entity relationship diagrams under `docs/figures/`, the TACC bootstrap and shared OCR stage helpers under `scripts/tacc/`, the spike jobs under `tacc/env-spike/`, `tacc/ocr-smoke/` and `tacc/pdf-parse/`, the model provider configuration in `config/models.yaml` with the committed `.env.example` template, and the implemented model layer: `src/verifiable_tutor/llm/config.py`, `src/verifiable_tutor/llm/adapter.py` (chat, streaming with replay, ASR, TTS, MiMo audio-file routing, DeepSeek search and fetch, file-backed response cache), the `tests/llm/` suite, `pyproject.toml`, `uv.lock`, and `scripts/smoke_model_adapter.py`. Proposal assets: `.gitignore`, `proposal/build_proposal.py`, `proposal/proposal.md`, `proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx`, the matching `.pdf`, `proposal/figs/fig1_usecase.dot`, `proposal/figs/fig1_usecase.png`, `proposal/figs/fig2_components.dot`, `proposal/figs/fig2_components.png`, and two committed page previews under `proposal/preview/`.
- The remaining directories are still `.gitkeep` placeholders: `benchmarks/`, `data/`, `examples/`, `tacc/serve/`, `tacc/client/`, and the unbuilt `src/verifiable_tutor/` subpackages (`policy/`, `orchestrator/`, `evidence/`, `practice/`, `teaching/`, `eval/`, `ui/`).
- The model layer is implemented and tested locally. LangGraph is the decided orchestration runtime, Langfuse the decided local tracing layer, and the typed tool runner the decided execution boundary; all three are pending implementation ([ADR-0008](docs/adr/0008-langgraph-as-agent-orchestration-runtime.md), [ADR-0007](docs/adr/0007-langfuse-for-local-model-call-tracing.md), [ADR-0009](docs/adr/0009-typed-agent-tools-instead-of-a-shell.md)). The product requirements are in [docs/prd.md](docs/prd.md) (version 0.6) and the vocabulary in [GLOSSARY.md](GLOSSARY.md); the auth, UI, policy, evidence, practice, teaching, and evaluation packages are still `.gitkeep` placeholders. Multi-course support is out of scope and recorded as future development in the PRD. No other application code exists yet, and there is no CI, no `LICENSE`, and no benchmark input or result data. pytest is the chosen framework and `tests/llm/` is the first suite.
- Do not assume a module, entry point, test runner, or benchmark result exists because a directory is named after it. The package, packaging files, and test runner are recorded in [Toolchain and commands](#toolchain-and-commands).

## Sources of truth

| Content | Master | Regenerate with |
|---|---|---|
| Proposal text | Constants in `proposal/build_proposal.py` (`TITLE`, `MOTIVATION`, `SYSTEM`, and the rest) | `python3 proposal/build_proposal.py`, which rewrites `proposal/proposal.md` and the `.docx` |
| Proposal figures | `proposal/figs/fig1_usecase.dot` and `proposal/figs/fig2_components.dot` | `dot -Gdpi=300 -Tpng <source>.dot -o <source>.png` |
| PRD diagrams | `docs/figures/prd-usecase.dot`, `docs/figures/prd-containers.dot`, `docs/figures/prd-er.dot`, `docs/figures/prd-sequence-question.dot`, and `docs/figures/prd-sequence-grading.dot` | `dot -Gdpi=200 -Tpng <source>.dot -o <source>.png` |
| Proposal PDF | The `.docx` | Manual export outside this repository; no script here produces it |
| Page previews | The exported PDF | Manual export; no script in this repository renders them |
| Project description and directory roles | [README.md](README.md) | Edit by hand |
| Product requirements and acceptance | [docs/prd.md](docs/prd.md) | Edit by hand; the proposal stays frozen and this file owns what ships |
| RQ2 benchmark protocol | [docs/benchmark-protocol.md](docs/benchmark-protocol.md) | Edit by hand; rerun the dry run after changing the baseline, the shared set, or the target values |
| Domain vocabulary | [GLOSSARY.md](GLOSSARY.md) | Edit by hand when a term is resolved |
| Technology decisions | [docs/tech-selection.md](docs/tech-selection.md) and the ADRs under `docs/adr/` | Edit by hand; append a new ADR to supersede a decision |
| Corpus record fields | [docs/corpus-schema.md](docs/corpus-schema.md) | Edit by hand; bump the record schema version when a field changes meaning |
| PaddleOCR-VL request and response contract | [docs/paddleocr-vl-api.md](docs/paddleocr-vl-api.md) | Edit by hand; re-verify field names against the pinned PaddleOCR and PaddleX releases when either version changes |
| Model providers and request parameters | `config/models.yaml` (no secrets); keys only in the ignored `.env` | Edit by hand; `.env.example` is the committed template |
| Local development tracing procedure | [docs/langfuse-local.md](docs/langfuse-local.md); the decision is [ADR-0007](docs/adr/0007-langfuse-for-local-model-call-tracing.md) | Edit by hand |
| Registration and reset email procedure | [docs/email-local.md](docs/email-local.md) | Edit by hand |
| Agent rules | This file | Edit by hand |

- Edit the constants in `proposal/build_proposal.py`, then rerun the script. Never hand-edit `proposal/proposal.md` or the `.docx`: the next build overwrites both.
- Re-rendering the committed figures with the command above reproduces the committed PNGs byte for byte (checked on 2026-10-28).
- The proposal is frozen as a two-page A4 document. A substantial addition breaks the layout, so confirm the page count before committing a proposal change. The PDF and the previews are not regenerated by any command in this repository; refresh them by hand when the DOCX changes.
- After a rebuild, run `git diff` and confirm the generated files changed only because the constants changed.

## Toolchain and commands

Verified locally on 2026-10-28 and 2026-10-29:

- `python3` is Python 3.11.9 (the interpreter used for the proposal build; the application targets 3.12 per [ADR-0001](docs/adr/0001-pinned-python-environment-without-docker.md)), `python-docx` 1.2.0 is installed, and Graphviz `dot` is 14.1.5.
- Build or refresh the proposal: `python3 proposal/build_proposal.py`. It is the only runnable build in the repository.
- That script imports `docx`, but no `requirements.txt` or `pyproject.toml` records the requirement. On a fresh interpreter, install it with `python3 -m pip install python-docx` (this requirement is inferred from the import, not declared by a file).
- Re-render one proposal figure: `dot -Gdpi=300 -Tpng proposal/figs/fig1_usecase.dot -o proposal/figs/fig1_usecase.png`, and the same pattern for `fig2_components`.
- Re-render a PRD diagram after editing its source: `dot -Gdpi=200 -Tpng docs/figures/prd-containers.dot -o docs/figures/prd-containers.png`, and the same pattern for `prd-usecase`, `prd-er`, `prd-sequence-question`, and `prd-sequence-grading`.
- Create the local application environment: `uv venv .venv --python 3.12` then `uv pip install -e '.[dev]'`. The application targets Python 3.12 and `pyproject.toml` is the packaging source.
- Run the test suite: `.venv/bin/python -m pytest`. The first suite is `tests/llm/` (configuration, chat, streaming, ASR, TTS, audio-file routing, search, fetch, cache); the runner is recorded here as the TDD change required.
- Run the live model smoke: `.venv/bin/python scripts/smoke_model_adapter.py`. It makes real DeepSeek and MiMo calls with the keys in `.env`, including audio-file input and TTS, is not part of pytest, and exits non-zero on a failed step (verified 2026-10-29, ten steps).
- Start the optional local Langfuse stack only when tracing is needed; the steps are in [docs/langfuse-local.md](docs/langfuse-local.md). Neither pytest nor any TACC job depends on it.
- Run one PDF through the TACC OCR job from the laptop: `python3 scripts/tacc/parse_pdf.py --pdf <file.pdf> --pages 1-3`. It uploads the file, submits the job, polls it, downloads the results, and prints one JSON object; verified 2026-10-29 with jobs 27887 and 27889. The record fields are in [docs/corpus-schema.md](docs/corpus-schema.md).
- There is no application build or server run command yet, and no UI build command. [docs/tech-selection.md](docs/tech-selection.md) lists the planned commands and the verification spikes; record any new command here in the change that adds it.

## Where new work goes

| Change | Location |
|---|---|
| Disclosure gate and deadline registry | `src/verifiable_tutor/policy/` |
| Accounts, authentication, sessions, and roles | `src/verifiable_tutor/auth/` |
| LangGraph workflow, state schema, and context budget | `src/verifiable_tutor/orchestrator/` |
| Typed tools and the restricted execution runner | `src/verifiable_tutor/orchestrator/` and `src/verifiable_tutor/practice/` |
| Hybrid retrieval (BM25 plus dense) and span verifier | `src/verifiable_tutor/evidence/` |
| Practice pack generation and executable tests | `src/verifiable_tutor/practice/` |
| Line-anchored explainer | `src/verifiable_tutor/teaching/` |
| Evaluation harness | `src/verifiable_tutor/eval/` |
| Browser UI source; built assets are written to `src/verifiable_tutor/ui/static/` | `src/verifiable_tutor/ui/web/` |
| Optional baseline GPU job for the Qwen service | `tacc/serve/` |
| GPU job for the OCR pipeline (render, layout, recognition) | `tacc/ocr/` |
| Whole-PDF parse job for the demo OCR path | `tacc/pdf-parse/` (week-one prototype; the production pipeline moves into `tacc/ocr/` and `src/verifiable_tutor/corpus/`) |
| GPU job for embeddings and the BM25 index | `tacc/index/` |
| CPU job for the agent backend and the evaluation harness | `tacc/client/` |
| CPU job that runs reference tests and self-test code answers | `tacc/exec/` |
| Corpus build from OCR output, page images, chunking, and corpus hashing | `src/verifiable_tutor/corpus/` |
| Model provider config, adapter, and response cache (implemented); replay and mock backends, token accounting (pending) | `src/verifiable_tutor/llm/` |
| Course questions and policy scenarios | `benchmarks/questions/`, `benchmarks/policy_scenarios/` |
| Self-test generation and grading benchmark data | `benchmarks/self_test/` (planned) |
| Generated benchmark results | `benchmarks/results/` |
| Configuration such as the deadline registry, model providers, request parameters, and the local tracing settings | `config/` |
| OCR output and page images, retrieval index, embedding and response caches | `data/corpus/`, `data/index/`, `data/caches/` |
| Helper scripts | `scripts/` |
| Report and PRD figures | `docs/figures/` |
| Example inputs and outputs | `examples/` |
| Tests | `tests/` |

- Python code targets Python 3.12 and uses the `src/` layout. The dependency and environment strategy is [ADR-0001](docs/adr/0001-pinned-python-environment-without-docker.md); local development uses a uv-managed 3.12 interpreter. The package name is `verifiable_tutor`, so a module added at `src/verifiable_tutor/policy/gate.py` is imported as `from verifiable_tutor.policy.gate import ...`.
- Run code with the editable install in `.venv`; without installing the package, `PYTHONPATH=src .venv/bin/python` also works.
- Tests are written before the implementation and live under `tests/`; [Test-driven development](#test-driven-development) owns the loop and the file naming. The framework is pytest; the change that adds the first test records the runner command here.
- Keep new files inside the mapped directory. If a change makes the directory roles stale, update [README.md#repository-layout](README.md#repository-layout) in the same commit.

## Test-driven development

Every new feature follows the red, green loop. A feature is new or changed behavior in `src/verifiable_tutor/` or in a TACC job directory (`tacc/`); documentation and proposal edits are not features. A feature change without a test that failed first is not complete, even when tests cover it afterwards.

- Red first: write one failing test, run it, and confirm it fails for the intended reason. A test that fails to import, or fails on an unrelated assertion, is not red yet.
- Green second: write only enough implementation to make that test pass. Do not add behavior the current test does not require.
- One slice at a time: one seam, one test, one minimal change, then plan the next test from what the last cycle taught. Do not write a batch of tests for imagined behavior.
- Refactor after green, under the protection of the passing tests, and keep refactoring out of the red to green cycle.

Tests observe behavior at seams. A seam is the public boundary through which the feature can be observed, such as an exported module function, a deadline-registry query, a retrieval call, or an HTTP endpoint. Tests stay blind to internal structure: a test that breaks when internals are renamed but behavior is unchanged sits at the wrong seam.

- Before the first test of a feature, name the seams under test, each with one line on what it catches and what it misses. When the request does not name them, confirm the seams with the user before writing tests; no test is written at an unconfirmed seam.
- Aim tests at the critical paths and complex logic those seams expose, not at every edge case.
- Take expected values from an independent source: a worked example from the course material, a known-good literal, or behavior the proposal states. Do not recompute the expected value the way the implementation does, and do not assert a constant against itself.
- Mock only at process or network boundaries: the TACC model service, external LLM and search APIs, and the clock. Do not mock internal collaborators, and do not verify through a side channel (index files, caches, logs) what the interface already returns.
- Reproduce a reported defect with a failing test before fixing it.
- Name tests after the capability in domain terms, for example `test_before_deadline_refuses_complete_solution_and_offers_hint`. If the repository gains a `GLOSSARY.md` or ADRs near the change, read them and use their terms.

Tests live under `tests/` and mirror the package path: `src/verifiable_tutor/policy/gate.py` is tested at `tests/policy/test_gate.py`. The framework and its command are recorded in [Toolchain and commands](#toolchain-and-commands).

## Conventions

- Write English documentation in GitHub-flavored Markdown with sentence-case headings.
- Do not use em dashes, en dashes, or a double hyphen as an aside. Use commas, colons, parentheses, or a single hyphen instead.
- One fact, one home. This file owns agent rules; [README.md](README.md) owns the project description and directory roles. Link instead of duplicating, and update the owning file when a fact changes.
- Commit messages follow Conventional Commits with a scope, matching the existing history: `chore(repo): initialize project repository` and `docs(proposal): add student IDs to title block`. Keep one logical change per commit.
- Keep the `.gitkeep` files; they are why the empty scaffold directories exist in Git.
- Never commit generated or runtime output: data, caches, logs, Slurm logs, temporary and scratch work, example outputs, environment files, or macOS metadata. `.gitignore` is the authoritative list of ignored paths; do not force-add an ignored file.
- `.env.example` is the only environment file that may be committed, and it must contain no real secrets.
- Do not edit the proposal `.docx` or `.pdf` binaries by hand. Rebuild the DOCX from the script and replace the PDF only through a manual export.
- Never commit course PDFs or transcripts: the contents of `data/corpus/` are gitignored so course materials are not redistributed.
- `benchmarks/results/` is not gitignored (see Known gaps). Stage only small, curated result files there.

## TACC and model serving

This repository is a standalone Git repository nested inside the course workspace at `../../`, so paths beginning with `../../` are outside the repository and do not resolve on a hosted copy. The project targets the course TACC@HKUST platform. `tacc/env-spike/`, `tacc/ocr-smoke/` and `tacc/pdf-parse/` are the committed spike jobs; `tacc/serve/`, `tacc/ocr/`, `tacc/index/`, `tacc/exec/`, and `tacc/client/` are planned task directories. The authoritative workflow is the course documentation outside this repository: the course workspace instructions in `../../CLAUDE.md` and the copies in `../../tacc-env-docs/`. Treat this section as a pointer, not the authority. All paths in this section are on TACC or inside a task directory, not in this repository.

- The course uses the official SDK CLI: configure with `tcloud config -u USERNAME -f PRIVATE_KEY`, then `tcloud init`, and submit from a task directory containing `tuxiv.conf` with `tcloud submit`.
- Inspect a job with `tcloud ps -j JOB_ID`, read its log with `tcloud cat slurm_log/<task>-<JOB_ID>.log`, fetch outputs with `tcloud download <remote> <local>`, and release resources with `tcloud cancel -j JOB_ID`.
- The Qwen service is a GPU job in `tacc/serve/`: vLLM serving model `qwen3.8-27b` on port 8000, 32K context, at most 4 concurrent requests, 2x RTX 3090, tensor parallel 2. It is an optional baseline: the primary text generation uses external OpenAI-compatible APIs ([ADR-0005](docs/adr/0005-external-model-apis-as-primary.md)), configured in `config/models.yaml` with keys in `.env`. The agent backend or client is a separate CPU job in `tacc/client/`.
- The service is ready only when its log contains `Application startup complete`. The log then prints `SERVICE_BASE_URL=http://NODE:8000/v1`; the client writes that value into its `server-url.txt` before submission. The address expires when the job ends.
- Hard constraints: cancel GPU jobs when finished; `/mnt/home/public/course-envs/CSIT6000V/` is read-only, so never install dependencies into it or modify it; on the `tacc` partition, Slurm exports host-global CUDA device indices while the container enumerates devices from zero, so CUDA jobs must `unset CUDA_VISIBLE_DEVICES` or CUDA reports no CUDA-capable device.
- No custom images: the SDK job schema has no image field, and accounts have no Docker or root. The dependency strategy is a hash-pinned project environment installed into `$HOME` ([ADR-0001](docs/adr/0001-pinned-python-environment-without-docker.md)); GPU work keeps the public environment.
- Keep one entrypoint item per job: the SDK joins multiple entrypoint entries into a single command line. Keep task directories to code, because a submit directory is capped at 1 GiB; put corpus, page images, indexes, and weights in `USERDIR` or `$HOME` with `tcloud upload`.
- Platform mechanics measured from the SDK source and the live cluster configuration (submit cap, persistence, single entrypoint, container facts) are recorded in [docs/tacc-notes.md](docs/tacc-notes.md#platform-mechanics-2026-10-28).
- Compute nodes are private and have no inbound path from a laptop. The documented off-platform access path is an SSH local forward through the account's SSH entry; the course documents both prescribe and prohibit student-run forwarding, so the policy is unresolved. Read [docs/tacc-notes.md](docs/tacc-notes.md#access-from-outside-2026-10-28) before designing a demo around a tunnel.
- The scheduler enforces a one-hour limit: `sinfo` reports `TIMELIMIT 1:00:00` for the `tacc` partition, so every job requests `time=00:59:00`. A persistent OCR service is therefore a 59-minute job with a 438 to 495 s cold start; plan the demo window accordingly and keep replay ready. Staff clarifications received on 2026-10-28 and the resulting job and storage budgets are recorded in [docs/tacc-notes.md](docs/tacc-notes.md); that file owns them.
- `tacc/pdf-parse/` is the demo prototype: one PDF in, per-page records plus one document markdown out. `scripts/tacc/parse_pdf.py` is the local request interface that submits it.

## Before claiming a change is done

- Docs: every cited path and relative link resolves from this directory (`test -e` each one), no em dash or en dash appears, no double hyphen is used as an aside, and every claim traces to a file in this repository or to the course docs described above.
- Proposal changes: rerun `python3 proposal/build_proposal.py`, inspect `git diff` for `proposal/proposal.md` and the DOCX, re-export the PDF and previews if the DOCX changed, and confirm the document is still two pages.
- File hygiene: `git status --short` shows only the intended files, `.gitkeep` files are untouched, and no generated artifact, cache, log, environment file, or benchmark dump is staged.
- Features: every slice has a test that was seen to fail for the intended reason before the implementation, passes after it, and the seams covered are stated in the change description.
- Code: run `.venv/bin/python -m pytest` locally and the same suite on TACC when a job can execute it, cancel any GPU job started for the test, and record the exact command used.

## Known gaps and open decisions

Known gaps:

- No root `requirements.txt`; packaging lives in `pyproject.toml` with `uv.lock`, and the TACC job requirements live in `scripts/tacc/requirements-tacc.txt`.
- The response cache has no TTL or eviction; delete `data/caches/model/` or change `cache.directory` to invalidate it.
- No UI build script yet. The first frontend change adds the `npm ci && npm run build` flow and records the command here.
- No script exports the proposal PDF or the page previews; both are manual steps outside this repository.
- `benchmarks/results/` is not gitignored, so large run outputs can be committed by accident.
- There is no `LICENSE` and no CI workflow.
- LangGraph and its dependency group are decided but not installed; the graph topology, the TACC import spike, and the SQLite checkpointer fallback are pending ([ADR-0008](docs/adr/0008-langgraph-as-agent-orchestration-runtime.md)).
- Langfuse is local only; TACC runs emit no traces by design, so evaluation evidence comes from JSONL and job logs ([ADR-0007](docs/adr/0007-langfuse-for-local-model-call-tracing.md), [docs/langfuse-local.md](docs/langfuse-local.md)).
- Self-test answer grading and the `tacc/exec` job are planned but not implemented; the per-request TACC queue latency and the trusted-user assumption are unmeasured.
- The RQ2 benchmark protocol in [docs/benchmark-protocol.md](docs/benchmark-protocol.md) has not been run; no self-test benchmark data or results exist yet.
- Multi-course support is a deliberate limitation of this deliverable and is recorded as future development in [docs/prd.md](docs/prd.md#future-development).

Open decisions, not settled by this repository:

- The technology choices are settled in [docs/tech-selection.md](docs/tech-selection.md) and the ADRs under `docs/adr/`: packaging and dependency pinning, test framework, OCR pipeline, embedding model, UI stack, model backend, retry behavior, local tracing, and the orchestration runtime. Do not reopen them in code; supersede a decision with a new ADR.
- The command execution boundary is settled in [ADR-0009](docs/adr/0009-typed-agent-tools-instead-of-a-shell.md); implement it before any user-supplied code runs.
- The allowed registration domains and the email verification flow are defaults recorded in the open questions of [docs/prd.md](docs/prd.md); confirm them before implementation.
- Self-test generation and TACC execution are P0 while answer grading is P1; code answers use per-request TACC jobs under the team account with two to three trusted demo users. Confirm the split and the acceptable queue latency.
- The proposal PDF export remains a manual step outside this repository; it is not a project dependency.
- Spikes 1 to 3 in [docs/tech-selection.md#verification-spikes](docs/tech-selection.md#verification-spikes) ran on 2026-10-29 and passed. Their measurements are in [docs/tacc-notes.md](docs/tacc-notes.md#verification-spike-results-2026-10-29); the raw artifacts are in `USERDIR/env-spike/`, `USERDIR/ocr-smoke/` and `USERDIR/pdf-parse/` on TACC. Spikes 4 to 10 are unrun; record their findings in the same file when they happen.

## Agent skills

### Issue tracker

Issues live in the GitHub Issues of `Kane-LI-0114/verifiable-tutor`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use the default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
