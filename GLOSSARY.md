# Verifiable tutor

Vocabulary for the course-grounded tutoring agent. It is a single-context repository: this glossary and the ADRs in [`docs/adr/`](docs/adr/) are the domain documentation.

## Language

**Answer**:
A response to a student's message that contains course content. An answer is either verified, partially verified with named gaps, or an abstention.
_Avoid_: Reply, completion, output

**Citation**:
A reference from a claim in an answer to one document, one page, and one quoted span. A citation without a quoted span is not a citation.
_Avoid_: Source, reference, footnote

**Quoted span**:
The exact text from the OCR page that a citation rests on. It must occur on the cited page after whitespace and case normalization.
_Avoid_: Snippet, excerpt, quote

**Span verifier**:
The deterministic check that compares a quoted span with the cited page text and decides whether the citation stands.
_Avoid_: Fact checker, hallucination filter

**Repair round**:
The single retry in which the agent corrects citations that failed verification before it abstains.
_Avoid_: Retry, regeneration

**Abstention**:
An answer that states it cannot support the requested claim with evidence, and names what is missing, instead of guessing.
_Avoid_: Refusal, fallback answer

**Disclosure gate**:
The code-level decision that maps a request and a policy state to what may be revealed. It is not a prompt instruction.
_Avoid_: Content filter, moderation

**Policy state**:
One of the five values the disclosure gate derives from the deadline registry: pre-release, active, extension window, post-deadline, or unknown.
_Avoid_: Phase, status

**Deadline registry**:
The versioned configuration that records each assignment's release date, due date, extensions, and the resulting policy state.
_Avoid_: Calendar, schedule, config

**Intent class**:
The category the router assigns to a request: course question, homework solution request, pasted solution, post-deadline teaching request, or other.
_Avoid_: Label, category

**Hint**:
A pre-deadline response that moves the student toward the solution without supplying it.
_Avoid_: Answer, partial solution

**Practice pack**:
A generated practice artifact that mirrors one assignment's environment, or a self-test question set over a topic: toolchain, source layout, datasets, test harness, and reference answers.
_Avoid_: Exercise set, tutorial, sandbox

**Self-test question**:
A generated question the student answers and the agent grades. The types are single choice, multiple choice, true or false, short answer, and code. The self-test feature and the practice lab are the same capability.
_Avoid_: Quiz item, exercise, test

**Answer grading**:
The agent's judgement of a student's answer: a score, an explanation, and a citation to the course material that supports the correct answer. Code answers are graded from recorded TACC test results.
_Avoid_: Correction, marking, auto-grading

**TACC execution job**:
A TACC job that runs reference tests and self-test code answers on the platform and writes results to `USERDIR`. The local backend submits it, polls it, and downloads the results.
_Avoid_: Sandbox, runner, worker

**Offline TACC job**:
A submitted batch job that produces artifacts, such as OCR page records, embedding vectors, execution results, or evaluation output, which are downloaded to the laptop and read by the local backend. It serves no requests and exits when it finishes.
_Avoid_: TACC service, deployment, hosted backend

**TACC model-serving backend**:
A model that runs inside a submitted TACC job and whose output the local application uses. The project serves BGE-M3 for the index and Qwen for the knowledge base; no inbound service or SSH forwarding is used, and each job exits when it finishes.
_Avoid_: Hosted model, served endpoint, TACC web service

**Knowledge base**:
The local store of cited course knowledge cards that Qwen builds on TACC from course chunks. The agent uses it for review outlines and self-tests, and students can browse it.
_Avoid_: Vector store, document store

**Knowledge card**:
One validated knowledge record for a page or section: a summary, key terms, study questions, and page citations, produced by the Qwen knowledge-base job and stored locally.
_Avoid_: Note, flashcard, summary row

**Knowledge-base build job**:
One submitted TACC GPU job that loads Qwen through vLLM, reads a request and course chunks from `USERDIR`, writes knowledge records and progress, and exits. The local backend submits it, polls it, downloads the result, validates it, and stores it.
_Avoid_: Qwen endpoint, inference service

**Reference solution**:
A solution to a practice exercise that is shown only after it compiled and passed the pack's tests.
_Avoid_: Solution, answer key

**Explainer**:
The line-anchored teaching output over a student's own submitted solution.
_Avoid_: Grader, feedback, review

**Work chain**:
The ordered, persisted record of what the agent did for one answer: each model reasoning segment and each tool call, grouped under the work-chain step it belongs to. The expanded chain shows one section per step that actually exists, in the canonical phase order, with that step's events in order under it. A step with no events still shows its section. It survives history reload and replay.
_Avoid_: Trace, log, debug view

**Work-chain event**:
One entry in the work chain, either a reasoning segment from one model call or one tool call. Each event carries the id of the work-chain step it belongs to and is stored in order (ADR-0017, ADR-0019).
_Avoid_: Step, timeline item

**Thinking**:
The model's reasoning content streamed before the answer. It is stored as a work-chain event before the tool calls of the same model call and shown as unverified model output, not as a citation.
_Avoid_: Chain of thought, reasoning trace, scratchpad

**Tool call**:
A typed action the agent asks the backend to execute, such as retrieving pages or running a practice test. The work chain shows its arguments, command line, exit code, and output.
_Avoid_: Function call, command execution, shell

**Session trace**:
The JSONL record of one conversation's events, used for replay and evaluation. It is the canonical record; the Langfuse trace is a development inspection layer.
_Avoid_: Log file, transcript, telemetry

**Replay**:
Re-emitting a recorded session trace through the normal frontend and backend path without model calls.
_Avoid_: Rerun, mock mode

**Benchmark question**:
One of the 50 evaluation inputs with its expected evidence, used to measure RQ1 and RQ4.
_Avoid_: Test case, prompt, fixture

**Policy scenario**:
One of the 10 evaluation cases for the disclosure gate, including adversarial attempts to bypass it.
_Avoid_: Test case, prompt

**Run**:
One execution of the evaluation harness over a benchmark file, identified by a run id and stored with model, corpus, and configuration versions.
_Avoid_: Experiment, benchmark

**Student account**:
A registered user identified by a student email address.
_Avoid_: User, member, customer

**Instructor account**:
The seeded role that owns the deadline registry and can read policy state.
_Avoid_: Admin, teacher, TA account

**Model profile**:
A selectable combination of provider, tier, and thinking level, such as DeepSeek Flash with thinking off or MiMo Pro with thinking high.
_Avoid_: Model, backend, provider
