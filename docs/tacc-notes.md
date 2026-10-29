# TACC notes

Working notes on the course TACC platform: what the course staff allow, what the job budgets are, and what those constraints change for this repository. The authoritative platform documentation lives outside this repository (the course public environment guide and student commands, mirrored in the course workspace); this file records the clarifications we received and the operating rules derived from them. Platform workflow and hard environment constraints are summarized in [AGENTS.md](../AGENTS.md#tacc-and-model-serving), not repeated here.

## Staff clarification (2026-10-28)

Yijun Sun (course TA) answered our questions about allowed model usage and the TACC environment on 2026-10-28. The answer is broader than the course documents imply:

| Topic | Clarification | What it means here |
|---|---|---|
| Model backend | TACC and the provided Qwen model are not mandatory. External LLM APIs and external computing resources are acceptable. | External APIs are allowed and are now the primary text path; the TACC Qwen service stays as an optional baseline ([ADR-0005](adr/0005-external-model-apis-as-primary.md)). |
| Cost | The course may not be able to reimburse external API or external compute costs. | No experiment in the submitted repository may require a paid external call. Cache every external result. |
| Packages and storage | Dependencies and model downloads may go into our own workspace. Group storage must stay within 100 GB, combined across all three members. | Install into `$HOME`, never into the read-only public environment. Budget weights, indexes, and caches against the 100 GB cap. |
| Embeddings | An embedding model may run on TACC through a submitted job. Precomputing embeddings externally and BM25-only retrieval are also acceptable. | Keep the planned hybrid index; the dense side can be produced on TACC in a short batch job. |
| OCR and vision models | These may also run on TACC through submitted jobs, or be preprocessed off-platform. | The week-one OCR decision is unconstrained. Existing course transcripts remain the low-risk fallback. |
| Resource limits | Each job may run for at most one hour. Avoid submitting many jobs repeatedly in a short period, because that can delay other students. | See the job budget and the discrepancy below. |

The reply also notes that at this stage the proposal should focus on the idea and the overall approach, with implementation details refined as the project progresses.

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

- **Compute nodes are private.** The observed node address is RFC1918 (`10.0.1.0/24`, with `10.0.0.0/8` routed), and login and compute nodes share one NAT egress address. There is no direct inbound path from a laptop, and tcloud 0.4.1 has no port-publishing or ingress command.
- **The reachable path is an SSH local forward through the account's SSH entry.** The documented off-platform path forwards to `NODE:8000` through the account's SSH entry. Probes on 2026-10-28 showed that `gw.turing.ust.hk:30041` accepts `-L` forwards to arbitrary cluster addresses and arbitrary target ports, and the login node routes into `10.0.0.0/16`. Gateway to job-container port reachability is still unverified and is the critical item in the tunnel spike.
- **Command shape:** `ssh -p 30041 -i <private key> -N -L 127.0.0.1:<local port>:<node>:<remote port> <user>@gw.turing.ust.hk`, then open `http://127.0.0.1:<local port>/`. Target the node address or the dashed node name, never the gateway's own localhost. Use `ExitOnForwardFailure` and `ServerAliveInterval` to make a dead tunnel visible.
- **No document addresses forwarding to a student-run web port directly.** The general wording and the model-service wording conflict, and no sentence either permits or forbids the web-port use case by name. Exact wording:
  - "SDK 内部使用 SSH 协议和 Slurm；学生不登录平台服务器，也不自行建立 SSH 转发。" (student commands, file and environment section)
  - "离开平台的本地客户端需要通过该账号可用的 SSH 入口转发到 NODE:8000；登录和密钥使用本人已配置的账号。" (service commands, client section)
  - "个人电脑默认通过 SDK 提交客户端程序到平台调用；如果需要从校外电脑直接访问 HTTP 服务，请使用平台明确提供或批准的访问入口。" (student commands, service section)
  - "All users cannot ssh to our server. If you have special needs, please feel free to contact us." (tcloud quickstart FAQ, item 4)
  - Term of Service usage rules: "Do not run any application that performs a security intrusion", "Do not run any application that could be interpreted as a privacy violation", "Do not hold TACC resources when they are not actively used", "Do not access resources that are not allocated to you", "Do not make hacking attempts to the TACC infrastructure". Violations can lead to account disabling, notifying the supervisor, or legal action.
  - Reading: the model-service forward has specific textual support; forwarding to our own web port has none. Treat the web-port use as an authorization question for the TA, not as documented permission.
- **Capability versus permission.** The SSH plumbing works; the only explicit text about off-platform access is the model-service forward. Ask the TA before relying on a student-run tunnel to a web port for the demo.
- **No per-job public URL was found.** The web console shows job history and status; the platform's HAProxy port-exposure mechanism for Jupyter-style access is not documented for student jobs through the course SDK.
- **Capacity is tight.** Measured on 2026-10-28: 10 nodes, `MaxNodes=2`, 20 CPUs per node, 2 GPUs per node, with 0 idle, 6 drain, 4 down, and 3 jobs pending from another account. Queueing, not concurrency, is the demo risk; keep replay and start service jobs early.

Sources for this section: SDK source `userconfig.go` and `tcloudcli.go`; `sinfo` and `scontrol` output read from the login node on 2026-10-28; tcloud quickstart FAQ and TOS; platform architecture paper arXiv 2110.01556, sections 3.2, 5.2, and 7.

## Job budget

- The public environment validation recorded on 2026-10-06 measured a full cold start of 12 minutes 40 seconds for the Qwen service, including first load and compile. With a one-hour cap, one service job leaves about 45 minutes of usable serving time.
- The service address (`SERVICE_BASE_URL=http://NODE:8000/v1`) changes with every job, and the client must read it from the log of the current job each time. The address stops working when the job ends.
- Evaluation must fit the usable window: split the 50-question benchmark and the ablations into batches that complete in under 45 minutes, and cache retrieval snapshots and model responses so a rerun does not need a fresh service.
- Use one service job per evaluation window instead of short repeated submissions; this respects both the one-hour cap and the fairness rule.
- The demo should have a replay mode that reads cached responses, so the presentation does not depend on a live GPU job.

## Storage budget

- 100 GB total, shared by the group rather than per account.
- The provided Qwen weights live in the read-only public path, so they are not part of our workspace usage.
- Downloads we control: the OCR model (about 2 GB), the embedding model (about 2.3 GB fp32), page images and OCR output (a few hundred MB), the retrieval index and cached responses (small), and any course PDFs kept in the workspace (about 58 MB). The chosen models are recorded in [tech-selection.md](tech-selection.md).
- Keep model downloads outside the corpus directory ([`data/corpus/`](../data/corpus/) at the repository root). Clear job-local scratch and Hugging Face caches if they grow; the platform maps `HF_HOME` to a job-local temporary directory, so those caches do not persist anyway.

## Consequences for the plan

- No proposal change is needed: the frozen two-page [proposal](../proposal/proposal.md) already states the TACC service as primary, with external LLM and search APIs optional, labelled, and cached. The clarification confirms that text rather than invalidating it.
- Keep the repository runnable without external keys or GPU access: cached baselines, cached retrieval snapshots, and a replay path.
- The dense retrieval side needs no new packages: the public environment already ships PyTorch and Transformers, so an open embedding model can be loaded directly once its weights are downloaded to our workspace. BM25 remains the no-cost fallback and a required ablation arm.
- The OCR job is now part of the plan, not a stretch goal: the corpus is produced by a TACC OCR job whose model and output contract are recorded in [tech-selection.md](tech-selection.md) and [ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md). The existing transcripts are only a human quality reference.
- Dependency installation follows the pinned project layer described in [ADR-0001](adr/0001-pinned-python-environment-without-docker.md): a cached install under `$HOME`, never a modification of the read-only public environment.

## Sources

- Course staff reply from Yijun Sun, 2026-10-28, by email to LI Jinchuan, TIAN Yujia, and XIE Yifeng.
- Course public environment guide and student commands, course workspace copies outside this repository.
- TACC tutorial, `time=02:00:00` service example.
- Public environment validation record, 2026-10-06: 12 minutes 40 seconds cold start, 65.75 tokens/s single stream, 203.33 tokens/s at four concurrent requests.
- tcloud SDK 0.4.1 job schema: https://github.com/turingaicloud/tcloud-sdk/blob/master/cli/tcloudcli/tuxivconfig.go
- tcloud quickstart configuration guide and FAQ: https://github.com/turingaicloud/quickstart
- SDK client cluster configuration, `~/.tcloud/.clusterconfig`, read on 2026-10-28.
