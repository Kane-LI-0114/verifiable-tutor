# ADR-0010: TA grading assistant with evidence and human approval

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-29 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The course project originally covered the student side only. The lead added a TA-side grading assistant on 2026-10-29: a TA uploads an assignment package and a batch of student submissions, and the assistant proposes per-criterion scores with evidence, a feedback draft, and a confidence value. This is an extension beyond the frozen proposal, and the report explains the deviation.

Grading decisions have consequences that a tutoring answer does not: a wrong score harms a student, and an unexplained score invites appeals. The project already has the ingredients for a verifiable grading flow: the model layer with retries and caching ([ADR-0005](0005-external-model-apis-as-primary.md), [ADR-0006](0006-same-model-retries-without-cross-model-fallback.md)), the LangGraph orchestration runtime ([ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)), typed tools with a restricted runner ([ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md)), and local tracing ([ADR-0007](0007-langfuse-for-local-model-call-tracing.md)).

The platform constrains the design: the deployment is single-node and local-only for the demo, TACC provides no strong sandbox for untrusted code (see [ADR-0011](0011-grading-execution-sandbox.md)), and there is no historical submission data to calibrate an automatic grader.

The requirements are in [docs/prd.md](../prd.md), section 5.7.

## Decision

- The grading assistant is a separate TA-side LangGraph workflow, not a branch of the student tutoring graph. It has its own tools, its own authorization checks, and its own trace stream.
- An assignment package is the unit of grading: title, rubric criteria with maximum points, a test harness or reference solution, and the runtime image. The TA authors it once per assignment.
- Submissions arrive as a TA-uploaded batch (a zip or a file set with a student identifier). There is no student-facing upload in this deliverable; that is future development.
- For each submission the assistant produces a grade recommendation: a score per rubric criterion, the evidence for each score (file and line references for code, test commands and outcomes, rubric notes), a feedback draft, and a confidence value. The recommendation is never a grade.
- Every score is checked against evidence: a line reference must exist in the submitted file, and a test outcome must come from a recorded run. A recommendation without evidence is downgraded or left to the TA.
- Code submissions run only in the Docker sandbox from [ADR-0011](0011-grading-execution-sandbox.md); written submissions are rubric-graded from the submission text and are P2.
- A TA reviews the recommendation in a workbench, accepts, edits, or rejects each item, and approves the submission. Only approved grades can be exported as CSV. An approved record is immutable except through an audit-logged revision.
- The audit log records every assistant suggestion, TA edit, approval, and export with the acting account and timestamp. It is the record an appeal would use.
- Grading data, submissions, and grading traces are visible only to the TA role. Student identifiers are pseudonymized in traces. The student-facing tutor cannot read grading data.
- There is no automatic publication, no plagiarism detection, and no gradebook integration beyond the CSV export.
- Grading quality is measured as RQ5: per-criterion agreement with a TA reference on a small constructed sample, evidence validity, and the TA edit rate.

## Consequences

**Positive:**

- The TA keeps authority over every grade, while the assistant removes most of the mechanical reading, running, and rubric application.
- Evidence-first recommendations make scores explainable and appealable, which manual grading rarely records.
- The same model, tool, tracing, and audit patterns as the student side are reused, so the second workflow is cheaper than the first.
- Approved grades are exportable, and the audit log makes changes traceable.

**Negative:**

- The grading workflow adds a second UI surface, a second LangGraph graph, new data tables, and a Docker dependency for execution, which is a large addition to a course project.
- Grading quality depends on the assignment package: a vague rubric or a broken test harness produces bad recommendations, and the TA still has to invest in the package.
- Running student code locally differs from the course TACC environment, so environment alignment must be recorded and explained.
- A small constructed sample cannot prove grading quality at scale; the report states the limitation.

**Neutral:**

- The student tutoring product is unchanged; grading is an additional role-specific workflow over the same platform.

**Follow-up:**

- Define the assignment package schema, the rubric structure, and the recommendation schema with pydantic models and tests at the package and recommendation seams.
- Build the Docker sandbox runner from [ADR-0011](0011-grading-execution-sandbox.md) and record image and toolchain versions per run.
- Add the audit log and the CSV export, and verify that no path exports an unapproved grade.
- Define RQ5 and build the 5 to 10 constructed submissions with a TA reference score set.

## Alternatives considered

**Manual grading only.** For: no new surface, no untrusted code execution, and full TA judgement. Against: the original problem (TA scarcity, inconsistent feedback, unrecorded evidence) remains, and the lead asked for the assistant; not chosen.

**Unattended automatic grading.** For: the least TA effort. Against: a wrong grade would be final, evidence would be optional, and appeals would be impossible; the project rejects it as a non-goal (PRD section 3).

**Prompt-only rubric scoring without evidence or execution.** For: the simplest possible implementation with no Docker. Against: scores would be unverifiable, code correctness would never be checked, and the same trust problem as an ungrounded tutoring answer appears; used only for written submissions in P2, never as the main path.

**External grading platform or gradebook.** For: mature workflows and integrations. Against: data leaves the laptop, the course does not reimburse services, and the project needs its own evaluable system; CSV export covers the course need.

**Run tests in the TACC job container.** For: the same environment as the course. Against: TACC provides no strong sandbox for third-party code, and the one-hour job and queue make interactive grading impractical; rejected in [ADR-0011](0011-grading-execution-sandbox.md).

## References

- Product requirements, including grading requirements FR-K1 to FR-K9: [../prd.md](../prd.md)
- Execution sandbox: [ADR-0011](0011-grading-execution-sandbox.md)
- Typed agent tools: [ADR-0009](0009-typed-agent-tools-instead-of-a-shell.md)
- Orchestration runtime: [ADR-0008](0008-langgraph-as-agent-orchestration-runtime.md)
- Local tracing: [ADR-0007](0007-langfuse-for-local-model-call-tracing.md)
- Model layer: [ADR-0005](0005-external-model-apis-as-primary.md), [ADR-0006](0006-same-model-retries-without-cross-model-fallback.md)
