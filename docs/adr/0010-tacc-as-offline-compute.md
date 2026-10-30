# ADR-0010: TACC as an offline compute resource, with the backend running locally

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-30 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The frozen proposal commits to a TACC CPU job for the agent backend and to the course Qwen service on TACC. [ADR-0005](0005-external-model-apis-as-primary.md) moved text generation to external APIs but kept the TACC CPU job as the evaluation evidence path. [tech-selection.md](../tech-selection.md#where-the-backend-runs) recorded the hosting question as open and planned two demo modes: a local backend and a TACC-hosted backend reached through an SSH forward.

The project brief does not state where the backend must run. On 2026-10-29 we emailed the TA two follow-up questions: whether SSH forwarding to a student-run web port is allowed, and whether the final demo must run the backend on TACC. The answer arrived on 2026-10-30: the backend does not have to be deployed on TACC. The requirement is at least one offline job that uses TACC results. The examples given are OCR parsing and embedding of document chunks: TACC produces them, the results are stored locally, and the delivered system reads them. TACC is an offline compute resource, and no online service is deployed there ([tacc-notes.md](../tacc-notes.md#staff-clarification-2026-10-30)).

The platform facts point the same way. Compute nodes are private with no inbound path from a laptop, tcloud has no port publishing, the course documents support only the model-service SSH forward and contain a general sentence against student-run forwarding, and every job is capped at one hour. A TACC-hosted backend would add queue time, a per-job address, a tunnel, and an authorization risk to every demo, for a deployment the course does not require.

The project still needs real TACC compute in the deliverable: the corpus OCR, the index and embeddings, the self-test execution, and the evaluation evidence. Those are batch jobs whose outputs are files, so they fit the offline model exactly.

## Decision

- **Delivered topology.** The FastAPI backend, the React UI, SQLite, the JSONL traces, the model adapter, and the LangGraph graph run on the developer laptop. The local backend is the delivered mode, not a fallback, and it is the mode the demo and the report use.
- **TACC usage.** TACC appears only through submitted batch jobs: `tacc/ocr/`, `tacc/index/`, `tacc/exec/`, `tacc/client/` for the evaluation harness, the committed `tacc/pdf-parse/` prototype for a single PDF, and an optional `tacc/serve/` baseline generation job. Each job exits when it finishes. An on-demand submission during a demo, such as one PDF parse or one code-answer execution, is still a batch job, not a service. No job serves the product, and no job port is reached from outside the cluster.
- **Artifacts, not services.** Every TACC job writes its output to `USERDIR`, and the output is downloaded into the local mirror: `data/corpus/`, `data/index/`, `data/caches/`, and `benchmarks/results/`. The backend reads only the local mirror, so the demo and the evaluation work with no TACC job running.
- **Required course evidence.** The OCR and index jobs are the offline pipeline that satisfies the clarification: TACC parses the corpus and computes the embedding vectors, and the results are stored locally. The report cites the job ids, logs, and artifact hashes.
- **Query embedding.** Query embedding runs on the laptop, with a local BGE-M3 copy or cached query vectors. Batch index embedding runs on a TACC GPU job ([ADR-0004](0004-hybrid-retrieval-with-bge-m3.md)).
- **Per-request execution.** Self-test code answers still use `tacc/exec/` because the course MPI toolchain lives on TACC. The local backend submits one batch job, polls it, and downloads the results. This is batch compute submitted on demand, not a hosted service. If the queue makes the demo unreliable, precomputed reference results and the local restricted runner are the fallback.
- **Optional Qwen baseline.** The Qwen baseline is generated inside one GPU batch job and written to `USERDIR`. No endpoint is exposed, so the course Qwen model is used as offline compute rather than as a deployed service.
- **Dropped.** The TACC-hosted demo mode, the SSH web-port forward, and the tunnel spike are removed. The web-port forwarding question is moot.
- **Proposal deviation.** The proposal's TACC CPU backend commitment is not delivered as written. The report explains the deviation and records the TACC compute that was actually used.

## Consequences

**Positive:**
- The demo no longer depends on queue time, a job address, a tunnel, or an authorization answer. It runs from the laptop with mirrored artifacts.
- The course TACC requirement is met with durable, downloadable evidence: job ids, logs, OCR records, embeddings, execution results, and evaluation JSON.
- The local backend keeps iteration fast and every run reproducible; the same code serves development, demo, and replay.
- No service is exposed on the cluster, which removes the forwarding policy conflict and the security surface.

**Negative:**
- GPU work is still queue-bound: the corpus, index, and baseline jobs wait for node availability and each must fit one hour.
- The laptop must carry a BGE-M3 query-embedding path; a local model copy or cached vectors add setup and disk use.
- The per-request `tacc/exec` path keeps a queue-dependent step in the demo, and the report must measure its latency.
- The delivered topology deviates from the frozen proposal's TACC CPU job and Qwen-service primaries, so the report has one more deviation to explain.

**Neutral:**
- `tacc/client/` changes from an agent backend and UI job to an offline evaluation harness job.
- The TACC inventory is four planned batch jobs plus the committed parse prototype and one optional baseline job, with no serving role.

## Alternatives considered

**Keep the TACC-hosted backend and UI as the primary mode.** For: it matches the proposal's execution path and needs no CORS. Against: queue, one-hour job lifetime, a changing node address, an SSH tunnel through a policy the course does not settle, and no requirement from the course. Why not chosen: the clarification removes the need, and the risk would be carried by every demo.

**Use only the offline OCR and drop every other TACC call.** For: the smallest TACC surface. Against: the self-test execution evidence and the evaluation job would move off TACC, which weakens the course requirement and the proposal's tooling story. Why not chosen: the requirement is a minimum, and the batch jobs are compatible with it.

**No TACC use at all.** For: the simplest local system. Against: the course requires at least one offline TACC job, so this fails the requirement. Why not chosen: the OCR and index jobs are already the pipeline.

**Move everything to TACC, including the demo backend.** For: one host and one story. Against: the one-hour cap, the queue, the private nodes, and the forwarding conflict. Why not chosen: it is the risk this decision removes.

## References

- Staff clarifications: [../tacc-notes.md](../tacc-notes.md#staff-clarification-2026-10-30), [../tacc-notes.md](../tacc-notes.md#staff-clarification-2026-10-28)
- Hosting analysis and job topology: [../tech-selection.md](../tech-selection.md#where-the-backend-runs), [../tech-selection.md](../tech-selection.md#jobs-and-demo-modes)
- Requirements: [../prd.md](../prd.md)
- External model APIs and retry behavior: [0005-external-model-apis-as-primary.md](0005-external-model-apis-as-primary.md), [0006-same-model-retries-without-cross-model-fallback.md](0006-same-model-retries-without-cross-model-fallback.md)
- Embedding and index build: [0004-hybrid-retrieval-with-bge-m3.md](0004-hybrid-retrieval-with-bge-m3.md)
- Typed tools and the restricted runner: [0009-typed-agent-tools-instead-of-a-shell.md](0009-typed-agent-tools-instead-of-a-shell.md)
- Platform notes and access facts: [../tacc-notes.md](../tacc-notes.md#access-from-outside-2026-10-28)
