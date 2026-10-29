# Product requirements: verifiable-tutor

| | |
|---|---|
| **Status** | Draft for review, version 0.2 |
| **Date** | 2026-10-29 |
| **Owners** | LI Jinchuan, TIAN Yujia, XIE Yifeng |
| **Scope** | What the system must do and how it is accepted |
| **Supersedes** | The proposal stays frozen as the submitted two-page artifact. This document is the living product specification; [tech-selection.md](tech-selection.md) and the ADRs own how the system is built |

This document is the source of truth for what ships. The proposal records why the project exists and what was promised to the course; the technology selection and the ADRs record implementation decisions. When a requirement here contradicts the proposal, the report explains the deviation.

## 1. Problem and goals

CSIT6000V students absorb dense lecture and tutorial material and apply it in individual assignments, but support is uneven. Generic assistants cannot ground answers in the course's own slides, cannot respect the assignment integrity rules, and cannot verify what they claim. The system treats this as one problem: every output must be checkable.

Goals:

- **G1 Evidence-grounded answers.** Every course claim cites a page and a quoted span, and every cited span is checked against the page text.
- **G2 Enforced disclosure.** What the agent may reveal follows a dated assignment policy evaluated in code, not in the prompt.
- **G3 Verified practice.** A practice exercise is shown only with a reference solution that has compiled and passed the pack's tests in the course environment.
- **G4 Reproducible evaluation.** Representative cases, recorded traces, and a failure analysis produced from TACC runs, with no paid call needed to rerun.
- **G5 Grading assistance.** A TA can run a grading batch, receive per-criterion score recommendations with evidence, and approve or edit them before any grade leaves the system.

Course deliverables this must satisfy: a frontend for task input, visible progress, and result review; a backend with an agent workflow, a model API, and tool and data integration; an evaluation with representative cases, metrics, and at least one analyzed failure; a tested demo; and a runnable code repository.

## 2. Users and roles

| Role | Description | Access |
|---|---|---|
| Student | A person with a course student email address | Registers and signs in; owns their conversations, practice runs, and traces |
| Instructor or TA | Owns the course: maintains the deadline registry that drives the disclosure policy, and runs the grading assistant on student submissions | Seeded account; role checked server-side; registry editing in P0 is a versioned configuration change by the team, the in-app editor and the TA workbench are P1; grading data is visible only to this role |
| Demo operator | A team member driving the presentation | Uses a student or seeded account |
| Grader or audience | Watches the demo | No account and no direct access to the deployment |

Accounts exist to associate conversations and traces with a person and to prepare the system for real use. This is a course design: it is not hardened for public multi-tenant operation, and abuse protection is out of scope (section 3). Students never see grading data, submissions, or grading traces.

## 3. Scope

Priorities are build order, not a cut list. All P0 and P1 content is committed; P2 is best effort. The TA grading assistant is an extension beyond the frozen proposal; the report explains the deviation.

**P0, required for the first end-to-end demo and evaluation run:**

- Accounts: registration with student email, verification code, login and logout, password reset, roles, per-user isolation.
- Conversation: bilingual course questions with hybrid retrieval, page-level citations with quoted spans, deterministic span verification with one repair round or abstention, an evidence panel with page images and highlights.
- Model control: DeepSeek Flash as the default, MiMo Flash and Pro selectable, a unified thinking level, and explicit retry and timeout behavior without cross-model fallback.
- Disclosure gate: five policy states from a versioned deadline registry, intent routing, refusal and hints before the deadline, full teaching after it, decision logging, injected clock.
- Work chain: a user-facing timeline of steps, model thinking, and tool calls including command lines and output.
- Practice lab: one MPI and GEMM pack that mirrors the assignment environment; exercises and reference solutions generated in batch, verified by compilation and tests, and cached.
- Voice: microphone transcription into the composer, audio file attachments when a MiMo model is selected, and text to speech playback.
- Observability and evaluation: JSONL session traces, local Langfuse tracing during development, a benchmark harness over 50 course questions, 10 policy scenarios, and the practice pack, results, and a failure analysis.
- Delivery: the system runs locally from a clean checkout with documented commands, a demo runbook, and a replay fallback. TACC jobs produce the corpus, index, and evaluation evidence used in the report.

**P1, committed but can land after the first demo:**

