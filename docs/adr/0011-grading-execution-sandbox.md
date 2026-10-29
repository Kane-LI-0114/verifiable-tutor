# ADR-0011: Docker sandbox for untrusted student submissions

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The grading assistant from [ADR-0010](0010-ta-grading-agent.md) must run test harnesses against student code. Student submissions are untrusted third-party code, which is a different class from the agent's own practice code: a submission may try to read the project `.env`, reach the network, fill the disk, fork until the machine stalls, or modify the corpus.

[ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md) settled agent tool execution with process-level limits inside the TACC job container, and it states plainly that this is not a strong sandbox: no filesystem jail, no network isolation, no cgroup control. That is acceptable for generated practice code and unacceptable for arbitrary student code.

The local machine has Docker; the TACC platform has none, no root, and user namespaces are disabled. The delivered grading workflow runs on the local backend, so Docker is available at the place where grading actually happens. TACC is not needed for grading in this deliverable: the evaluation evidence is local, and the report states that grading does not run on TACC.

The assignment environments differ: the course MPI toolchain lives in the TACC public environment, while a Docker image is a local reproduction. This mismatch must be recorded per assignment.

## Decision

- Untrusted student code runs only inside a local Docker sandbox, one container per submission.
- The sandbox removes the usual risks: `--network none`, a non-root user inside the container, a read-only root filesystem, exactly one writable per-run directory, only the submission and the assignment package mounted (read-only where possible), no host home directory, no project repository, no `.env`, and no Docker socket.
- Resource limits are explicit: CPU quota, memory limit, process limit, and a wall-clock timeout enforced by the runner, which also kills the container when the timeout fires.
- The container runs the assignment package's own image and command; the run records the image digest, toolchain versions, exit code, and captured output.
- Grading orchestration stays in the local backend; TACC runs no untrusted student code in this deliverable, and no grading job directory is added under `tacc/`.
- No network access is allowed during test execution. If an assignment genuinely needs a download, the package must vendor the data into the image or the assignment is not auto-runnable; the TA supplies the test results in that case.
- If an assignment toolchain cannot be reproduced faithfully in Docker, the assignment package can declare a test-output fallback: the TA runs the harness and provides the outputs, and the assistant grades without execution. The report states which assignments used the fallback and why.
- Docker is a local grading dependency only. The agent tool runner ([ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md)) and the practice lab do not use Docker, so the student-side execution path stays unchanged.
- The runner seam is tested with a fixture image or a fake runner: no network, no host file access, timeout kill, exit code capture, and a write outside the mount is rejected.

## Consequences

**Positive:**

- The grading assistant never executes student code on the host, so the project `.env`, the corpus, and the rest of the machine are not reachable through a submission.
- Resource limits protect the laptop and the job budget; the container is removed after each run.
- The recorded image digest and toolchain versions make a grading run reproducible and auditable.
- The design keeps the TACC boundary clean: no untrusted code runs on the platform, so the platform policy question does not arise for grading.

**Negative:**

- Docker becomes a required local dependency for grading, with image builds per assignment and a first-run cost of building or pulling each image.
- The local image is a reproduction of the course environment, not the environment itself; environment alignment must be stated per assignment.
- A container escape or a Docker daemon misconfiguration remains a residual risk. Standard Docker defaults are used, but this is not a hardened isolation boundary.
- The fallback for non-reproducible toolchains loses execution evidence and weakens the grade recommendation for those assignments.

**Neutral:**

- Student submissions and grading results never reach TACC in this deliverable, which is consistent with the local-first demo mode.

**Follow-up:**

- Build one reference image for the MPI and GEMM assignment and record its digest and toolchain versions.
- Test the sandbox seam: no network, no host path, timeout, exit code, process and memory limits.
- Record per-run image and toolchain evidence in the grading trace and the report.
- State the local versus TACC environment mismatch in the report limitations.

## Alternatives considered

**Run student code in the TACC job container.** For: the closest environment to the course assignments. Against: no strong isolation on TACC, a one-hour job cap, queue latency, and a policy surface for untrusted execution; rejected for this deliverable.

**Process-level limits on the local host (the ADR-0009 runner).** For: no Docker dependency and one runner for everything. Against: student code could read `.env`, reach the network, and write outside the workspace; unacceptable for third-party code.

**A rootless container runtime such as Podman.** For: daemonless and rootless isolation. Against: the machine already has Docker and the team does not need a second runtime; Docker Compose is already used for Langfuse ([ADR-0007](0007-langfuse-for-local-model-call-tracing.md)).

**A microVM or WASM sandbox.** For: stronger isolation than containers. Against: the MPI and CUDA toolchains cannot run in WASM, and a microVM adds a heavy local dependency for no course benefit.

**An external grading service.** For: isolation and scale handled elsewhere. Against: student work leaves the laptop, the course does not reimburse external services, and the project needs its own evaluable pipeline; not chosen.

**No execution, TA-supplied test outputs only.** For: no untrusted code path at all. Against: code assignments would lose executable evidence and the assistant would grade on the TA's word; kept only as the explicit fallback for non-reproducible toolchains.

## References

- Grading workflow and human approval: [ADR-0010](0010-ta-grading-agent.md)
- Agent tool execution boundary: [ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md)
- Environment strategy and the platform constraints: [ADR-0001](0001-pinned-python-environment-without-docker.md), [../tacc-notes.md](../tacc-notes.md)
- Product requirements, NFR-11: [../prd.md](../prd.md)
- Docker runtime isolation options: https://docs.docker.com/engine/security/
