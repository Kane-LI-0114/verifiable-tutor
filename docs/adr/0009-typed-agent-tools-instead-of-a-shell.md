# ADR-0009: Typed agent tools instead of a generic shell

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

> **Context update (2026-11-01).** The delivered backend runs on the laptop. [ADR-0011](0011-tacc-as-required-model-serving-backend.md) makes TACC a required model-serving backend for the embedding index and Qwen knowledge-base jobs, reached only by job submission; the tool boundary and the per-request `tacc/exec` execution of code answers are unchanged.

## Context

The lead requires users to see the agent's thinking and execution, including command-line execution. That can mean two different things: giving the model a shell, or giving it typed tools whose implementation runs commands. The choice decides both the security surface and the shape of the user-visible work chain.

The agent backend runs locally now and may run in a TACC CPU job later. On TACC there is no Docker, no root, and user namespaces are disabled; processes run inside the per-job container as the same user, with open network egress. A strong sandbox is therefore unavailable there, while the laptop does have Docker. Requiring Docker locally would break parity with TACC and with the demo.

The project already needs a restricted subprocess runner for the practice lab and for test execution ([../tech-selection.md](../tech-selection.md)). That runner is the natural execution boundary.

A generic shell exposed to a model would allow arbitrary file access (including the ignored `.env` with provider keys), arbitrary network use, and resource abuse inside a one-hour job. None of that is controllable without the sandbox that the platform does not provide.

## Decision

- The model receives typed tools only. There is no generic shell tool. The tool set covers retrieval, page reading, span verification, the disclosure decision, generation, practice test execution, and compile-and-run for practice binaries; the set is closed and versioned in configuration.
- Execution tools call one restricted subprocess runner:
  - Arguments are passed as a list with no shell interpolation, so no pipelines, redirection, or command substitution from model text.
  - The working directory is a per-user, per-run scratch directory.
  - The environment is allowlisted: `PATH`, `HOME`, `LANG`, `TMPDIR`, and nothing else. Provider keys, the SMTP authorization code, Langfuse keys, and session secrets are removed before the child starts.
  - Resource limits are set with `resource.setrlimit`: CPU seconds, address space, file size, open file descriptors, and process count.
  - A wall-clock timeout (30 seconds by default, 120 seconds for the practice test runner) kills the process group.
  - Standard input is closed; standard output and error are captured and truncated for display.
  - Network use is not enforced at the OS level because no network namespace or firewall is available under the PRoot runtime. The whitelist selects binaries that do not fetch, and the limitation is documented.
- The user-visible work chain renders each tool call: tool name, model-supplied arguments, the exact command line, the exit code, and truncated standard output and error. This is what "command-line execution" means in the product, and it is produced from the tool layer rather than from a shell session.
- Before running user-supplied code, the graph interrupts and asks the user to confirm, using the LangGraph interrupt mechanism ([ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)). Generated practice code that was already verified in batch runs without an extra confirmation. File writes outside the scratch directory are rejected by the runner.
- The same runner code is used locally and on TACC. A Docker container is not part of the local execution path, because parity with TACC matters more than stronger local isolation.
- Practice and self-test code answers run as TACC jobs under the team account. The demo has two to three trusted users, so the system does not claim hostile-user isolation; the job container and the runner limits are the boundary, and the limitation is stated in the report. The requirements are in [../prd.md](../prd.md), FR-E4 and NFR-11.

## Consequences

**Positive:**

- There is no shell injection surface, and every agent action is a typed, auditable, testable call.
- Commands and their output are visible to users without exposing a shell.
- Resource limits protect the one-hour job and the local machine.
- Local and TACC behavior are the same code path, so the demo matches the evidence path.

**Negative:**

- The agent is less capable than a general coding agent; a new need requires a new typed tool and a new test.
- Isolation on TACC is process-level only: no filesystem jail and no network block. A malicious command with a whitelisted binary could still reach other files the user owns.
- Resource limits can be evaded partially by forking (the process count limit narrows this, it does not close it).
- User-supplied code can only be run when the platform toolchain covers it; arbitrary languages are unsupported.

**Neutral:**

- The TACC job container remains the outer boundary around everything the agent does.

**Follow-up:**

- Implement the runner behind one seam and test it: exit code and captured output, timeout kills the process group, the environment contains no secrets, a non-whitelisted binary is rejected, and a write outside the scratch directory is rejected.
- Record the binary whitelist and the limits in configuration rather than in code.
- Add the interrupt around user-supplied code execution and show the confirmation in the work chain.
- State the missing network isolation in the report's limitations section.

## Alternatives considered

**Generic shell through `subprocess` with `shell=True`.** For: the most capable agent and the simplest implementation. Against: arbitrary access to `.env`, arbitrary network use, and no reliable resource control; not chosen.

**Container sandbox with Docker.** For: strong filesystem and network isolation on the laptop. Against: Docker is unavailable on TACC and custom images are not supported, so the local and TACC paths would diverge; not chosen for the execution path.

**bubblewrap, nsjail, or firejail.** For: lightweight Linux sandboxes. Against: they need user namespaces or privileges that the platform disables or does not grant, and they are not present in the public environment; not available.

**seccomp or Landlock filters.** For: kernel-level syscall and filesystem restrictions without root. Against: no supported tooling in the public environment under PRoot, and the filters are architecture-specific; not chosen for the first version.

**A WASM sandbox.** For: strong isolation and no host access. Against: cannot run the MPI and CUDA toolchain the practice packs require; not applicable.

**One Slurm job per execution.** For: platform-level isolation. Against: the one-hour policy, queueing, and the fairness rule make it unusable for interactive commands; not chosen.

**No execution at all.** For: the smallest risk. Against: the lead requires visible execution, and the practice lab needs to run tests; not acceptable.

## References

- Orchestration runtime: [ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)
- Environment strategy: [ADR-0001](0001-pinned-python-environment-without-docker.md)
- Platform mechanics and the PRoot runtime: [../tacc-notes.md](../tacc-notes.md)
- Practice lab and test runner: [../tech-selection.md](../tech-selection.md)
- User namespaces and PRoot constraints: course workspace `tacc-env-docs/SOURCES.md`, outside this repository