- Study aids: grounded review outline and self-test quiz.
- Line-anchored explanation of a user-submitted solution.
- In-app deadline registry editor for the instructor role.
- TACC-hosted demo path, if the TA authorizes the forward and the tunnel spike passes.
- DeepSeek web search augmentation for questions the corpus cannot answer.
- TA grading assistant: assignment package, batch submission upload, rubric and test based score recommendations with evidence, a review workbench, an audit log, and CSV export.

**P2, best effort:**

- Live generation of practice exercises instead of batch generation.
- A CUDA and attention practice pack.
- Teaching-video voiceover pipeline built on TTS.
- A reranker for retrieval.
- Notifications or email digests.
- Grading of free-form written assignments.

**Non-goals:**

- A public deployment or real multi-tenant operation.
- Quotas, daily budgets, login lockout, and abuse protection. The account system has basic authentication and authorization only.
- Plagiarism detection and gradebook integrations beyond CSV export.
- Unattended automatic grading or automatic grade publication. The grading assistant recommends and a TA decides.
- Mobile applications, native clients, and server-side rendering.
- Strong sandboxing of user code on TACC (see ADR-0009, ADR-0011, and section 6).
- Email deliverability guarantees beyond local demonstration.

### Future development

- **Multi-course support.** The delivered system serves one course. Generalizing it needs a course-scoped data model (memberships, per-course corpus and index, per-course deadline registries), TA self-service course onboarding, and a per-course OCR and indexing pipeline. The current schema is single-course, so this is a migration rather than a configuration switch. Recorded as future work after the single-course evaluation.
- **Student self-submission portal.** Students upload their own work instead of the TA bulk uploading, with identity binding, deadline enforcement, and resubmission rules.
- **Written assignment grading.** Rubric grading for free-form answers and reports, with citation and evidence checks.
- **Multi-course evaluation and shared TA tooling.** Benchmarks per course and grading packages shared across courses.

## 4. User journeys

Each journey is a demo or evaluation script and is accepted against its numbered requirements.

- **J1 First visit and first question.** A student registers with a student email, receives a six digit code, signs in, asks a course question in Chinese or English, and sees a streamed answer with inline citations, a work chain, and an evidence panel.
- **J2 Homework request before the deadline.** The student asks for a complete assignment solution before the due date. The agent refuses the complete solution, offers a hint, and the work chain shows the policy state and the rule that decided it.
- **J3 Teaching after the deadline.** The same request after the due date (or inside an extension window that ended) receives full teaching plus a verified solution.
- **J4 Review outline and quiz.** The student asks for a review outline or a self-test quiz on a topic and receives cited material that does not reveal the current assignment solution.
- **J5 Practice.** The student opens a practice exercise for the MPI and GEMM assignment, runs the provided tests, and reviews the verified reference solution and stepwise explanation.
- **J6 Submitted solution.** The student pastes their own solution and receives line-anchored teaching. Before the deadline the agent does not fill in missing parts.
- **J7 Voice.** The student records a question in the composer (transcribed by ASR) or attaches an audio file while a MiMo model is selected, and can play the answer back as speech.
- **J8 Provider timeout.** A slow or unavailable provider produces an in-place timeout message with a retry action, without switching models and without exposing a raw provider error.
- **J9 Offline replay.** With no network and no model calls, a recorded session replays through the real frontend and backend path.
- **J10 TA grading batch.** A TA uploads an assignment package and a batch of student submissions, reviews the assistant's per-criterion scores with evidence, edits where needed, approves, and exports the grades.

## 5. Functional requirements

IDs are stable. Priority uses P0, P1, and P2 from section 3. Acceptance criteria are observable behavior.

### 5.1 Accounts and access

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-A1 | Register with a student email address and a password, then confirm a six digit code sent by email | P0 | Unverified accounts cannot sign in; a code expires after 10 minutes; the code path is covered by a test seam |
| FR-A2 | Sign in and out with email and password; persistent server-side session with an HttpOnly, SameSite=Lax cookie | P0 | A signed-in session survives a page refresh and expires after 7 days of inactivity; logout invalidates it |
| FR-A3 | Only configured email domains may register; default `connect.ust.hk` and `ust.hk` | P0 | A foreign domain is rejected with a clear message; the domain list is configuration, not code |
| FR-A4 | Password reset by a one-time email link valid for 30 minutes | P0 | The link works once, expires, and invalidates all sessions for the account |
| FR-A5 | Two roles, student and instructor; the instructor account is seeded and can read the deadline registry state | P0 | Role checks happen server-side; a student cannot open instructor surfaces |
| FR-A6 | Every conversation, message, practice run, and trace belongs to one user | P0 | A second user cannot read another user's conversation by ID; the check is covered by a test seam |
| FR-A7 | Passwords are stored with scrypt and never logged; email addresses never appear in model traces | P0 | A database dump shows no plaintext password; a trace export shows internal user ids only |
| FR-A8 | Email delivery uses QQ Mail SMTP with an authorization code from `.env`; when SMTP is not configured, development mode writes the code to the backend log and marks the response | P0 | A registration test in development mode finds the code in the log; the configuration is documented in [email-local.md](email-local.md) |
| FR-A9 | A seed command creates the instructor account and demo student accounts | P0 | The command is idempotent and documented; no production credentials are committed |

