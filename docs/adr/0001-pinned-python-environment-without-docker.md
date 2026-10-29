# ADR-0001: Pinned Python environment without Docker

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-28 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The project needs a reproducible Python environment for three kinds of work: the CPU agent backend and evaluation harness, the GPU OCR and embedding batch jobs, and local development on macOS. The course platform limits the options:

- The tcloud SDK 0.4.1 has no image, container, or registry configuration. Its `TuxivConfig` accepts an entrypoint, a conda environment, Slurm job settings, and datasets only, and the generated launcher always activates a conda environment ([tuxivconfig.go](https://github.com/turingaicloud/tcloud-sdk/blob/master/cli/tcloudcli/tuxivconfig.go)). Jobs do run in containers, but the platform chooses the image.
- Accounts have no Docker, no sudo, and no user namespaces; the public environment exists because root-level isolation is unavailable.
- A submit directory is capped at 1 GiB by the cluster configuration, so images and large data cannot travel with a job.
- The public course environment is read-only and pins 199 packages, including Python 3.12.14, PyTorch 2.11.0+cu128, vLLM 0.26.0, and Transformers 5.10.4. Its package list and entry points are mirrored in the course workspace under `tacc-env-docs/`, outside this repository.
- Compute nodes and login nodes have open network egress, and the official FAQ sanctions install commands inside a job entrypoint.
- `$HOME` and `USERDIR` persist across jobs; `WORKDIR` is re-synchronised on every submit and may be removed when a job ends.

The project also needs packages the public environment lacks, at pinned versions: `pypdfium2`, `pytest`, and the PaddleOCR client.

## Decision

We ship two reproducible layers and no image.

- **GPU layer:** the read-only public environment, unchanged, for vLLM, PyTorch, and Transformers. Model weights are downloaded once with `hf download --local-dir "$HOME/models/<name>"`, because `HF_HOME` is bound to a job-local temporary directory.
- **Project layer:** a hash-pinned `requirements.txt`, a committed `uv.lock`, and an idempotent `scripts/tacc/bootstrap.sh`. The script downloads `uv` into `$HOME/bin` when missing, installs the requirements into a directory keyed by the requirements hash and the public environment version, for example `$HOME/vt-deps/<key>`, and jobs prepend that directory to `PYTHONPATH` before running the public Python. A virtual environment created from the public interpreter is the fallback if a target directory does not work under the PRoot runtime.
- **Data layer:** course PDFs, OCR output, page images, indexes, caches, and weights live in `USERDIR` or `$HOME`; task directories hold code only.
- A `Dockerfile` may exist for local development parity, but it is not a delivery mechanism.

`requirements.txt` pins only the delta the project adds. The public environment owns the GPU stack pins. The first job pays the install cost; every later job runs the hash check and skips installation.

## Consequences

**Positive:**
- Pinned, reviewable dependency versions without root access, an image registry, or a 1 GiB upload.
- Repeat jobs start in seconds once the cache exists.
- The GPU stack keeps the versions the course already verified on this hardware.

**Negative:**
- The environment is two layers, so `requirements.txt` alone does not describe the full runtime. The setup documentation and the report must state the public environment versions beside the project pins.
- The bootstrap depends on network egress and on `uv` running under the PRoot userland runtime. Both are unverified until the first TACC spike.
- A public environment upgrade can invalidate the cache key and force a reinstall, so the key must include the public environment version.
- The first job of a fresh account pays an install cost that must fit inside the one-hour policy cap.

**Neutral:**
- Large inputs move from task directories to `USERDIR`, which adds an explicit upload step and needs a documented local mirror for development.

## Alternatives considered

**Custom Docker image.** For: the strongest reproducibility and the cleanest handover. Against: the SDK has no image field, the launcher hardcodes a conda activation, and accounts cannot run Docker or build images. Why not chosen: impossible on this platform.

**SDK conda environment with pinned dependencies.** For: supported by the SDK by design and activated automatically by the generated launcher. Against: the course proxy configuration is empty, the base conda is 4.9.2 on Python 3.8.5, and the course docs warn that a course-specific conda configuration can block environment creation. Why not chosen: unverified success and an awkward place to pin pip-only packages. Kept as a fallback if the bootstrap fails twice in a row.

**Plain `pip install` at every job start.** For: simplest to write. Against: repeated network cost inside one-hour jobs and version drift when a requirement uses a range. Why not chosen: violates the reproducibility goal.

**Install everything into a repository-local directory.** For: no `$HOME` dependency. Against: the submit directory is capped at 1 GiB and every submit re-synchronises it. Why not chosen: the cap and the sync cost make it fragile.

## References

- SDK configuration source: https://github.com/turingaicloud/tcloud-sdk/blob/master/cli/tcloudcli/tuxivconfig.go
- Quickstart configuration guide: https://github.com/turingaicloud/quickstart/blob/master/tuxiv.conf.md
- Quickstart FAQ, dependency installation inside the entrypoint: https://github.com/turingaicloud/quickstart/blob/master/FAQ.md
- Platform mechanics and budgets: [../tacc-notes.md](../tacc-notes.md)
- Public environment versions and entry points: course workspace `tacc-env-docs/`, outside this repository
- Verification items: [../tech-selection.md](../tech-selection.md#verification-spikes)
- Verified on 2026-10-29 (job 27872): the target install and all four project imports work under PRoot; the first install took 1957 s and a later job reused the cache in 32 ms. Measurements: [../tacc-notes.md](../tacc-notes.md#verification-spike-results-2026-10-29).
