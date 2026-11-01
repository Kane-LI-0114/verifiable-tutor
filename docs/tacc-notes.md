# TACC notes

Working notes on the course TACC platform: what the course staff allow, what the job budgets are, and what those constraints change for this repository. The authoritative platform documentation lives outside this repository (the course public environment guide and student commands, mirrored in the course workspace); this file records the clarifications we received and the operating rules derived from them. Platform workflow and hard environment constraints are summarized in [AGENTS.md](../AGENTS.md#tacc-and-model-serving), not repeated here.

## Staff clarification (2026-10-28)

Yijun Sun (course TA) answered our questions about allowed model usage and the TACC environment on 2026-10-28. The answer is broader than the course documents imply:

| Topic | Clarification | What it means here |
|---|---|---|
| Model backend | TACC and the provided Qwen model are not mandatory. External LLM APIs and external computing resources are acceptable. | External APIs are allowed and are the primary interactive text path. The TACC Qwen service was initially kept as an optional baseline; the 2026-11-01 email makes it a required offline knowledge-base backend ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)). |
| Cost | The course may not be able to reimburse external API or external compute costs. | No experiment in the submitted repository may require a paid external call. Cache every external result. |
| Packages and storage | Dependencies and model downloads may go into our own workspace. Group storage must stay within 100 GB, combined across all three members. | Install into `$HOME`, never into the read-only public environment. Budget weights, indexes, and caches against the 100 GB cap. |
| Embeddings | An embedding model may run on TACC through a submitted job. Precomputing embeddings externally and BM25-only retrieval are also acceptable. | Keep the planned hybrid index; the dense side can be produced on TACC in a short batch job. |
| OCR and vision models | These may also run on TACC through submitted jobs, or be preprocessed off-platform. | The week-one OCR decision is unconstrained. Existing course transcripts remain the low-risk fallback. |
| Resource limits | Each job may run for at most one hour. Avoid submitting many jobs repeatedly in a short period, because that can delay other students. | See the job budget and the discrepancy below. |

The reply also notes that at this stage the proposal should focus on the idea and the overall approach, with implementation details refined as the project progresses.

## Staff clarification (2026-10-30)

The follow-up questions sent to the TA by email on 2026-10-29 were answered on 2026-10-30: whether the final demo must run the backend on TACC, and whether SSH forwarding may reach a student-run web port. The same reply corrected the proposal deadline to Sunday 2026-11-01; the course brief lists Thursday 2026-10-29. The reply, reported by the project lead:

| Topic | Clarification | What it means here |
|---|---|---|
| Backend hosting | The backend does not have to be deployed on TACC. | The backend, UI, and stores run locally, and no TACC-hosted mode is built ([ADR-0010](adr/0010-tacc-as-offline-compute.md)). |
| Required TACC use | At least one offline job must use TACC results. The examples are OCR parsing and embedding of document chunks: TACC produces the results, they are stored locally, and the delivered system reads them. | The OCR and index jobs are the required offline pipeline; their outputs are mirrored under `data/corpus/` and `data/index/`; the report cites the job ids and logs. |
| Online services | TACC is used as an offline compute resource, and no online service is deployed there. | Every TACC job writes files and exits. The TACC-hosted backend, the SSH web-port forward, and the tunnel spike are dropped. |
| Proposal deadline | The proposal is due Sunday 2026-11-01, not Thursday 2026-10-29 as the course brief lists. | Proposal v3 (dated 2026-11-01) is submitted before the Sunday deadline; the PRD records the key date. |

The 2026-11-01 email below supersedes the "required TACC use" and "online services" rows; the backend-hosting and deadline rows still stand. The 2026-10-28 clarification remains valid for model usage, cost, packages, storage, embeddings, OCR, and resource limits.

## Staff clarification (2026-11-01)

A second staff email on 2026-11-01 supersedes the optional reading of the 2026-10-30 answer:

| Topic | Clarification | What it means here |
|---|---|---|
| Model serving | The project must use TACC as at least one of its model-serving backends and demonstrate a working end-to-end workflow. | TACC runs the BGE-M3 index job and a required Qwen knowledge-base enrichment job; one build is demonstrated end to end ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)). |
| Text generation on TACC | The staff suggest also deploying a text-generation model on TACC, such as the course Qwen model. | Qwen runs as an offline text-processing backend for the knowledge base; it is not used for interactive chat, because a job-per-turn cold start is unusable ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)). |
| SSH forwarding | SSH port forwarding is not supported for the project. | No tunnel or forwarded port is used; all TACC access is job submission ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)). |
| Access pattern | Keep the frontend local and access TACC through job submission: submit a task, wait for the result, then use it in the application. | The local backend writes requests to `USERDIR`, submits a job, waits, downloads and validates the result, and uses it locally. |

