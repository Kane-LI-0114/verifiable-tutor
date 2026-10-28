# TACC notes

Working notes on the course TACC platform: what the course staff allow, what the job budgets are, and what those constraints change for this repository. The authoritative platform documentation lives outside this repository (the course public environment guide and student commands, mirrored in the course workspace); this file records the clarifications we received and the operating rules derived from them. Platform workflow and hard environment constraints are summarized in [AGENTS.md](../AGENTS.md#tacc-and-model-serving), not repeated here.

## Staff clarification (2026-10-28)

Yijun Sun (course TA) answered our questions about allowed model usage and the TACC environment on 2026-10-28. The answer is broader than the course documents imply:

| Topic | Clarification | What it means here |
|---|---|---|
| Model backend | TACC and the provided Qwen model are not mandatory. External LLM APIs and external computing resources are acceptable. | The TACC service stays the primary backend for the course execution path; external LLM calls cover optional baselines only. |
| Cost | The course may not be able to reimburse external API or external compute costs. | No experiment in the submitted repository may require a paid external call. Cache every external result. |
| Packages and storage | Dependencies and model downloads may go into our own workspace. Group storage must stay within 100 GB, combined across all three members. | Install into `$HOME`, never into the read-only public environment. Budget weights, indexes, and caches against the 100 GB cap. |
| Embeddings | An embedding model may run on TACC through a submitted job. Precomputing embeddings externally and BM25-only retrieval are also acceptable. | Keep the planned hybrid index; the dense side can be produced on TACC in a short batch job. |
| OCR and vision models | These may also run on TACC through submitted jobs, or be preprocessed off-platform. | The week-one OCR decision is unconstrained. Existing course transcripts remain the low-risk fallback. |
| Resource limits | Each job may run for at most one hour. Avoid submitting many jobs repeatedly in a short period, because that can delay other students. | See the job budget and the discrepancy below. |

The reply also notes that at this stage the proposal should focus on the idea and the overall approach, with implementation details refined as the project progresses.

## Discrepancy: job time limit

The course documentation states two hours per job in two places: the public environment guide says the service job requests 2 GPUs, 8 CPUs, and 2 hours, and its `serve.slurm` template encodes that request; the TACC tutorial example uses `time=02:00:00`. The TA states that each job may run for at most one hour.

- Treat one hour as the working limit when planning, because the staff statement is the more recent and more specific instruction.
- Verify the real limit on the first service submission, since the template and the stated limit cannot both be right. Submit the service job, then read `TimeLimit` from `squeue -o '%.18i %.9P %.8j %.2t %.10M %.6l %R'` or from `scontrol show job JOB_ID | grep -E 'TimeLimit|RunTime'`.
- If the platform rejects or kills a two-hour request, set the job time to 59 minutes in our copy of the service configuration.
- Open question: whether the one-hour cap applies to every job, including the CPU client job, or only to GPU jobs.

## Job budget

- The public environment validation recorded on 2026-10-06 measured a full cold start of 12 minutes 40 seconds for the Qwen service, including first load and compile. With a one-hour cap, one service job leaves about 45 minutes of usable serving time.
- The service address (`SERVICE_BASE_URL=http://NODE:8000/v1`) changes with every job, and the client must read it from the log of the current job each time. The address stops working when the job ends.
- Evaluation must fit the usable window: split the 50-question benchmark and the ablations into batches that complete in under 45 minutes, and cache retrieval snapshots and model responses so a rerun does not need a fresh service.
- Use one service job per evaluation window instead of short repeated submissions; this respects both the one-hour cap and the fairness rule.
- The demo should have a replay mode that reads cached responses, so the presentation does not depend on a live GPU job.

## Storage budget

- 100 GB total, shared by the group rather than per account.
- The provided Qwen weights live in the read-only public path, so they are not part of our workspace usage.
- Downloads we control: embedding model weights (a few hundred MB to a couple of GB), OCR weights if adopted (allow a few GB), the retrieval index and cached responses (small), and any course PDFs and transcripts kept in the workspace (tens of MB).
- Keep model downloads outside the corpus directory ([`data/corpus/`](../data/corpus/) at the repository root). Clear job-local scratch and Hugging Face caches if they grow; the platform maps `HF_HOME` to a job-local temporary directory, so those caches do not persist anyway.

## Consequences for the plan

- No proposal change is needed: the frozen two-page [proposal](../proposal/proposal.md) already states the TACC service as primary, with external LLM and search APIs optional, labelled, and cached. The clarification confirms that text rather than invalidating it.
- Keep the repository runnable without external keys or GPU access: cached baselines, cached retrieval snapshots, and a replay path.
- The dense retrieval side needs no new packages: the public environment already ships PyTorch and Transformers, so an open embedding model can be loaded directly once its weights are downloaded to our workspace. BM25 remains the no-cost fallback and a required ablation arm.
- OCR stays optional. Existing course transcripts are already in the course workspace, so a self-run OCR job is a stretch goal, not a dependency.

## Sources

- Course staff reply from Yijun Sun, 2026-10-28, by email to LI Jinchuan, TIAN Yujia, and XIE Yifeng.
- Course public environment guide and student commands, course workspace copies outside this repository.
- TACC tutorial, `time=02:00:00` service example.
- Public environment validation record, 2026-10-06: 12 minutes 40 seconds cold start, 65.75 tokens/s single stream, 203.33 tokens/s at four concurrent requests.
