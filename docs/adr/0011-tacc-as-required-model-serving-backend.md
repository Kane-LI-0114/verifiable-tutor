# ADR-0011: TACC as the required model-serving backend through job submission

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-01 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The 2026-10-30 staff clarification said the backend did not have to run on TACC and that at least one offline job using TACC results was enough. [ADR-0010](0010-tacc-as-offline-compute.md) recorded TACC as an offline compute resource, with Qwen kept as an optional baseline.

The 2026-11-01 staff email supersedes the optional part of that reading. The project must use TACC as at least one of its model-serving backends and demonstrate a working end-to-end workflow. The email also suggests deploying a text-generation model on TACC, such as the course Qwen model, and states that SSH port forwarding is not supported for the project. It suggests keeping the frontend local and reaching TACC through job submission: submit a task, wait for the result, then use it in the application ([tacc-notes.md](../tacc-notes.md#staff-clarification-2026-11-01)).

The platform constrains the shape of that serving. Compute nodes are private, there is no inbound path, tcloud has no port publishing, and every job is capped at one hour. A Qwen job pays a seven to eight minute vLLM cold start, so a job submission per chat turn cannot serve an interactive conversation. The team therefore uses Qwen on TACC as an offline text-processing backend for a course knowledge base: each build is one submitted GPU job, and its output is downloaded and used locally. The BGE-M3 index job already runs on TACC ([ADR-0004](0004-hybrid-retrieval-with-bge-m3.md)); together the two jobs make TACC a real model-serving backend without a hosted endpoint.

## Decision

- **Required TACC model serving.** TACC serves two models for the project: BGE-M3 in the index job, and Qwen in the knowledge-base enrichment job. The Qwen knowledge-base job is the required end-to-end demonstration.
- **Access path.** The frontend and backend run locally. TACC is reached only through `tcloud` job submission and the persistent `USERDIR`: the backend writes a request manifest and input JSONL into `USERDIR`, submits one GPU job, waits for it, downloads the result, validates it, and stores it in the local knowledge base. No SSH forwarding, port publishing, or inbound service is used.
- **Knowledge base.** The knowledge base is a P0 feature. Qwen reads a batch of course chunks, generates cited knowledge cards (summary, key concepts, study questions) as JSONL, and writes a progress file. The local backend records queued, running, ready, and failed states in the UI; completed builds are cached and reused.
- **One-shot job per build shard.** A build is one submitted job over one document or section shard, chosen to fit the one-hour cap. Larger corpora use sequential shards with resumable outputs. The job runs vLLM with Qwen at tensor parallel 2 and 32K context, processes the input, writes the result, and exits.
- **Qwen is not a chat backend.** Interactive text generation stays on external OpenAI-compatible APIs ([ADR-0005](0005-external-model-apis-as-primary.md)). Qwen on TACC is an offline text-processing backend; the knowledge base feeds review outlines and self-tests, and every displayed citation still passes the span verifier.
- **Evidence.** Each build records the job id, log, request and result hashes, queue and cold-start time, build time, chunk coverage, and schema validity. The demo runs one knowledge-base build end to end and uses its records in the knowledge-base view and in a review outline.
- **Failure handling.** Records are validated against the knowledge schema with one repair attempt; a failed or partial job is retried or resumed at the shard level; results are keyed by corpus hash, prompt version, and model id so a rebuild is skipped when nothing changed.
- **Privacy.** Course material for the knowledge base stays on the platform and TACC; it is not sent to an external model API.
- **Superseded in part.** [ADR-0010](0010-tacc-as-offline-compute.md) no longer describes TACC as offline-only or Qwen as optional. Its local-backend, no-inbound-service, and artifact-download decisions still stand.

## Consequences

**Positive:**
- The project satisfies the 2026-11-01 requirement with a real model-serving path on TACC and a reproducible end-to-end demo.
- No port forwarding or inbound service is needed, so the access path stays within the supported job-submission workflow.
- The knowledge base adds a durable product capability on top of the required model deployment, and its records are cached and auditable.
- The same job pattern can later serve other offline text-processing tasks without redesigning the access path.

**Negative:**
- A build pays queue time and a seven to eight minute cold start before Qwen generates anything, so the demo needs a pre-built or early-submitted job.
- The one-hour cap forces sharding and resumable output for the whole corpus.
- Qwen structured output needs schema validation and one repair path, which adds code and failure modes.
- The local backend must manage `tcloud` submission, polling, and download state, and the demo depends on the course account and cluster availability.

**Neutral:**
- `tacc/serve/` changes from an optional baseline to the required Qwen knowledge-base job.
- A local knowledge base store and a build-state table are added to the data layer.
- External APIs remain the interactive text path; Qwen is the offline enrichment path.

## Alternatives considered

**Serve Qwen for interactive chat through a job per turn.** For: the strongest reading of "model-serving backend". Against: queue time plus a seven to eight minute cold start per turn makes chat unusable, and streaming and timeouts become the dominant behaviour. Why not chosen: the staff email itself recommends the submit, wait, use pattern, and an offline text-processing job satisfies it with a usable demo.

**Use SSH forwarding to the Qwen endpoint.** For: low latency and a familiar serving pattern. Against: the 2026-11-01 email states SSH port forwarding is not supported for the project. Why not chosen: it violates the access rule.

**Batch pre-generation without UI integration.** For: the simplest implementation. Against: the result is not a working end-to-end workflow in the application; the demo would only show files. Why not chosen: it does not satisfy the end-to-end requirement.

**Rely on the embedding job alone as the model-serving backend.** For: no new text-generation work. Against: the staff email recommends deploying a text-generation model as well, and a batch index alone is a weak demonstration of model serving. Why not chosen: the Qwen knowledge-base job is the requested text-generation demonstration.

**Use only external APIs and skip TACC model serving.** For: the simplest chat path. Against: the 2026-11-01 email makes TACC model serving a requirement. Why not chosen: it fails the requirement.

## References

- Staff clarifications: [../tacc-notes.md](../tacc-notes.md#staff-clarification-2026-11-01), [../tacc-notes.md](../tacc-notes.md#staff-clarification-2026-10-30)
- Requirements: [../prd.md](../prd.md) FR-J3, FR-J5, and FR-K1 to FR-K4
- Knowledge-base records: [../knowledge-schema.md](../knowledge-schema.md)
- Job topology and the Qwen job: [../tech-selection.md](../tech-selection.md#jobs-and-demo-modes)
- Embedding model: [0004-hybrid-retrieval-with-bge-m3.md](0004-hybrid-retrieval-with-bge-m3.md)
- Interactive model APIs: [0005-external-model-apis-as-primary.md](0005-external-model-apis-as-primary.md)
- Prior TACC boundary: [0010-tacc-as-offline-compute.md](0010-tacc-as-offline-compute.md)
