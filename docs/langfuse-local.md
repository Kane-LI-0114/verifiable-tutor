# Local Langfuse tracing

Local development runbook for the Langfuse instance behind [ADR-0007](adr/0007-langfuse-for-local-model-call-tracing.md). This instance traces agent graph steps during local development only. TACC evaluation runs do not use it and do not depend on it.

Versions are pinned on both sides: the server images are `4.82.0` and the Python SDK is `langfuse==5.2.0` in the `dev` extra of [pyproject.toml](../pyproject.toml). The SDK 5.x line requires a server 4.59.0 or later, so the pinned pair is compatible.

## What it is for

- Inspect each model call: provider, model, parameters, thinking level, retries, tokens, latency, and cost.
- Inspect each agent step: graph node, retrieval, span verification, policy decision, tool call, and command output.
- Compare runs and collect trace exports and screenshots for the evaluation report and failure analysis.

The JSONL session trace remains the canonical replay and evaluation record. Langfuse is an inspection layer and may be unavailable without affecting the application.

## Cost

| Item | Cost |
|---|---|
| Software license | 0. Langfuse OSS is MIT licensed, and core tracing, sessions, users, token and cost tracking, datasets, and prompt management have no usage limit |
| Hosting | 0. The stack runs on the laptop; no VM or cloud account |
| Disk | About 5 to 10 GB on first use (image download plus volumes); measure with `docker system df` |
| Memory | About 8 GB assigned to Docker Desktop on a 24 GB machine |
| Time | One or two hours for the first setup including the image download; one to three minutes per start |
| Network | Image pulls only; the instance works without internet access after the images are present |

Enterprise features (data retention policies, project RBAC, audit logs, server-side masking) need a license and are not used.

## Prerequisites

- Docker Desktop for macOS, running. Check with `docker info`.
- `git`, `curl`, and `openssl`.
- Free ports: 3000 (web UI), 9090 (MinIO console), and the localhost-only ports 3030, 5432, 6379, 8123, 9000, 9091.

## First setup

1. Start Docker Desktop and confirm the daemon is reachable:

   ```bash
   open -a Docker
   docker info
   ```

2. Clone the upstream repository at the pinned release. The Compose file lives at the repository root.

   ```bash
   git clone --depth 1 --branch v4.82.0 https://github.com/langfuse/langfuse.git ~/tools/langfuse
   cd ~/tools/langfuse
   ```

3. Create a `.env` next to `docker-compose.yml`. Compose expands these values into the file's `CHANGEME` defaults, so every secret must be set. Generate values with `openssl rand -hex 32` (for `ENCRYPTION_KEY`) and `openssl rand -base64 24` (for the others).

   | Variable | Value |
   |---|---|
   | `NEXTAUTH_URL` | `http://localhost:3000` |
   | `NEXTAUTH_SECRET` | random |
   | `SALT` | random |
   | `ENCRYPTION_KEY` | 64 hex characters, `openssl rand -hex 32` |
   | `POSTGRES_PASSWORD` | random |
   | `CLICKHOUSE_PASSWORD` | random |
   | `REDIS_AUTH` | random |
   | `MINIO_ROOT_USER` | random |
   | `MINIO_ROOT_PASSWORD` | random |
   | `LANGFUSE_IMAGE_TAG` | `4.82.0`, so web, worker, and gateway images share one exact release |
   | `TELEMETRY_ENABLED` | `false`, so the instance sends no usage metrics |

   The `4.82.0` images resolve through `docker.langfuse.com` to Docker Hub. When a direct Docker Hub pull is blocked, pre-pull the same digests through a Docker Hub mirror and retag them as `docker.langfuse.com/langfuse/langfuse:4.82.0` and `docker.langfuse.com/langfuse/langfuse-worker:4.82.0`, then start the stack. The image digests, not only the tags, identify the release.

   Add the headless initialization variables from the Langfuse documentation so the organization, project, API keys, and first user are created on startup. This makes the setup reproducible and avoids manual clicks:

   ```bash
   LANGFUSE_INIT_ORG_ID=verifiable-tutor
   LANGFUSE_INIT_ORG_NAME=Verifiable Tutor
   LANGFUSE_INIT_PROJECT_ID=verifiable-tutor-dev
   LANGFUSE_INIT_PROJECT_NAME=verifiable-tutor dev
   LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-<random>
   LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-<random>
   LANGFUSE_INIT_USER_EMAIL=<your local admin email>
   LANGFUSE_INIT_USER_NAME=<your name>
   LANGFUSE_INIT_USER_PASSWORD=<local admin password>
   ```

   Do not double quote the headless initialization values inside the Compose `.env`.