The 2026-10-30 backend-hosting and deadline rows still stand. Its "required TACC use" and "online services" rows are superseded by this email.

## Discrepancy: job time limit

The course documentation states two hours per job in two places: the public environment guide says the service job requests 2 GPUs, 8 CPUs, and 2 hours, and its `serve.slurm` template encodes that request; the TACC tutorial example uses `time=02:00:00`. The TA states that each job may run for at most one hour.

- Treat one hour as the working limit when planning, because the staff statement is the more recent and more specific instruction.
- Measured on 2026-10-28: `sinfo` reports `TIMELIMIT 1:00:00` for the `tacc` partition and `scontrol show partition tacc` reports `MaxTime=01:00:00`, so the scheduler enforces one hour. The course templates' two-hour requests are stale and should be rejected.
- Set the job time to 59 minutes in every task configuration, including CPU jobs; the partition limit applies to all jobs in it, which closes the earlier open question about GPU-only limits.
- The first real submission still tells us how a two-hour request is rejected, but no planning decision depends on it any more.

## Platform mechanics (2026-10-28)

Facts below were read from the tcloud SDK 0.4.1 source, the live cluster configuration on the SDK client, and the course documentation. They are not staff statements; the staff clarifications above remain the authority on budgets and policy.

- **Custom images are not supported.** The SDK job schema has no image, container, or registry field: `tuxiv.conf` accepts an entrypoint, a conda environment, Slurm job settings, and datasets only. The generated launcher always activates a conda environment. Jobs do run inside containers, but the platform chooses the image. The Dockerfile in the assignment 2 materials is an optional local development recipe and is never used by the TACC path.
- **The submit directory is capped at 1 GiB.** The cluster configuration reports `storagequota: 1024`, in MB. Before upload the SDK walks the local task tree and refuses oversized trees; every submit then mirrors the tree with `rsync --delete`. Keep task directories to code only.
- **`USERDIR` is the persistent channel for data.** `tcloud upload` writes into `USERDIR`, is incremental, and is not subject to the submit cap. `TACC_WORKDIR` is re-synchronised on every submit and may be removed after the job. `$HOME` is persistent and is where installed environments and model weights belong.
- **Use one entrypoint item.** Multiple `entrypoint` entries are joined into a single command line, not run in sequence. Every job directory uses one script.
- **The SDK conda environment is old and empty by design.** The platform personal Miniconda is 4.9.2 on Python 3.8.5, and the course registers an empty proxy environment. Adding conda dependencies to `tuxiv.conf` is supported by the schema but unverified for this account and is not the primary dependency strategy (see [ADR-0001](adr/0001-pinned-python-environment-without-docker.md)).
- **Guard the shell before activating conda.** Scripts that run with `set -u` and source the conda profile need `export PS1="${PS1:-}"` first; a previous assignment job failed on an unbound `PS1`.
- **The scheduler enforces the one-hour limit.** On 2026-10-28 `sinfo` reported `TIMELIMIT 1:00:00` for the `tacc` partition and `scontrol show partition tacc` reported `MaxTime=01:00:00`. Use `time=00:59:00` in every `tuxiv.conf`; a two-hour request should be rejected. The course templates still show `02:00:00` and are stale for this partition.
- **Measured hardware.** Compute nodes have 2x RTX 3090 with 24 GB each; the driver measured in job 27790 was 560.35.05 (CUDA 12.6), while the job container ships nvcc 11.0. The public environment's PyTorch 2.11.0+cu128 works on this driver; do not assume the container nvcc for Python work.
- **Network egress is open** from the login node and compute nodes, and Hugging Face downloads go through `https://hf-mirror.com`.

## Access from outside (2026-10-28)

Updated 2026-11-01: the project does not use SSH port forwarding; all access is job submission.