### 5.2 Conversation and evidence

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-B1 | Answer in the language of the question (Chinese or English), with course terms preserved | P0 | Five benchmark questions in each language produce answers in the matching language |
| FR-B2 | Hybrid retrieval over the course corpus (SQLite FTS5 BM25 plus BGE-M3 dense, reciprocal rank fusion) | P0 | The ablation arms BM25, dense, and hybrid are runnable and reported |
| FR-B3 | Every course fact carries a citation with document id, page number, and the quoted span | P0 | A citation chip opens the evidence panel at the cited page and highlights the span |
| FR-B4 | Deterministic span verification: after whitespace and case normalization the quoted span must occur on the cited page; one repair round; otherwise abstain | P0 | A fabricated citation is rejected by the verifier; an answer that cannot be repaired becomes an abstention with the missing evidence named |
| FR-B5 | Evidence panel: server-rendered page image plus highlight rectangles from OCR block boxes | P0 | No PDF viewer and no CDN are required; the panel works offline |
| FR-B6 | Model selection: DeepSeek Flash default, MiMo Flash, MiMo Pro; one thinking control with four levels; MiMo degradation is recorded | P0 | The selected model and the effective thinking level appear in the trace; a MiMo selection with audio uses that same tier |
| FR-B7 | Same-model retries only; after exhaustion show a timeout or unavailable message with a retry action; no cross-model fallback and no raw provider error | P0 | A forced 503 sequence produces the user copy after three attempts and no call to another model |
| FR-B8 | Cache successful model calls and replay identical requests without a paid call | P0 | A repeated benchmark request produces the same result with no network call |
| FR-B9 | User-visible work chain: steps (understand, retrieve, verify, decide, generate, cite), model thinking, and tool calls with command lines and output | P0 | The chain is expandable per answer, shows the policy decision, and never shows a trace id or a provider raw error |
| FR-B10 | Record every session as JSONL and replay it through the same UI stream | P0 | Replay works with the network disabled |
| FR-B11 | Per-user conversation history with resume | P0 | A signed-in user sees their own conversations only |
| FR-B12 | Streamed response; a failed stream after partial output stops with the failure copy and does not replay a partial answer | P0 | A mid-stream failure shows the error state and the answer is not cached |

### 5.3 Disclosure policy

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-C1 | Versioned YAML deadline registry with assignment release dates, due dates, extensions, and the derived state | P0 | The registry validates against a schema; a missing or invalid file fails closed |
| FR-C2 | Five states: pre-release, active, extension window, post-deadline, unknown | P0 | The state for the current clock is shown in the work chain |
| FR-C3 | Intent routing over five classes: course question, homework solution request, pasted solution, post-deadline teaching request, other | P0 | The router is rule based first and model assisted second; every decision is logged with the rule id |
| FR-C4 | Before the deadline: refuse complete homework solutions, offer hints; explain a user-provided solution only at the level provided and never fill in missing parts | P0 | Ten policy scenarios cover refusal, hint, and partial explanation; a prompt injection asking to ignore the policy does not change the decision |
| FR-C5 | After the deadline: full teaching with a verified solution | P0 | The same request after the due date produces teaching, not refusal |
| FR-C6 | Unknown state or insufficient evidence: abstain rather than guess | P0 | An unregistered assignment abstains with a clear message |
| FR-C7 | Decision log in JSONL with state, rule id, registry version, and clock | P0 | Every policy decision appears in the trace and the log |
| FR-C8 | The clock is injected so tests can place a request in any state | P0 | A test changes the clock only, not the code path |

