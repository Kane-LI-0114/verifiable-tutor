# Benchmark data schema: self-test

Owner: this file is the field-level contract for the RQ2 benchmark data under
`benchmarks/self_test/`. [benchmark-protocol.md](benchmark-protocol.md) owns the
procedure and the directory layout; this file owns the record shapes.

Status: draft, 2026-11-15. Owner: TIAN Yujia.

## Directory layout

```
benchmarks/self_test/
  generation/
    <run-id>/prompt.txt
    <run-id>/system-a.jsonl
    <run-id>/system-b.jsonl
    <run-id>/transcripts/
    <run-id>/annotations.jsonl
    <run-id>/metrics.json
  grading_shared/
    <run-id>/questions.jsonl
    <run-id>/answers.jsonl
    <run-id>/grading_prompt.txt
    <run-id>/system-a-grades.jsonl
    <run-id>/system-b-grades.jsonl
    <run-id>/ground_truth.jsonl
    <run-id>/metrics.json
    <run-id>/failures.md
```

Every `.jsonl` file is one JSON object per line. Fields are `snake_case`.

## Question record

Written by both systems to `generation/<run-id>/system-a.jsonl` and
`system-b.jsonl`. One object per generated question.

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | Unique id, prefixed by source, e.g. `a-001`, `b-001` |
| `type` | string | `single_choice` / `multiple_choice` / `true_false` / `short_answer` / `code` |
| `topic` | string | Topic brief used, e.g. `memory hierarchy` |
| `question_text` | string | The question body |
| `options` | array of string or null | Choices for choice types; null otherwise |
| `reference_answer` | string | The reference answer |
| `scoring_points` | array of string | Itemized scoring points |
| `max_score` | number | Maximum score for the question |
| `citation` | object or null | `{doc_id, page_no, span}`; null when the system cites nothing |
| `reference_verified` | boolean or null | Reference answer compiled and passed tests where applicable; null when not applicable |
| `citation_verified` | boolean or null | Citation passed the span verifier; null when the citation is absent or unverified |
| `source` | string | `A` or `B`; hidden during annotation |

`citation` object:

| Field | Type | Meaning |
|---|---|---|
| `doc_id` | string | Course document identifier |
| `page_no` | integer or null | Page number when available |
| `span` | string or null | Quoted span; verified for system A only |

## Annotation record

`generation/<run-id>/annotations.jsonl`. One object per question, produced
blind by two annotators.

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | Matches a question record |
| `knowledge_points` | array of string | Covered knowledge points, mapped to the course list |
| `valid` | boolean | Answerable, reference correct, no duplicate, no assignment leak |
| `validity_notes` | array of string | Reasons when `valid` is false |
| `difficulty` | string | `low` / `medium` / `high` |
| `annotator` | string | De-identified annotator id |
| `verified_max_score` | number | Confirmed maximum score |

## RQ2a metrics

`generation/<run-id>/metrics.json`. One object.

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | Run identifier |
| `date` | string | ISO date of the run |
| `model` | string | Model used for generation |
| `knowledge_point_coverage` | number | Covered / expected knowledge points |
| `question_validity_rate` | number | Valid / all questions |
| `reference_answer_verifiability` | number | Share with verifiable reference answer |
| `citation_validity` | number or null | Share of A citations passing the span verifier; null for B |
| `generation_cost_per_question` | number | Paid-call cost per question |
| `generation_latency_per_question` | number | Latency per question |

## Shared question record

`grading_shared/<run-id>/questions.jsonl`. Frozen sample of eight questions,
source labels hidden and order shuffled.

Same fields as the question record, plus:

| Field | Type | Meaning |
|---|---|---|
| `shared_id` | string | Frozen id after shuffle, e.g. `s-01` |

`source` is omitted from the shared set until the annotation join.

## Answer record

`grading_shared/<run-id>/answers.jsonl`. Simulated student answers.

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | Matches a shared question |
| `variant` | string | `correct` / `partially_correct` / `wrong` / `ambiguous` |
| `answer_text` | string | The simulated student answer |
| `simulator` | string | Model id used for simulation, e.g. `mimo-v2.6-pro` |
| `simulator_date` | string | ISO date of simulation |

## Grade record

`grading_shared/<run-id>/system-a-grades.jsonl` and `system-b-grades.jsonl`.

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | Matches a shared question |
| `variant` | string | Answer variant graded |
| `score` | number | Score assigned by the grader |
| `explanation` | string | Short grading explanation |
| `citation` | object or null | `{doc_id, page_no, span}`; null for B |
| `grader` | string | `A` or `B` |

## Ground-truth record

`grading_shared/<run-id>/ground_truth.jsonl`. Developer scores, hidden from
both graders and the simulator.

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | Matches a shared question |
| `variant` | string | Answer variant |
| `score` | number | Final ground-truth score |
| `matched_scoring_points` | array of string | Scoring points the answer satisfies |

## RQ2b metrics

`grading_shared/<run-id>/metrics.json`. One object.

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | Run identifier |
| `exact_match_rate` | number | Exact score matches / items |
| `within_one_point_agreement` | number | Within-one-point agreement |
| `normalized_mae` | number | Mean absolute error, normalized by max score |
| `scoring_point_agreement` | number or null | Criterion-level agreement when the rubric is itemized |
| `false_pass_rate` | number | Wrong answers scored as correct |
| `false_fail_rate` | number | Correct answers scored as wrong |
| `citation_validity` | number or null | Share of A citations passing the span verifier |
| `grading_latency_per_item` | number | Latency per graded item |
| `grading_cost_per_item` | number | Paid-call cost per graded item |