- **Compute nodes are private.** The observed node address is RFC1918 (`10.0.1.0/24`, with `10.0.0.0/8` routed), and login and compute nodes share one NAT egress address. There is no direct inbound path from a laptop, and tcloud 0.4.1 has no port-publishing or ingress command.
- **SSH local forwarding is not supported for the project.** The 2026-11-01 email settles the question: no tunnel or forwarded port is used. Probes on 2026-10-28 showed that `gw.turing.ust.hk:30041` accepts `-L` forwards to arbitrary cluster addresses and ports, and the login node routes into `10.0.0.0/16`; the project does not use them, and all TACC access is job submission ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).
- **Historical command shape, not used:** `ssh -p 30041 -i <private key> -N -L 127.0.0.1:<local port>:<node>:<remote port> <user>@gw.turing.ust.hk`, then open `http://127.0.0.1:<local port>/`. It is recorded only to document what the platform technically allows; the project does not forward ports.
- **No document addresses forwarding to a student-run web port directly.** The general wording and the model-service wording conflict, and no sentence either permits or forbids the web-port use case by name. Exact wording:
  - "SDK 内部使用 SSH 协议和 Slurm；学生不登录平台服务器，也不自行建立 SSH 转发。" (student commands, file and environment section)
  - "离开平台的本地客户端需要通过该账号可用的 SSH 入口转发到 NODE:8000；登录和密钥使用本人已配置的账号。" (service commands, client section)
  - "个人电脑默认通过 SDK 提交客户端程序到平台调用；如果需要从校外电脑直接访问 HTTP 服务，请使用平台明确提供或批准的访问入口。" (student commands, service section)
  - "All users cannot ssh to our server. If you have special needs, please feel free to contact us." (tcloud quickstart FAQ, item 4)
  - Term of Service usage rules: "Do not run any application that performs a security intrusion", "Do not run any application that could be interpreted as a privacy violation", "Do not hold TACC resources when they are not actively used", "Do not access resources that are not allocated to you", "Do not make hacking attempts to the TACC infrastructure". Violations can lead to account disabling, notifying the supervisor, or legal action.
  - Reading: the model-service forward has specific textual support; forwarding to our own web port has none. The 2026-11-01 email makes the policy explicit: SSH forwarding is not supported for the project.
- **Capability versus permission.** The SSH plumbing works, but the 2026-11-01 clarification does not permit SSH forwarding for the project. The delivered system does not use it; the facts above are historical and are not a design path ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md), [tech-selection.md](tech-selection.md#jobs-and-demo-modes)).
- **No per-job public URL was found.** The web console shows job history and status; the platform's HAProxy port-exposure mechanism for Jupyter-style access is not documented for student jobs through the course SDK.
- **Capacity is tight.** Measured on 2026-10-28: 10 nodes, `MaxNodes=2`, 20 CPUs per node, 2 GPUs per node, with 0 idle, 6 drain, 4 down, and 3 jobs pending from another account. Queueing, not concurrency, is the demo risk; keep replay ready and submit batch jobs early.

Sources for this section: SDK source `userconfig.go` and `tcloudcli.go`; `sinfo` and `scontrol` output read from the login node on 2026-10-28; tcloud quickstart FAQ and TOS; platform architecture paper arXiv 2110.01556, sections 3.2, 5.2, and 7.

## Job budget

- The public environment validation recorded on 2026-10-06 measured a full cold start of 12 minutes 40 seconds for the Qwen service, including first load and compile. With a one-hour cap, one service job leaves about 45 minutes of usable serving time.
- The course-provided service address (`SERVICE_BASE_URL=http://NODE:8000/v1`) changes with every job and is not used by the project: SSH forwarding is not supported, so the project runs Qwen inside its own submitted job ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).
- Evaluation must fit the usable window: split the 50-question benchmark and the ablations into batches that complete in under 45 minutes, and cache retrieval snapshots and model responses so a rerun does not need a fresh service.
- Use one Qwen knowledge-base job per document shard instead of short repeated submissions; this respects both the one-hour cap and the fairness rule.
- The Qwen knowledge-base job pays the full vLLM cold start (438 to 495 s) before generation; shard by document, keep records resumable, and pre-build the demo knowledge base.
- The demo has a replay mode that reads cached responses, so the presentation does not depend on a live model or a queued job. The demo mode is settled by the 2026-11-01 requirement: the backend and UI run locally, and TACC is a required model-serving backend reached through job submission ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).

## Storage budget

