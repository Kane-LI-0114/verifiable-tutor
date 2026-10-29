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
A bundle that mirrors one assignment's environment: toolchain, source layout, datasets, and a test harness.
_Avoid_: Exercise set, tutorial, sandbox

**Reference solution**:
A solution to a practice exercise that is shown only after it compiled and passed the pack's tests.
_Avoid_: Solution, answer key

**Explainer**:
The line-anchored teaching output over a student's own submitted solution.
_Avoid_: Grader, feedback, review

**Work chain**:
The user-visible sequence of agent steps, model thinking, and tool calls that produced an answer.
_Avoid_: Trace, log, debug view

**Thinking**:
The model's reasoning content streamed before the answer. It is shown as unverified model output, not as a citation.
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
The seeded role that owns the deadline registry, reads policy state, and runs the grading assistant.
_Avoid_: Admin, teacher, TA account

**Model profile**:
A selectable combination of provider, tier, and thinking level, such as DeepSeek Flash with thinking off or MiMo Pro with thinking high.
_Avoid_: Model, backend, provider

**Assignment package**:
The TA-authored bundle for one assignment: the statement, the rubric, the tests or reference solution, and the runtime image.
_Avoid_: Assignment, exercise, task

**Rubric**:
The ordered list of grading criteria with maximum points used to score a submission.
_Avoid_: Grading scheme, checklist

**Criterion**:
One rubric item with its maximum points and the evidence accepted for it.
_Avoid_: Item, category

**Submission**:
One student's uploaded work for one assignment, identified by a student identifier and stored for TA review.
_Avoid_: Answer, solution, upload

**Grade recommendation**:
The assistant's per-criterion score, evidence, feedback draft, and confidence for one submission. It becomes a grade only after TA approval.
_Avoid_: Grade, score, mark

**Grading run**:
One execution of the grading assistant over one assignment batch, identified by a run id and recorded with the package, image, model, and prompt versions.
_Avoid_: Batch, job, evaluation

**TA workbench**:
The instructor-side interface for reviewing, editing, and approving grade recommendations and exporting results.
_Avoid_: Admin panel, dashboard

**Audit log**:
The append-only record of every grading suggestion, edit, approval, and export, with the acting account and time.
_Avoid_: History, changelog