### 5.4 Study aids, practice, and teaching

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-D1 | Review outline on a topic, grounded in citations | P1 | Every outline item carries at least one verified citation |
| FR-D2 | Self-test quiz with answers and citations, without revealing the current assignment solution | P1 | The quiz respects the same policy gate as chat |
| FR-E1 | Practice pack format mirroring the assignment: toolchain, Makefile, datasets, and a test harness | P0 | The MPI and GEMM pack compiles and runs with the course toolchain |
| FR-E2 | Exercises and reference solutions generated in batch; a solution is shown only after it compiles and passes the pack's tests; verified artifacts are cached | P0 | A generated exercise without a passing solution is not shown; the cache avoids regeneration |
| FR-E3 | Test execution inside the restricted runner in the TACC CPU job | P0 | The runner seam returns exit code and output, enforces the timeout, and rejects commands outside the whitelist |
| FR-E4 | RQ2 metrics: share of exercises whose reference solution compiles and passes tests, environment alignment, cost per exercise | P0 | The evaluation harness exports the metrics as JSON |
| FR-F1 | Line-anchored explanation of a submitted solution with file and line references and test outcomes | P1 | Each claim points to a line that exists in the submitted file |
| FR-F2 | The explainer respects the disclosure gate and never fills in missing parts before the deadline | P0 | A pre-deadline submission explanation does not include the missing implementation |

### 5.5 Voice and audio

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-G1 | Microphone input is transcribed by MiMo ASR and inserted into the composer; the next turn uses the selected text model | P0 | A recording produces a transcript and a normal chat turn |
| FR-G2 | Audio file attachments are accepted only when a MiMo model is selected; the selected tier handles the audio; a DeepSeek selection returns a capability error | P0 | The capability error names the constraint; flash and pro each receive their own audio request |
| FR-G3 | Text to speech playback for assistant messages with cached audio per text, voice, and format | P0 | A played message produces audio without a second paid call |
| FR-G4 | Teaching-video voiceover pipeline | P2 | Out of scope for P0 and P1; recorded as a candidate |

### 5.6 Execution and tools

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-H1 | The agent invokes typed tools only; there is no generic shell tool | P0 | The tool set is closed and configured; an unknown tool call is rejected |
| FR-H2 | Execution tools use one restricted runner: argument list without shell interpolation, per-user scratch directory, environment allowlist without secrets, resource limits, wall-clock timeout, process group kill | P0 | The runner seam tests cover secrets removal, timeout, non-whitelisted binary rejection, and scratch directory boundary |
| FR-H3 | The work chain shows each tool call with the exact command line, exit code, and truncated output | P0 | A practice test run shows the command and its output in the timeline |
| FR-H4 | User-supplied code requires explicit confirmation before execution; generated and pre-verified practice code does not | P0 | The confirmation appears as a graph interrupt and a UI action; declining runs nothing |
| FR-H5 | Network isolation is not claimed; the limitation is stated in the report | P0 | The report limitations section and the tool documentation state it |

### 5.7 TA grading assistance

The grading assistant is a separate TA-side workflow. It recommends, the TA decides, and nothing is published or exported without approval.

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-K1 | Assignment package: title, rubric criteria with maximum points, tests or reference solution, and the expected runtime image | P1 | A package validates against a schema and is stored per assignment |
| FR-K2 | Batch submission upload by the TA (a zip or a file set with a student identifier); there is no student-facing upload in this deliverable | P1 | A batch parses into one submission per student; a malformed entry is reported and skipped |
| FR-K3 | The grading assistant produces per-criterion score recommendations with evidence (file and line references, test outcomes, rubric notes), a feedback draft, and a confidence value; it never publishes a grade | P1 | Every recommended score cites evidence; the workbench marks the draft as unapproved |
| FR-K4 | Code submissions run in the Docker sandbox from ADR-0011; test results become grade evidence | P1 | The sandbox blocks network and host file access, enforces limits, and records exit codes and output |
| FR-K5 | TA review workbench: accept, edit, or reject each recommendation; approval is required before export; an approved record is immutable except through an audit-logged revision | P1 | A grade cannot be exported while unapproved; every edit is in the audit log |
| FR-K6 | Audit log: every assistant suggestion, TA edit, approval, and export with the acting account and time | P1 | The log is complete for a batch and exportable |
| FR-K7 | CSV export after approval: student identifier, rubric items, total, feedback | P1 | Exported totals equal the approved rubric sums |
| FR-K8 | Grading data is hidden from students and from the student-facing trace; grading runs have their own JSONL trace and an optional local Langfuse trace without raw student identities | P1 | A student account cannot read submissions or grades; a trace export has pseudonymized student identifiers |
| FR-K9 | The assignment package records the toolchain and the runtime image, and any known mismatch with the course environment is stated | P1 | A grading run records the image and toolchain versions, and the report states the mismatch, if any |