- 100 GB total, shared by the group rather than per account.
- The provided Qwen weights live in the read-only public path, so they are not part of our workspace usage.
- Downloads we control: the OCR model (about 2 GB), the embedding model (about 2.3 GB fp32), page images and OCR output (a few hundred MB), the retrieval index and cached responses (small), and any course PDFs kept in the workspace (about 58 MB). The chosen models are recorded in [tech-selection.md](tech-selection.md).
- Keep model downloads outside the corpus directory ([`data/corpus/`](../data/corpus/) at the repository root). Clear job-local scratch and Hugging Face caches if they grow; the platform maps `HF_HOME` to a job-local temporary directory, so those caches do not persist anyway.

## Consequences for the plan

- The proposal is revised: v1 (2026-10-27) stays the submitted artifact, v2 (2026-10-30) is a previous draft, and v3 (2026-11-01) records the required TACC model-serving backend and the knowledge base; v3 is submitted before the Sunday deadline. The course brief lists Thursday 2026-10-29, which the TA corrected.
- The delivered topology runs the backend locally and uses two TACC model-serving jobs, the BGE-M3 index job and the Qwen knowledge-base job, both reached by job submission; v3 records this ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md), [ADR-0005](adr/0005-external-model-apis-as-primary.md)).
- The course TACC requirement is met by the BGE-M3 index job and the Qwen knowledge-base job; one build is demonstrated end to end, and the report cites the job ids, logs, timings, and record hashes ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)).
- The knowledge base is a P0 feature: one build is one submitted GPU job per document shard, its records validate against [knowledge-schema.md](knowledge-schema.md), and the demo uses them in a review outline.
- Keep the repository runnable without external keys or GPU access: cached baselines, cached retrieval snapshots, and a replay path.
- The dense retrieval side needs no new packages: the public environment already ships PyTorch and Transformers, so an open embedding model can be loaded directly once its weights are downloaded to our workspace. BM25 remains the no-cost fallback and a required ablation arm.
- The OCR job is now part of the plan, not a stretch goal: the corpus is produced by a TACC OCR job whose model and output contract are recorded in [tech-selection.md](tech-selection.md) and [ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md). The existing transcripts are only a human quality reference.
- Dependency installation follows the pinned project layer described in [ADR-0001](adr/0001-pinned-python-environment-without-docker.md): a cached install under `$HOME`, never a modification of the read-only public environment.

## Verification spike results (2026-10-29)

The two week-one spikes ran on 2026-10-29: the CPU mechanics job (27872) and the GPU OCR smoke job (27879). Both passed every exit criterion. Raw artifacts are in `USERDIR/env-spike/` and `USERDIR/ocr-smoke/`; the scripts are [tacc/env-spike/](../tacc/env-spike/) and [tacc/ocr-smoke/](../tacc/ocr-smoke/).

### Cluster availability

- From 2026-10-28 18:11 to 2026-10-29 17:17 HKT the whole `tacc` partition was unschedulable: `sinfo` reported 0 idle, 6 nodes `drain*` and 4 `down*`, where the asterisk means not responding to the controller. Seven jobs from four accounts stayed queued for the entire window and none started.
- Two nodes returned at 17:17 HKT and ran both spike jobs at once, on 10-0-3-10 and 10-0-3-11.
- Consequence: the demo and the evaluation windows must tolerate a queue outage of a day or more. Submit early, keep replay ready, and never assume a node on demand.

### Node and job envelope

- `scontrol show job` accepted `time=00:59:00`; the partition reports `MaxTime=01:00:00` and jobs observe `TimeLimit=00:59:00`.
- A `cpus-per-task=4` request was reported as `NumCPUs=20` and `TRES=cpu=20`, so the job effectively holds the whole 20 CPU node. Node RAM is 251 GB.
- `/mnt/home` is 7.3 TB with about 8 percent used. The container overlay is 916 GB and was 88 to 92 percent used, leaving 75 to 113 GB of job-local scratch.
- PRoot userland: 286 MB unpacked, Ubuntu 22.04.5, kernel 5.4.0-150-generic, glibc 2.35. Versions confirmed inside it: Python 3.12.14, vLLM 0.26.0, PyTorch 2.11.0+cu128, Transformers 5.10.4.
- MPI toolchain: `/mnt/home/public/course-envs/CSIT6000V/assignment1/mpi-gemm-v1/bin/` provides gcc, mpicc, mpiexec and make; a compile and `mpiexec -n 2` hello world succeed in a job.
- GPUs are 2x RTX 3090 per node. Drivers 560.35.05 and 530.30.02 both ran vLLM successfully.