4. Start the stack and wait for readiness. The first start pulls the images.

   ```bash
   docker compose up -d
   curl -s http://localhost:3000/api/public/health
   curl -s http://localhost:3000/api/public/ready
   ```

   The stack is ready when both endpoints report success. The documentation quotes two to three minutes after the images are present. Release 4.82.0 adds an optional `langfuse-ai-gateway` service; this project does not use the gateway, so the six tracing services can be started explicitly with `docker compose up -d postgres clickhouse redis minio langfuse-web langfuse-worker`.

5. Open `http://localhost:3000`, sign in with the headless initialization user, and confirm the project and its API keys.

## Project configuration

Only the two keys are secret; everything else is committed configuration.

`config/observability.yaml`:

```yaml
langfuse:
  enabled: true
  base_url: http://127.0.0.1:3000
  environment: local
  release: dev
  sample_rate: 1.0
```

`.env` (ignored by Git; add empty placeholders to `.env.example`):

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

The file is committed as [config/observability.yaml](../config/observability.yaml). The loader and the fail-open wrapper are in [src/verifiable_tutor/observability.py](../src/verifiable_tutor/observability.py), and `load_settings` exposes them as `AppSettings.observability`.

The SDK is an exact `dev` dependency, `langfuse==5.2.0`. The application must start and answer requests when `enabled` is false, when a key is missing, or when the instance is down. In those cases tracing is a no-op.

What is traced today: each chat turn runs the LangGraph loop with the Langfuse LangChain callback handler, so graph nodes and tool runs appear as spans, and `langfuse_session_id` and `langfuse_user_id` are set from the conversation and the internal user id. Model calls made through the OpenAI SDK in the adapter are not generation spans yet, and the trace id is not written to the answer or the JSONL record yet; both remain follow-up work on VT-15.

## Verify one trace

1. Start the backend locally with tracing enabled.
2. Send one chat request, ideally one that runs retrieval, a policy decision, and a generation.
3. In Langfuse, open Traces and confirm one trace with a `session_id` and a `user_id`, the `LangGraph` root span, and one span each for the `agent` and `tools` nodes under it. Model-call generation spans, with model, tokens, latency, and cost, do not appear yet: the adapter calls the OpenAI SDK directly, so they are a follow-up on VT-15.
4. The trace id is not written to the JSONL session record yet; that cross-reference is also a VT-15 follow-up.

## Operations

- Start: `docker compose up -d`. Stop: `docker compose down` (volumes and data are kept). Reset all trace data: `docker compose down -v`.
- Logs: `docker compose logs -f langfuse-web` and `docker compose logs -f langfuse-worker`.
- Update: `docker pull` via `docker compose pull`, then `docker compose up -d`. Minor and patch releases apply migrations on start; read the upgrade guide before a major server upgrade.
- Disk: `docker system df`. Docker's default json-file logging does not rotate; set a `max-size` in the Docker daemon logging configuration instead of truncating files by hand.
- Backup is not required for a course project. Export the traces needed for the report from the UI, or keep screenshots with the trace id visible.

## Troubleshooting

- Web UI does not answer: check `docker compose ps`, then the web and worker logs. A failed Postgres, ClickHouse, or MinIO health check blocks the web container.
- Port already in use: change only the host side of the mapping in `docker-compose.yml` and update `NEXTAUTH_URL` and `LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT` to the new port.
- Slow image pull: replace the `docker.langfuse.com` image registries with the Docker Hub mirrors `docker.io/langfuse/langfuse:4` and `docker.io/langfuse/langfuse-worker:4`.
- The application cannot reach the instance: the SDK runs on the host, so use `http://127.0.0.1:3000`, not the container name.
- A container pulls `:4` instead of the pinned release: set `LANGFUSE_IMAGE_TAG=4.82.0` in the Compose `.env` and restart the stack.
- Disk grows: remove old traces in the UI, reset with `docker compose down -v`, and check Docker's log rotation settings.

## Boundary with TACC

The TACC requirements file does not include the Langfuse SDK, and TACC jobs do not send traces. TACC evidence is JSONL, job logs, and evaluation result files. The report states which surface each figure comes from.
