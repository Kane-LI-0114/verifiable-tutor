# ADR-0005: External model APIs as the primary text-generation backend

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

> **Superseded in part.** [ADR-0006](0006-same-model-retries-without-cross-model-fallback.md) replaces the cross-model fallback part of this decision. The rest stands. The live-verified model ids are `deepseek-flash`, `mimo-v2.6-flash`, and `mimo-v2.6-pro`; see [config/models.yaml](../../config/models.yaml).

## Context

The frozen proposal commits to the course Qwen service on TACC as the primary model backend, with external LLM and search APIs as optional baselines. Two things changed after the proposal:

- The staff clarification of 2026-10-28 says that TACC and the provided Qwen model are not mandatory, and that external LLM APIs and external computing resources are acceptable ([../tacc-notes.md](../tacc-notes.md)). It also says the course may not reimburse external API costs, so every external result must be cached.
- Text generation is the highest-latency and highest-cost step of the agent. Pinning it to a shared Qwen job means every iteration waits on a queue, a 12 minute 40 second cold start, and an address that changes per job. The team wants faster iteration and a provider that can be swapped from configuration.

Two OpenAI-compatible providers are available to the team on 2026-10-29: DeepSeek at `https://api.deepseek.com/v1` with models `deepseek-flash` and `deepseek-v4-pro`, and Xiaomi MiMo at `https://api.xiaomimimo.com/v1` with models `mimo-v2.6-flash` and `mimo-v2.6-pro`. The model ids were read from the local client configuration and must be confirmed at the first live call. Embeddings stay local: BGE-M3 on TACC was already chosen in [ADR-0004](0004-hybrid-retrieval-with-bge-m3.md), and keeping them local makes retrieval reproducible and free.

## Decision

- **Primary text generation:** external OpenAI-compatible APIs through the `openai` SDK. The `chat` role points at DeepSeek `deepseek-flash`; [ADR-0006](0006-same-model-retries-without-cross-model-fallback.md) removes the earlier cross-model fallback. The `translate_query` role uses DeepSeek, and the `classify_intent` role uses MiMo. The provider mapping is configuration, not code.
- **Embeddings:** BGE-M3 runs on TACC, both in the index job and for query embedding in the backend. Embeddings are not an external API.
- **Course Qwen service:** an optional TACC baseline, not on the primary path.
- **Secrets:** only API keys live in `.env` at the repository root, which Git ignores. The committed [.env.example](../../.env.example) is the template.
- **Provider settings:** endpoints, model ids, role routing, request parameters, retry and timeout values, the response cache, and the embedding configuration live in [config/models.yaml](../../config/models.yaml). That file is committed and contains no secrets.
- **Caching and attribution:** every external call is labelled with provider, model, parameters, and latency, and cached by provider, model, parameters, and messages. No experiment in the submitted repository may require a paid call at rerun time.
- **Loader:** the config is read through a typed loader that resolves `api_key_env` from the environment and fails closed when a key or provider entry is missing. The loader and its tests land with the first code change.

## Consequences

**Positive:**
- No GPU job is needed for text generation; iteration no longer waits on the TACC queue or the Qwen cold start.
- Providers and model ids are configuration, so a failure or a better model is a config edit rather than a code change.
- API keys stay out of Git, and the committed configuration stays reviewable.
- Retrieval remains free and reproducible because embeddings are local and cached.

**Negative:**
- The system now depends on two external providers for its most important step; an outage or a key problem stops generation unless the fallback is healthy.
- The course does not reimburse external calls, so evaluation must run from cache and the paid-call budget must stay small; a careless benchmark run costs money.
- Provider model ids and behaviour change over time, so the report and the cache key must record the exact provider and model.
- Course material excerpts leave the platform as prompts to a third party. This is acceptable for a course project with public course material, but it must be stated in the report.
- The frozen proposal names the Qwen service as primary. The report must explain this deviation and keep the TACC jobs for evaluation evidence.
- A local demo needs an embedding path: either BGE-M3 loaded on the laptop or a cache of query vectors; this is still to be decided.

**Neutral:**
- `tacc/serve` moves from a required job to an optional baseline, and the job budget shifts toward OCR and indexing.

## Alternatives considered

**Keep the Qwen service as primary.** For: exact alignment with the frozen proposal, no API cost, and a model the course has already validated and provided. Against: queue, cold start, address churn, and shared GPU contention limit iteration and demo reliability. Why not chosen: speed of iteration and independence matter more for a four-week project, and the staff clarification permits external APIs.

**Use a single external provider.** For: one endpoint, one key, and the simplest configuration. Against: no fallback when the provider has an outage or a key problem. Why not chosen: two providers were already available and the config makes the fallback cheap.

**Run text generation on a self-hosted model on TACC.** For: no external cost and no data leaving the platform. Against: the one-hour job cap, the read-only public environment, and the cold start make it the slowest path for the chat loop. Why not chosen: it reproduces the problem the team is trying to escape, and the provided Qwen service already covers the optional baseline.

**Use an external embedding API.** For: no local model to deploy. Against: cost and network dependency on every query, and BGE-M3 on TACC is already part of ADR-0004. Why not chosen: local embeddings are free, fast enough, and reproducible.

## References

- Provider configuration: [config/models.yaml](../../config/models.yaml), [.env.example](../../.env.example)
- Staff clarification and cost rule: [../tacc-notes.md](../tacc-notes.md)
- Environment strategy: [ADR-0001](0001-pinned-python-environment-without-docker.md)
- Retrieval and embedding choice: [ADR-0004](0004-hybrid-retrieval-with-bge-m3.md)
- Provider endpoints and model ids observed in the local client configuration on 2026-10-29; confirm against provider documentation at the first live call.
