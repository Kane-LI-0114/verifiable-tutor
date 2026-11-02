# ADR-0012: FastAPI backend structure, storage, and sessions

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-02 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The repository had no HTTP layer. The technology selection and ADR-0003, ADR-0008, ADR-0010, and ADR-0011 settle the stack: a local FastAPI process serves the API and the built React SPA on one origin, exposes the AI SDK UI message stream protocol, and reaches TACC only through submitted jobs. [docs/fastapi-reference.md](../fastapi-reference.md) distilled the official FastAPI documentation into implementation rules.

The PRD requires the first product surfaces now: accounts with verification and reset (FR-A1 to FR-A9), streamed answers with a session trace and replay (FR-B10, FR-B12, FR-I1), voice (FR-G1, FR-G3), knowledge-card browsing and the Qwen build lifecycle (FR-K1 to FR-K3), and corpus page images for the citation panel (FR-B5). Retrieval, the disclosure gate, the LangGraph runtime, `tacc/exec`, and the React UI do not exist yet.

## Decision

**Package and layering.** The HTTP boundary lives in `src/verifiable_tutor/api/`: `factory.py` builds the only `FastAPI` instance, `main.py` exposes the module-level app for the CLI, `deps.py` wires dependencies from `app.state`, `routers/` holds thin endpoints, `streaming.py` encodes the AI SDK protocol, `chat.py` and `replay.py` hold the chat and replay services. Domain logic lives in its mapped packages: `verifiable_tutor/auth/` (security, email, accounts and sessions) and `verifiable_tutor/knowledge/` (cards and build orchestration). Settings, SQLite storage, and the JSONL trace live at the package root (`settings.py`, `storage.py`, `trace.py`) because more than one layer uses them. Tests import `create_app` with explicit settings and injected fakes, never `main`.

**Configuration.** Non-secret settings live in `config/app.yaml`: allowed registration domains, cookie flags and lifetimes, local data paths, chat history depth, replay speed, and the knowledge-build pages path. Secrets stay in the ignored `.env` and are read through the existing `llm.config.load_dotenv` parser, so the repository keeps one dotenv reader. `SESSION_SECRET` is required and the app fails closed without it. `pydantic-settings` is not adopted in this change; adopting it would replace the single dotenv reader rather than add a second one.

**Storage.** Accounts, login sessions, verification and reset values, conversations, messages, and knowledge-build state live in SQLite at `data/app/app.sqlite3` with WAL and short-lived connections. `data/app/` is gitignored; the database and the JSONL traces under `data/app/traces/` are runtime state. The API "session" is the user-visible conversation; the login session is internal (`login_sessions`). A restart marks interrupted builds as failed.

**Accounts.** scrypt with per-password salt, opaque registration codes and reset tokens stored hashed and single use, and a server-side login session whose cookie value is `token.HMAC-SHA256(token, SESSION_SECRET)`. The cookie is HttpOnly, `SameSite=Lax`, seven-day sliding, and deleted at logout. Email uses QQ Mail SMTP when configured and otherwise writes the code or link to the backend log (FR-A8). The instructor account is seeded by `python -m verifiable_tutor.api.seed` (FR-A9).

**Chat contract.** The request body is project-owned (`message`, optional `session_id`, `provider`, `tier`). The response is the AI SDK UI message stream v1: SSE `data:` parts for `start`, `data-step`, text and reasoning start/delta/end, `finish`, and `error`, the `x-vercel-ai-ui-message-stream: v1` header, and a terminating `data: [DONE]`. The live response also carries `x-conversation-id` so a new conversation is addressable. Every frame is appended to the conversation's JSONL trace with a timestamp and internal user id; replay re-emits the recorded frames with scaled and capped gaps.

**Provider protocol versus product protocol.** The provider layer stays OpenAI-compatible behind the existing adapter (DeepSeek and MiMo are both `openai_compatible`). The browser boundary deliberately does not expose the OpenAI Chat Completions schema: the project needs work-chain steps, citations, user-facing error copy, cookie sessions, persistence, and replay, and `useChat` consumes the AI SDK stream. An OpenAI-compatible `/v1/chat/completions` endpoint is recorded as a future interop option; it would reuse the same chat service and needs Bearer-to-user and model-alias mapping first.