### Project environment bootstrap

- The first install of [requirements-tacc.txt](../scripts/tacc/requirements-tacc.txt) with `uv pip install --target` took 1957 s (32.6 minutes) for 105 distributions and 1.4 GB. Most of that time was PyPI retries (the paddlex wheel failed several times) plus writing many small files to NFS.
- A second bootstrap call in the same job took 32 ms, and the OCR job then started with a cache hit and 0 s of install time. The cache key was `991ab0a1a749-1c681929e3bd-r1`.
- Imports after install: pypdfium2 5.6.0, pytest 9.0.3, paddlepaddle 3.2.1 (CPU, no CUDA), paddleocr 3.7.0, paddlex 3.7.2, opencv 4.10.0. `paddle`, `paddleocr`, `cv2` and `pypdfium2` all import under PRoot.
- `cv2` needed the headless overlay: the mandated `opencv-contrib-python` wheel links libGL, which the userland lacks. The bootstrap detects the failed import and replaces the package with `opencv-python-headless` 4.10.0.84.
- SQLite 3.53.1 in the public interpreter has FTS5 enabled; creating an FTS5 table, inserting rows and ordering by `bm25` works.
- pypdfium2 renders a 16:9 slide at 200 DPI to 2667x1500 in 0.6 to 1.1 s inside PRoot.
- `PaddleOCRVL` exposes 29 constructor parameters. `pipeline_version` defaults to `v1.6`, and the server-mode parameters (`vl_rec_backend`, `vl_rec_server_url`, `vl_rec_api_model_name`, `vl_rec_max_concurrency`, `layout_detection_model_name`, `layout_detection_model_dir`) are present.
- Weights: `PaddleOCR-VL-1.6` is 1.8 GB (1917 MB of safetensors) and `PP-DocLayoutV2` is 212 MB. `hf download` against the HF mirror is unreliable inside PRoot (TLS certificate verification errors and stalls), while the PaddleX download path through modelscope worked and fetched PP-DocLayoutV2 into `$HOME/models/paddlex/official_models/` in about 110 s.
- Layout detection on CPU works: PP-DocLayoutV2 found 5 blocks on a rendered Lecture 1 page (paragraph_title, text, footer_image, footer) with plausible pixel boxes.

### OCR smoke

- vLLM 0.26.0 serves the local PaddleOCR-VL-1.6 checkpoint with `--trust-remote-code --served-model-name PaddleOCR-VL-1.6-0.9B --max-model-len 32768`. `/v1/models` returns that id, and the loader reports 1.82 GiB of weights in 32.6 s. Startup to a healthy `/health` took 281 s at `--gpu-memory-utilization 0.85` and 354 s at 0.90, because torch.compile and CUDA graph capture run in the job-local cache on every job.
- Peak GPU memory was 22,913 MiB at 0.85 and 24,009 MiB at 0.90 of 24,576 MiB, so 0.85 is the safer setting.
- A single page request through the OpenAI endpoint returned 457 characters in 2.4 to 3.4 s (1,235 prompt tokens and 105 completion tokens).
- The full pipeline ran 10 selected pages with PP-DocLayoutV2 on CPU and recognition on the server: 171 blocks, 10,776 characters, page markdown for 10 of 10 pages, and zero bbox, label or reading-order validation problems. The table page produced a `table` block, the formula pages `display_formula` blocks, and the two image-only Tutorial PDFs, which have no text layer, produced 910 and 1,698 characters.
- Per-page time had a median of 4.26 s. The first page took 25.7 s (layout model load and cold requests), and the remaining pages took 3.5 to 4.6 s. Render contributed 0.575 s per page.
- Projection including setup: 342 pages take about 1,934 s (32 minutes), so one 59-minute corpus job covers the corpus with margin. Keep the resumable design anyway.
- The whole OCR job body (bootstrap cache hit, render, server start, probe, 10 pages, teardown) took 421 s.

### Whole-document PDF parse