### 5.8 Observability, evaluation, and delivery

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-I1 | JSONL session trace is the canonical record for replay and evaluation | P0 | Every session has a JSONL file with ordered events, including step, thinking, tool, and text events |
| FR-I2 | Optional local Langfuse tracing of model calls and graph steps; fail-open; local development only | P0 | The application answers normally with Langfuse disabled or down; the runbook exists |
| FR-I3 | Benchmark: 50 course questions, 10 policy scenarios, one practice pack, with later-released sessions held out | P0 | The benchmark files exist and the harness runs them from cache |
| FR-I4 | Evaluation harness exports JSON results and the five research questions are answered | P0 | RQ1 to RQ5 each have a result table or figure in the report |
| FR-I5 | At least one failure is analyzed by cause | P0 | The report names the dominant failure mode with trace evidence |
| FR-J1 | The repository runs locally from a clean checkout with documented commands | P0 | A fresh clone plus the documented commands reaches a working chat |
| FR-J2 | Tested demo runbook with the replay fallback | P0 | The demo can be run twice in a row, and replay works without network |
| FR-J3 | TACC jobs produce OCR, index, and evaluation evidence recorded in the report | P0 | Job ids, logs, and result files are cited in the report |
| FR-J4 | UI strings in Chinese and English with a toggle | P1 | A single translation resource serves both languages |
| FR-J5 | TACC-hosted demo path | P1 | Open until the TA replies to the 2026-10-29 email |

## 6. Non-functional requirements

| ID | Requirement | Target or acceptance |
|---|---|---|
| NFR-1 | Response latency | Measure and report first-token and full-answer latency on the local backend; provisional targets: first token at or under 3 seconds at p95, full answer at or under 20 seconds at p95 with cached retrieval |
| NFR-2 | Provider failure handling | Same-model retries, explicit timeout copy, no cross-model fallback, no background retry |
| NFR-3 | Privacy | Local development data stays on the laptop; model traces carry no email address; secrets only in `.env`; the report states which course excerpts leave the machine to model APIs |
| NFR-4 | Authentication security | scrypt password hashing, HttpOnly and SameSite session cookie, same-origin CSRF posture, sanitized markdown rendering |
| NFR-5 | Execution safety | Typed tools only, environment allowlist, resource limits, timeout kill, confirmation before user code (ADR-0009); untrusted student code only in the Docker sandbox (ADR-0011) |
| NFR-6 | Reproducibility | Temperature 0 and thinking off for evaluation runs, corpus hash recorded, responses cached so evaluation reruns need no paid call |
| NFR-7 | Evidence integrity | 100 percent of displayed citations pass the deterministic verifier; abstain otherwise |
| NFR-8 | Scale | Single-node, course-demo scale; no load or concurrency guarantees; multi-user correctness is tested, performance is not |
| NFR-9 | Accessibility | Keyboard reachable controls and readable contrast in the main flows; full WCAG conformance is not claimed |
| NFR-10 | Data lifecycle | Local SQLite and JSONL files; the instructor can delete a user's data; no retention guarantee |
| NFR-11 | Grading execution isolation | Student code runs only in the Docker sandbox from ADR-0011, with no network, a read-only base image, a per-run writable directory, a non-root user, and CPU, memory, process, and wall-clock limits |
| NFR-12 | Grading privacy and audit | Submissions, scores, and feedback are visible only to the TA role; every change is audit logged; student identifiers are pseudonymized in traces |
| NFR-13 | Grading reproducibility | A grading run records the assignment package version, the runtime image, the model, and the prompt versions, so the same batch can be re-run from cache |

## 7. Configuration and data ownership

