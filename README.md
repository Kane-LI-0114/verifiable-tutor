# Verifiable AI Tutoring on TACC

*A course-grounded agent with evidence-checked answers, executable practice labs, and enforced course policy*

Project repository for CSIT6000V Advanced AI Computing and Systems (Fall 2026) by LI Jinchuan, TIAN Yujia, and XIE Yifeng: a course-grounded tutoring agent built to run on TACC.

## Status

**Proposal stage.** The only substantive content in this repository is the course project proposal. Apart from the proposal package and `.gitignore`, the repository is a directory scaffold of empty `.gitkeep` placeholders. There is no application code, no tests, no benchmark data or results, and no evaluation report yet. Everything described below as behavior is planned; planned directories appear in the layout table as `placeholder (.gitkeep)`.

## What it is

A tutoring agent for one course whose outputs are checkable in three ways: text claims against cited page spans, code artifacts against executable tests, and disclosure against a dated policy. The scope is deliberately narrow: this course's own materials, assignments, and deadlines. The full argument, including motivation and design rationale, is in [proposal/proposal.md](proposal/proposal.md); this README is the entry point, not a second proposal.

## Use cases

Students can:
- Ask course questions and receive answers that cite the exact page and quoted span.
- Request a review outline or a self-test quiz on a topic.
- Practise with a generated exercise at the scale and environment of the corresponding assignment, receiving a reference solution, tests, and a stepwise explanation.
- Submit their own solution and receive line-anchored teaching.

Instructors and TAs can:
- Maintain the deadline registry that drives the disclosure policy.

## Disclosure policy

A five-state policy decides what the agent may reveal. The states are pre-release, active, extension window, post-deadline, and unknown; the gate that enforces them is planned, not implemented.

| Policy state | What the agent does |
|---|---|
| Pre-release, active, extension window | Refuses complete homework solutions and offers hints. Explains a user-provided solution only at the level provided and never fills in missing parts. |
| Post-deadline | Replaces refusal with full teaching plus a verified solution. |
| Unknown | Abstains rather than guesses; insufficient evidence also leads to abstention. |

The gate is code, not a prompt: a versioned registry of release and due dates with extensions, an intent classifier, and a log of every decision. The proposal covers the policy in [section 2](proposal/proposal.md#2-task-definition-and-outputs) and [section 3](proposal/proposal.md#3-proposed-system).

## Architecture

The planned system has three moving parts: a browser UI, an agent backend submitted as a TACC CPU job, and a course Qwen service running as a TACC GPU job behind a model-client abstraction.

![System containers and components](proposal/figs/fig2_components.png)

The GPU job is intended to serve Qwen3.8-27B-AWQ-INT4 with vLLM at TP=2 and 32K context, admitting at most four concurrent requests. The figure source is [proposal/figs/fig2_components.dot](proposal/figs/fig2_components.dot).

The five planned subsystems inside the CPU job:
- Evidence: hybrid retrieval (batched and cached dense embeddings plus BM25, fused, with optional reranking) and a deterministic span verifier that requires every quoted span to occur on its cited page, with one repair round or abstention. The OCR stage is chosen in week one, with existing course transcripts as fallback.
- Practice lab: packs that mirror the target assignment environment (first pack: MPI/GEMM with the same toolchain, Makefile, public datasets, and an sdk-test-style harness); a generated reference solution is accepted only after it compiles and passes the pack's tests.
- Policy gate: the code-level gate described above, plus the versioned deadline registry it reads.
- Teaching explainer: cites page spans, code lines, and test outcomes, and never invents missing content before the deadline.
- Model client and trace logger: the TACC service is primary; external LLM and search APIs are optional, labelled, and cached for baselines; traces, tests, and results follow the required execution path from task to visible result.

## Repository layout

All paths are repository-relative. Planned roles are statements of intent, not descriptions of implemented behavior.

| Path | Intended role | State |
|---|---|---|
| `src/verifiable_tutor/policy/` | Code-level disclosure gate and deadline registry | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/orchestrator/` | Request routing and context budget | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/evidence/` | Hybrid retrieval and deterministic span verifier | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/practice/` | Practice pack generation and executable tests | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/teaching/` | Line-anchored explanations | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/eval/` | Evaluation harness | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/ui/` | Browser UI; static assets under `src/verifiable_tutor/ui/static/` | placeholder (`.gitkeep`) |
| `tacc/serve/` | TACC GPU job for the Qwen service | placeholder (`.gitkeep`) |
| `tacc/client/` | TACC CPU job for the agent backend | placeholder (`.gitkeep`) |
| `benchmarks/questions/`, `benchmarks/policy_scenarios/`, `benchmarks/results/` | Course questions, policy scenarios, recorded results | placeholder (`.gitkeep`) |
| `data/corpus/`, `data/index/`, `data/caches/` | Course PDFs and OCR, dense plus BM25 index, cached embeddings and retrieval snapshots | placeholder (`.gitkeep`) |
| `config/` | Runtime configuration | placeholder (`.gitkeep`) |
| `tests/` | Test suite | placeholder (`.gitkeep`) |
| `scripts/` | Utility scripts | placeholder (`.gitkeep`) |
| `examples/` | Usage examples | placeholder (`.gitkeep`) |
| `docs/figures/` | Report and documentation figures | placeholder (`.gitkeep`) |
| `proposal/` | Proposal sources: `proposal.md`, `build_proposal.py`, figure `.dot` sources, rendered PDF and DOCX | present: proposal sources |

## Evaluation plan

All evaluation work is planned and the repository contains no results. Four research questions, detailed in [proposal section 4](proposal/proposal.md#4-evaluation-plan):

- RQ1 evidence fidelity: citation span accuracy (deterministic) and faithfulness (human-checked support rate).
- RQ2 practice verifiability: the share of generated exercises whose reference solution compiles and passes course-style tests, plus environment alignment and cost per exercise.
- RQ3 disclosure correctness: behavior across the five policy states, including a deadline extension, and an adversarial set (false "deadline passed" claims, TA impersonation, role-play, pasted "official" solutions) against a prompt-only baseline.
- RQ4 cost: end-to-end latency, model calls per request, and a retrieval ablation over BM25, dense, and hybrid variants.

The benchmark is planned to hold fifty course questions, ten policy scenarios, and two practice packs, with later-released sessions held out; runs use temperature 0, cached retrieval snapshots and responses, and an injected clock.

## Roadmap

The four one-week workstreams from proposal Table 1 (planned):

| Workstream | W1 | W2 | W3 | W4 |
|---|---|---|---|---|
| Corpus and OCR pipeline | X | | | |
| Hybrid index and retrieval | X | X | | |
| Span verifier | | X | | |
| Policy engine and registry | | X | X | |
| Practice pack and tests | | | X | |
| Explainer | | | X | |
| UI and replay mode | | | X | X |
| Evaluation, report, demo | | | | X |

Deliverables: the code repository, the evaluation report, and the demo.

## Documentation

- [proposal/proposal.md](proposal/proposal.md): readable Markdown text of the proposal, generated by `proposal/build_proposal.py`.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.pdf): the two-page submitted PDF.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx): editable DOCX version.
- [AGENTS.md](AGENTS.md): agent and contributor guide covering sources of truth, commands, and conventions.

## Team

- LI Jinchuan (21188271)
- TIAN Yujia (21201619)
- XIE Yifeng (21322152)

CSIT6000V Advanced AI Computing and Systems, Fall 2026. Instructor: Prof. Kai Chen. Proposal dated October 27, 2026. Repository: https://github.com/Kane-LI-0114/verifiable-tutor