- Job 27884 parsed one complete file, `course_project.pdf` (584,562 bytes, sha256 `1bf2e7a6dc194cce...`), with no page preselection: copy the file in, enumerate 8 pages, render each at 200 DPI, serve the model, parse every page, assemble one document.
- All 8 pages enumerated and rendered; vLLM startup was 284 s; the first-page recognition probe returned the project title in 2.2 s.
- All 8 pages parsed in 121 blocks and 8,430 characters at a median 3.905 s per page, with no bbox, label or ordering problems.
- The assembled markdown `document/course_project-ocr.md` is 10,003 bytes with 8 `<!-- page: N -->` markers. The whole job body took 414 s, so a single small PDF fits comfortably inside one hour; a large PDF should still use the per-document sharding from the corpus design.
- This is the path the demo needs: a user supplies one PDF, the TACC OCR model parses the whole file, and the backend receives per-page records plus one document markdown. No corpus pre-parse is required.
- Known follow-up: the PaddleX page markdown can reference exported `imgs/...` crops that the job does not write. The citation panel should use the page WebP and block boxes, and the assembler can strip those image references when the UI does not need them.

### Parse request interface (local to TACC)

`scripts/tacc/parse_pdf.py` is the local interface: it uploads a PDF, generates a per-request task directory, submits `tacc/pdf-parse`, polls to completion, downloads the artifacts, and prints one JSON result. Two round trips were run on 2026-10-29.

- Job 27887, first attempt: the request asked for pages 1 to 3 but the page subset did not reach the job, so it parsed all 8 pages of `course_project.pdf`: 121 blocks, 8,430 characters, median 6.355 s per page, vLLM startup 495 s, job elapsed 707 s, VRAM peak 21,999 MiB. The interface still returned the full artifact set (document markdown, page JSONL, summary, log), so the transport and return path worked.
- Job 27889, after the fix: pages 1 to 3 requested and returned. 3 pages, 52 blocks, 1,586 characters, median 4.291 s per page, vLLM startup 438 s, interface wall time about 9 minutes including upload and download. Page subsetting now works end to end.
- Timing structure: model startup dominates every request (438 to 495 s, roughly 70 percent of the job), so dropping from 8 pages to 3 pages saves only about 30 to 40 s of parse time. For a short demo, either start the OCR service job about 10 minutes early and keep requests inside its one-hour window, or accept a roughly 9 to 10 minute per-request round trip. A persistent service plus a light client job is the next step if demo latency must be lower.
- The interface is local-only today: the demo backend can call it or wrap it, and it writes requests and results under `data/caches/parse-requests/` and `data/caches/parse-results/`, both gitignored. Record fields are in [corpus-schema.md](corpus-schema.md).

## Sources

- Course staff reply from Yijun Sun, 2026-10-28, by email to LI Jinchuan, TIAN Yujia, and XIE Yifeng.
- Course staff reply of 2026-10-30 on backend hosting, offline TACC use, and the proposal deadline (Sunday 2026-11-01), reported by the project lead after the 2026-10-29 follow-up email.
- Course staff email of 2026-11-01 on the required TACC model-serving backend, the suggested Qwen text-generation deployment, and the SSH-forwarding prohibition, reported by the project lead.
- Course project brief, Topic Selection and Proposal (course brief lists the proposal due October 29, 2026), course workspace copy outside this repository.
- Course public environment guide and student commands, course workspace copies outside this repository.
- TACC tutorial, `time=02:00:00` service example.
- Public environment validation record, 2026-10-06: 12 minutes 40 seconds cold start, 65.75 tokens/s single stream, 203.33 tokens/s at four concurrent requests.
- tcloud SDK 0.4.1 job schema: https://github.com/turingaicloud/tcloud-sdk/blob/master/cli/tcloudcli/tuxivconfig.go
- tcloud quickstart configuration guide and FAQ: https://github.com/turingaicloud/quickstart
- SDK client cluster configuration, `~/.tcloud/.clusterconfig`, read on 2026-10-28.
- Spike jobs 27872, 27879 and 27884, 2026-10-29: Slurm logs in `USERDIR/slurm_log/`, summaries and JSONL in `USERDIR/env-spike/`, `USERDIR/ocr-smoke/` and `USERDIR/pdf-parse/`.
- Parse request round trips 27887 and 27889, 2026-10-29: requests under `USERDIR/parse-requests/<request-id>/`, logs in `USERDIR/slurm_log/vt-parse-<request-id>-*.log`, local copies under the gitignored `data/caches/`.
