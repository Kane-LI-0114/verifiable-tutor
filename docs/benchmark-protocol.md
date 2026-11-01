# Benchmark protocol: self-test generation and grading

Status: draft, version 0.3, 2026-10-29. Owner: LI Jinchuan. This protocol implements RQ2 in [docs/prd.md](prd.md#8-acceptance-and-evaluation-targets). The PRD owns the requirement and the target values; this file owns the procedure and the data layout.

## 1. Purpose

This benchmark asks one question for a student: does using our agent produce a measurably better self-test loop than using the external chatbot? It is not a test of whether a chatbot can write questions, because a current chatbot can. It tests whether the agent's design (course retrieval, citation and span verification, reference-answer verification, TACC execution of code answers, and rubric-grounded grading) turns the same task into material a student can use without correction.

RQ2 is split into:

- **RQ2a self-test generation quality.** Are the generated questions valid, answerable, grounded in the course, and do they cover the intended knowledge points, and how much of that does each system deliver?
- **RQ2b grading agreement.** Given the same questions and the same answers, does the agent grade them closer to the developer ground truth than the external chatbot, and is the grading evidence valid?

The comparison is deliberately a small-sample, course-project benchmark. It reports the agent and the chatbot side by side, including the capability gap. It does not start from the assumption that the agent wins, and a tie is reported as a tie.

## 2. Systems under test

| Code | System | Prompt and settings |
|---|---|---|
| A | Our agent (course corpus, retrieval, verification, LangGraph workflow) | Project system prompt and tools; model `deepseek-flash` by default; thinking off; temperature 0; the task prompt is identical to the one given to B |
| B | DeepSeek web version (external chatbot) | DeepSeek web UI with the **DeepSeek Flash model selected**. The model is held constant with A and was confirmed for this evaluation on 2026-10-29. Record the access date, the model selector screenshot, and any visible model label. The web product still applies its own system prompt and may use search; the task prompt is identical to the one given to A |

Both systems receive the same user task prompt. The agent's system prompt, retrieval, tools, and verification are part of system A and must not be copied into the prompt given to B. Record every raw prompt and output, and take screenshots for the web session.

The model is held constant: A runs `deepseek-flash` and B runs the DeepSeek web UI with the DeepSeek Flash model selected, confirmed on 2026-10-29. The comparison therefore isolates system design (system prompt, retrieval, tools, verification) rather than model capability. It is still a product-level baseline, because the web product applies its own system prompt, may use search, and does not expose the same knobs. The report states this limitation and keeps the raw transcripts and model-selector screenshots so the comparison can be re-read. If the web UI cannot prove the Flash selection on the run day, the run is recorded as a different-model baseline and is not used for the RQ2b target.

## 3. RQ2a: generation protocol

1. **Topics.** Choose two course topics from the knowledge point list, for example memory hierarchy and FlashAttention. Use the same topic brief for A and B.
2. **Task prompt.** One prompt template, used verbatim for both systems:

   > Generate 10 self-test questions for CSIT6000V on the topic "<topic>". Cover the topic's key knowledge points. Use a mix of single choice, multiple choice, true or false, short answer, and code questions. For every question, give the reference answer, the scoring points, and the course source (lecture, tutorial, or assignment) it comes from. Do not reveal a complete solution to a current assignment.

   The prompt above is the user prompt. System A adds its own system prompt; system B uses its own product behaviour. Neither side receives extra hints.
3. **Collection.** Save the questions, reference answers, scoring points, and citations for A; save the raw chat transcript and screenshots for B. Run both on the same day and record the date and observed model/version.
4. **Annotation.** Two team members annotate each question set independently:
   - knowledge points covered, mapped to the course knowledge point list;
   - question validity: answerable, reference answer correct, no duplicate, no current-assignment leak;
   - scoring points and maximum score per question;
   - difficulty, low, medium, or high.
   Question sets are de-identified (randomized IDs, source hidden) during annotation; the ID to source mapping is kept separate and only joined after annotation.
5. **RQ2a metrics.**
   - knowledge point coverage: covered knowledge points divided by the expected points for the topic;
   - question validity rate: valid questions divided by all questions;
   - reference-answer verifiability: share whose reference answer compiles and passes tests where applicable;
   - citation validity: share of agent citations that pass the span verifier (A only; B may not cite);
   - generation cost and latency per question.

## 4. RQ2b: shared grading set

Grading is compared under condition B from the design discussion: one fixed question set, one fixed answer set, both systems grade the same items.

1. **Shared question set.** Sample eight questions from the two generated sets, four from each system, with source labels hidden and order shuffled. Include at least one question of each type and two code questions. Freeze the set before grading.
2. **Shared answer set.** Simulated student answers are produced by a language model role-play, not by a human, and this is disclosed in the report.
   - Simulator: Xiaomi MiMo Pro (`mimo-v2.6-pro`) through the project API, temperature 0.3, same prompt for every item; record the model version and date. A different model family from the graders reduces same-model familiarity bias. If MiMo is unavailable, use another non-DeepSeek model and record the substitution.
   - For every question, the simulator produces four variants: a correct answer, a partially correct answer, a wrong answer, and an ambiguous or edge answer. The simulator does not see the scoring points or the ground truth, and the prompt forbids it from using external search.
   - Answers are de-identified and frozen before grading. Code answers are not executed for RQ2b; grading uses the stated answer and, where relevant, the recorded test-output fallback.
3. **Graders.** Both systems grade the same frozen items:
   - Grading prompt: the question, the answer, the rubric or scoring points, and the maximum score, identical for A and B. Ask for a score per item, a short explanation, and, for A, a citation. B receives the same user grading prompt; its product system prompt is its own.
   - Run each grader once, record raw outputs and timestamps. Do not show either grader the developer scores first.
   - For code questions, system A may use the `tacc/exec` path; if execution is unavailable, grade from the stated answer and record the fallback.
4. **Developer ground truth.** Before grading outputs are joined, two team members score every frozen item against the scoring points. Disagreements are resolved by discussion and the final score is stored as the ground truth. Ground truth is hidden from both graders and from the answer simulator.
5. **RQ2b metrics.**
   - exact score match rate with the ground truth;
   - within-one-point agreement (or within 10 percent of maximum score);
   - mean absolute error, normalized by the maximum score;
   - criterion or scoring-point level agreement where the rubric is itemized;
   - false-pass rate: wrong answers scored as correct;
   - false-fail rate: correct answers scored as wrong;
   - citation validity for A, and explanation completeness on a small sample;
   - grading latency and paid-call cost per item.

## 5. Target values

Target values are provisional until the first run. They live in the PRD; this protocol only defines how they are measured. The initial PRD targets:

- RQ2a: at or above 0.90 of generated questions have a verifiable reference answer; knowledge point coverage reported; environment alignment and cost reported.
- RQ2b: within-one-point agreement at or above 0.85, normalized MAE at or below 0.10, false-pass at or below 0.05, and 100 percent citation validity for A on the shared set.
- Both: at least one failure analyzed by cause.

## 6. Capability gap and student usefulness

Beyond the per-system scores, report what each system can actually deliver to a student. These are the capabilities that distinguish the agent from a plain chatbot; they are reported as measured evidence, not as an assertion.

- **Verified reference answers.** Developers verify every generated question's reference answer, running tests where applicable. Report the share that passes for both systems.
- **Grounding.** Share of generated questions with a course source that passes the citation check. If the chatbot does not cite course pages, record the capability as absent and report the measured share for the agent; do not score the absence as zero quality.
- **Execution evidence.** Share of code questions whose reference answer or student answer actually ran on a test harness. The agent can use `tacc/exec`; the chatbot has no execution path, and that is recorded as absent.
- **Grounded grading.** Share of grading explanations with a course citation that passes the span verifier, and share of code grades backed by a recorded execution result. Report the agent's share and record the chatbot's absence.
- **Student usability.** Developers rate a sample of generated questions and graded items as usable as-is or requiring correction, looking for factual errors, ambiguity, missing answers, and feedback a student cannot act on.
- **Capability table.** A side-by-side table marks each capability for A and B as supported, partial, or absent, with the measured evidence beside it.

The report states the measured difference. If the chatbot matches the agent on a metric, that is reported as a tie; the protocol does not assume an advantage.

## 7. Data layout

All benchmark data stays under `benchmarks/self_test/`. Only small, curated results are committed; raw web transcripts and large simulated-answer batches are staged and summarized.

```
benchmarks/self_test/
  generation/
    <run-id>/prompt.txt
    <run-id>/system-a.jsonl        questions, reference answers, scoring points, citations
    <run-id>/system-b.jsonl        questions and reference answers typed from the web transcript
    <run-id>/transcripts/          raw web transcripts and screenshots
    <run-id>/annotations.jsonl     knowledge points, validity, scoring points, difficulty
    <run-id>/metrics.json
  grading_shared/
    <run-id>/questions.jsonl       frozen shared question set
    <run-id>/answers.jsonl         frozen simulated answers with variant labels
    <run-id>/grading_prompt.txt    the prompt given to both graders
    <run-id>/system-a-grades.jsonl
    <run-id>/system-b-grades.jsonl
    <run-id>/ground_truth.jsonl
    <run-id>/metrics.json
    <run-id>/failures.md
```

`benchmarks/results/` stays for the small machine-readable result files that the report cites.

When a run uses the course knowledge base as context, record the `build_id`, corpus hash, prompt version, model, and TACC job id in the run metadata. TACC queue, cold-start, and build times are reported under RQ4 ([knowledge-schema.md](knowledge-schema.md)).

## 8. Procedure checklist

1. Confirm model versions and access dates for A, B, and the simulator. A must run `deepseek-flash`; B must show the DeepSeek Flash selection in the web UI and be captured in a screenshot before the run.
2. Generate both question sets with the same task prompt; save raw outputs.
3. Annotate both sets blind, join the source mapping afterwards.
4. Freeze eight shared questions and their four answer variants.
5. Score the frozen items as developer ground truth.
6. Run both graders on the frozen items; save raw outputs.
7. Compute RQ2a and RQ2b metrics into JSON; write a short failure note.
8. Add the results tables to the report and state every limitation below.

## 9. Limitations

- **Same model, different product scaffolding.** A and B use DeepSeek Flash, so model capability is held constant, but the web product has its own system prompt, retrieval, and search behaviour while the agent has retrieval, verification, and typed tools. The comparison is a product-level comparison of system design, not a controlled model-only experiment. If the web selection cannot be verified on the run day, the run is marked as a different-model baseline.
- **Simulated students.** Answers are generated by a model role-play, not real students; the report discloses the simulator, model version, and prompt.
- **Small sample.** Two topics, twenty generated questions in total, eight shared questions, and thirty-two frozen items. The result is a course-project signal, not a validated benchmark.
- **Developer annotations.** Two team members annotate and score; randomization and blind annotation reduce, but do not remove, bias.
- **Web instability.** The web UI and the served model may change between runs; raw transcripts and dates are the only reproducibility mechanism for B.
- **No human answer quality.** The protocol measures generated questions and grading agreement, not learning gains for students.
- **A negative result is valid.** The comparison is designed to test whether the agent adds measurable value. If the chatbot matches or beats the agent, that is reported; prompts and metrics are not tuned after seeing the results.

## 10. Appendix: optional controlled API arm

The web baseline mixes the model with the web product's own system prompt, retrieval, and search. To separate that scaffolding from the agent's design, run one supplementary arm. It is never used for the RQ2 target values.

- **Generation.** Call the DeepSeek API directly at `https://api.deepseek.com/v1/chat/completions` with model `deepseek-flash`, the same user task prompt, temperature 0, thinking off, and no `tools` field and no search. Do not add a project system prompt; if the API requires one, use an empty or minimal prompt and record it verbatim.
- **Grading.** Use the same grading prompt, rubric, and answers as condition B, again with no tools and no search.
- **Recording.** Save the request JSON, the response JSON, the model id, the date, and the parameters. Report this arm beside A and B, labelled as the controlled API arm, and never merge it into the main comparison.
- **Reading.** If A beats this arm, the gain is attributable to the agent design (retrieval, verification, execution, and citations). If A only beats the web arm, the gain is attributable to product scaffolding. Either result is reported.