**Deferred wiring.** `chat.py` streams ungrounded model text for now. Retrieval, the span verifier, and the disclosure gate will plug into the same service and HTTP contract; the LangGraph runtime (ADR-0008) will replace the service internals. The practice-run route is a documented 503 scaffold until `tacc/exec` exists. The model adapter is created lazily on the first model-backed request, so health, accounts, knowledge browsing, and replay work without provider keys.

**Knowledge builds.** `POST /api/knowledge/builds` validates the instructor role and the `knowledge.pages_path` setting, records a `queued` build, and runs the existing `scripts/tacc/run_kb_job.py` driver in a subprocess through an injectable runner; states are `queued`, `running`, `ready`, and `failed`. Cards are read from the validated JSONL the driver stores under `data/kb/records/`. No TACC logic is duplicated, and tests replace the runner.

## Consequences

**Positive:**

- One HTTP contract for the frontend, the replay path, and the tests, with OpenAPI generated from the route decorators.
- Domain logic sits in its mapped packages, so retrieval, policy, and orchestration can grow without touching the HTTP boundary.
- Tests need no provider key, SMTP server, or TACC account; the fakes sit exactly at those boundaries.
- The build lifecycle reuses the verified TACC round trip instead of a second implementation.

**Negative:**

- The frontend needs a thin custom `ChatTransport` because the chat request body is project-owned; this is one small file when the UI lands.
- Without pydantic-settings, app settings are loaded by hand from YAML plus the existing dotenv parser; the loader must stay in sync with `.env.example`.
- SQLite is single-process by design; the local demo is one process, and replication is out of scope.
- Ungrounded chat answers are visibly weaker than the final product until the evidence and policy packages exist.

**Neutral:**

- The API version stays `0.1.0`; the project version in `pyproject.toml` is unchanged.
- `data/app/` joins the runtime data directories that are downloaded or regenerated, not committed.

## Alternatives considered

**pydantic-settings now.** For: the documented FastAPI pattern and validation. Against: the repository already has a dotenv reader and YAML config loaders; a second reader would drift. Why not chosen: keep one reader, revisit when the settings surface grows.

**Expose the OpenAI Chat Completions protocol to the browser.** For: familiar schema and third-party client compatibility. Against: no work-chain or citation parts, Bearer-style auth conflicts with cookie sessions, and `useChat` does not consume it. Why not chosen: the product needs a project protocol; an optional interop endpoint remains a recorded follow-up.

**Native `fastapi.sse.EventSourceResponse` or `sse-starlette` for chat.** For: less encoder code. Against: the exact AI SDK part types, the `[DONE]` terminator, and the project `data-step` part need direct control of frames and headers. Why not chosen: one tested encoder in `api/streaming.py` keeps the wire contract explicit.

**Land LangGraph orchestration first.** For: one runtime for the agent workflow (ADR-0008). Against: the HTTP contract, accounts, persistence, and replay are independent and are needed by the graph anyway. Why not chosen: ship the stable seam first; the graph replaces service internals later.

**Server-side sessions in memory or files.** For: no table. Against: sessions must survive a refresh and a restart during the demo, and the trace and build state already need SQLite. Why not chosen: one SQLite database keeps local state inspectable.

## Follow-ups

- Wire retrieval, the span verifier, and the disclosure gate into `ChatService` and add the `source-document` frames.
- Replace the chat service internals with the ADR-0008 LangGraph graph; keep the HTTP contract and trace format.
- Implement the practice-run and `tacc/exec` execution path, then replace the 503 scaffold.
- Build the React SPA and its custom `ChatTransport`; then verify the AI SDK stream against the real client.
- Decide the optional OpenAI-compatible interop endpoint after the UI path works.
- Add a CI workflow and the missing `LICENSE`.

## References

- [ADR-0003](0003-react-spa-with-ai-elements.md), [ADR-0005](0005-external-model-apis-as-primary.md), [ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md), [ADR-0010](0010-tacc-as-offline-compute.md), [ADR-0011](0011-tacc-as-required-model-serving-backend.md)
- [docs/fastapi-reference.md](../fastapi-reference.md)
- [docs/prd.md](../prd.md), [docs/email-local.md](../email-local.md), [docs/knowledge-schema.md](../knowledge-schema.md)