| Content | Owner |
|---|---|
| Provider endpoints, model ids, roles, retry and timeout values, cache and embedding settings | `config/models.yaml` |
| Deadline registry | `config/deadlines.yaml` (planned), validated by pydantic |
| Local tracing settings | `config/observability.yaml` (planned, local development only) |
| Secrets: provider keys, SMTP authorization code, Langfuse keys, session secret | `.env`, ignored by Git; `.env.example` carries empty placeholders |
| Corpus and page images, index, caches | `data/corpus/`, `data/index/`, `data/caches/` locally; `USERDIR` on TACC |
| Session trace | JSONL under the local data directory; `USERDIR` on TACC |
| Assignment packages, rubrics, submissions, grade recommendations, and the grading audit log | local data directory (SQLite plus files); grading runs locally and has no TACC path in this deliverable |
| Grading runtime images | a `Dockerfile` inside each assignment package; Docker is a local grading dependency only (ADR-0011) |

## 8. Acceptance and evaluation targets

Targets are provisional and confirmed by the first evaluation run. They are stated so the team can tell a pass from a regression.

| Research question | Target |
|---|---|
| RQ1 evidence fidelity | Deterministic span verification passes for 100 percent of displayed citations; citation span accuracy at or above 0.95 on the 50-question benchmark; human-checked faithfulness at or above 0.90 on a sample of 20 answers |
| RQ2 practice verifiability | At or above 0.90 of generated exercises have a reference solution that compiles and passes the pack's tests; environment alignment documented; cost per exercise reported |
| RQ3 disclosure correctness | At or above 9 of 10 policy scenarios correct, including the adversarial set; no false allow before the deadline |
| RQ4 cost and latency | Latency, model calls per request, and paid-call cost reported; BM25, dense, and hybrid ablation reported |
| RQ5 grading assistance | Per-criterion agreement with the TA reference scores on 5 to 10 constructed submissions, evidence validity (line references exist, tests ran), TA edit rate reported, and at least one grading failure analyzed |
| Failure analysis | At least one dominant failure mode analyzed with trace evidence |
| Course deliverable check | Frontend, backend, evaluation, tested demo including one grading batch, and a runnable repository are all demonstrated |

## 9. Milestones

There is no published presentation or submission date. Work is ordered in four workstreams; a workstream is complete when its acceptance items in section 5 pass.

1. **Corpus, index, and access.** TACC OCR and index jobs, retrieval, accounts, sessions, and the local run path.
2. **Agent and policy.** LangGraph graph, disclosure gate, deadline registry, evidence verification, work chain, and model control.
3. **Practice, teaching, voice, and grading.** MPI pack, test runner, explainer, study aids, microphone and speech output, assignment package ingestion, the Docker grading sandbox, and the TA workbench.
4. **Evaluation and delivery.** Benchmark, evaluation harness including RQ5 grading, local Langfuse traces, report and figures, demo runbook with one grading batch, replay fallback.

## 10. Open questions

- The TA reply on (a) SSH forwarding to a student-run web port and (b) whether the final demo must run the backend on TACC is pending. The local backend is the demo mode until then.
- Allowed registration domains are set to `connect.ust.hk` and `ust.hk` as a default; confirm if the course uses another domain.
- The email flow is set to a six digit code for registration and a one-time link for reset; confirm if a link is preferred for both.
- The Langfuse stack disk usage is estimated at 5 to 10 GB; measure once the stack is first started.
- The SQLite checkpointer depends on the native sqlite-vec extension; the TACC import spike is pending (ADR-0008).
- The practice pack set beyond the first MPI pack is P2; the report states the pack scope.
- The grading assistant is planned as P1 after the student tutoring loop: code assignments first, written assignments P2, TA bulk upload only (no student submission portal), and a local Docker sandbox only (no TACC grading). Confirm or adjust.
- Grading quality evidence uses 5 to 10 constructed submissions scored by a team member as the TA reference, because no historical submissions exist yet.
- Multi-course support is recorded as future development in section 3, not implemented.

## 11. Related documents

- Proposal: [../proposal/proposal.md](../proposal/proposal.md)
- Technology selection: [tech-selection.md](tech-selection.md)
- Decision records: [adr/](adr/)
- TA grading assistant decision: [ADR-0010](adr/0010-ta-grading-agent.md)
- Grading execution sandbox: [ADR-0011](adr/0011-grading-execution-sandbox.md)
- Local Langfuse runbook: [langfuse-local.md](langfuse-local.md)
- Local email runbook: [email-local.md](email-local.md)
- Agent rules: [../AGENTS.md](../AGENTS.md)
- Domain vocabulary: [../GLOSSARY.md](../GLOSSARY.md)
