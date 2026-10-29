# ADR-0007: Local model-call tracing with Langfuse

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The course evaluation path is explicitly "LOGS / TRACES → TEST CASES → RESULTS", and the final presentation must present the evaluation and its limitations. Generated content must be attributable: which provider, model, parameters, thinking level, retry count, token usage, and latency produced an answer, and which workflow steps touched it.

Earlier decisions cover a JSONL session trace for replay ([ADR-0003](0003-react-spa-with-ai-elements.md)), a file-backed response cache, and provider attribution in the configuration ([ADR-0005](0005-external-model-apis-as-primary.md)). None of them is an inspection surface: there is no view of individual model calls, no latency or cost aggregation, no way to compare two runs, and no per-step view of the agent workflow. The project lead asked for this gap to be filled with Langfuse on 2026-10-29.

Constraints from the lead and the platform:

- Tracing is for local development only. TACC evaluation may not depend on it, and the laptop is the only place where the stack runs.
- Course material and user content may not leave the laptop through the tracing path.
- Every added service must keep the request path working when it is unavailable.

Langfuse facts verified on 2026-10-29 from the published packages and documentation:

- The Langfuse server is open source at its core, MIT licensed, and self-hosted deployments have no usage limits on the core features (tracing, sessions, users, token and cost tracking, datasets, prompt management). Enterprise features that need a license (data retention policies, project RBAC, audit logs, server-side masking) are not used by this project.
- The official Docker Compose stack runs six containers: `langfuse-web`, `langfuse-worker`, Postgres 17, ClickHouse, Redis 7, and MinIO. It is the documented option for local use and testing, without high availability, scaling, or built-in backup.
- The current Python SDK is 5.0.4, OpenTelemetry based, and requires a Langfuse server 4.59.0 or later. The `:4` image tag tracks the latest v4 server, which satisfies that requirement.
- The SDK supports session and user attributes, metadata and tags, sampling, masking, a tracing enable flag, and a no-op mode when no keys are configured. It ships a LangChain callback handler, which traces LangGraph nodes and tools ([ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)).
- Self-hosted telemetry is enabled by default and sends aggregate usage metrics to PostHog; it does not send prompts, traces, or observations. It can be disabled with `TELEMETRY_ENABLED=false`.

## Decision

- Use a self-hosted Langfuse OSS instance as the local-development tracing layer. The stack runs from the upstream Docker Compose file on the laptop with the `:4` server tag and Python SDK 5.x; it is reached at `http://localhost:3000`, and `TELEMETRY_ENABLED=false` is set in its environment.
- Trace every model call (chat, streaming, ASR, TTS, search, and fetch) as a generation, and every agent workflow step (graph node, tool call, retrieval, span verification, policy decision) as a span. The trace carries `session_id` for the chat session, the internal user identifier (never the email address), the benchmark case id and run id when running the evaluation harness, and tags for environment and run type.
- Langfuse is an observability and provenance layer, not the source of truth. The JSONL session trace remains canonical for replay, offline demos, and evaluation reruns, so no submitted artifact may require a Langfuse instance or a network call to read. Tracing fails open: a missing key, the disabled flag, or an unreachable instance never fails a request.
- The Langfuse SDK is a local development dependency only. It is not added to `scripts/tacc/requirements-tacc.txt`, and TACC evaluation runs emit JSONL and job logs instead. The report draws trace evidence from exported local traces and from the TACC records, and states which surface each figure comes from.
- The end-user interface does not link to Langfuse and never shows a raw trace id. The user-visible work chain is rendered from the application's own event stream ([ADR-0003](0003-react-spa-with-ai-elements.md)) and shows steps, thinking, and command executions; Langfuse links are available only in development and in the report.
- Configuration: endpoint, environment, release, sampling, and the enable flag live in a new `config/observability.yaml`; only `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` live in the ignored `.env`, and [.env.example](../../.env.example) gains empty placeholders. The exact local procedure is recorded in [docs/langfuse-local.md](../langfuse-local.md).

## Consequences

**Positive:**

- Every answer can be traced to its provider, model, parameters, retries, tokens, latency, and workflow steps, which the evaluation report and the failure analysis need.
- The course required path "LOGS / TRACES → TEST CASES → RESULTS" has a concrete artifact: trace exports, dashboard screenshots, and per-case trace links cited in the report.
- LangGraph runs are traced through the LangChain callback handler, so graph nodes and tool executions appear without custom instrumentation.
- Local-only hosting keeps prompts, course excerpts, and user content on the laptop, and the OSS license makes the software free.

**Negative:**

- A six container Docker Compose stack joins the development machine: roughly 5 to 10 GB of disk for images and data, about 8 GB of memory assigned to Docker, and one to three minutes of startup. It adds one more failure mode to the local loop.
- TACC runs carry no Langfuse traces by design, so TACC evidence depends on JSONL and job logs, and the two surfaces must be kept consistent by hand when the report is assembled.
- Server and SDK move quickly: a new SDK major requires a minimum server version, and major server upgrades need migration steps.
- OSS lacks retention policies and project-level RBAC, so data cleanup is a local reset of the stack, and access control is the laptop itself. Neither is needed for a course project.

**Neutral:**

- This is a development tool, not a production tracing service.

**Follow-up:**

- Write the local runbook at [docs/langfuse-local.md](../langfuse-local.md) with secrets, headless initialization, health checks, reset, and upgrade steps.
- Add `langfuse` as an optional `dev` dependency, guarded by the enable flag, with a no-op fallback when tracing is off.
- Record the trace id on every assistant answer and in the JSONL event record so the two surfaces can be cross-referenced.
- Revisit Langfuse Cloud Hobby only if the local Docker stack becomes a burden; it is an acceptable fallback with the same SDK contract.

## Alternatives considered

**JSONL only, without a tracing service.** For: zero extra infrastructure, already required for replay, and no new failure mode. Against: no query UI, no aggregation, no per-step inspection, and no cost view; the lead asked for the missing provenance surface to be filled.

**Langfuse Cloud Hobby (free).** For: zero setup, 50k units per month, 30 day data access, two users, and the same SDK contract. Against: prompts, course excerpts, and user content leave the laptop, which the lead rejected in favor of local-only tracing; kept as a fallback.

**Self-hosted Langfuse on a remote VM.** For: reachable by teammates and screenshots can be shared by URL. Against: a paid host and a public surface for a laptop demo, and the TACC runs still produce no traces; not chosen.

**OpenTelemetry collector with Grafana Tempo or Jaeger.** For: generic distributed tracing and a mature ecosystem. Against: no LLM semantics such as generations, token and cost tracking, prompt debugging, sessions, or evaluation features without a large amount of glue work; not chosen.

**LangSmith.** For: polished LangChain-native tracing. Against: hosted and proprietary, so course content leaves the laptop and the course does not reimburse external services; not chosen.

## References

- Docker Compose deployment guide: https://langfuse.com/self-hosting/deployment/docker-compose
- Upstream Docker Compose file: https://github.com/langfuse/langfuse/blob/main/docker-compose.yml
- Self-hosting overview and licensing: https://langfuse.com/self-hosting and https://langfuse.com/self-hosting/license-key
- Self-hosted telemetry: https://langfuse.com/self-hosting/security/telemetry
- Headless initialization: https://langfuse.com/self-hosting/administration/headless-initialization
- Health and readiness endpoints: https://langfuse.com/self-hosting/configuration/health-readiness-endpoints
- LangGraph integration: https://langfuse.com/integrations/frameworks/langgraph
- Python SDK 5.0.4 inspected on 2026-10-29: https://pypi.org/project/langfuse
- Model layer seam: [../../src/verifiable_tutor/llm/adapter.py](../../src/verifiable_tutor/llm/adapter.py)
- Streaming contract: [ADR-0003](0003-react-spa-with-ai-elements.md)
- Orchestration runtime: [ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)
