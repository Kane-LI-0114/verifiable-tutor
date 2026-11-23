# RQ2 self-test evaluation checklist

Operational checklist from benchmark-protocol.md section 8. Work top to bottom;
each step names its output.

## 1. Confirm models and access dates

- [ ] A runs `deepseek-flash` (record model id + date).
- [ ] B shows DeepSeek Flash selected in the web UI, captured in a screenshot
      (`model-selector.png`).
- [ ] Simulator is `mimo-v2.6-pro` (record model id + date).

## 2. Generate both question sets

- [ ] Same task prompt for A and B, one topic per run.
- [ ] Give B the topic's course PDF as an uploaded attachment (see
      benchmark-protocol.md section 2 and 3).
- [ ] Save `generation/<run-id>/system-a.jsonl`.
- [ ] Save `generation/<run-id>/system-b.jsonl` (typed from the web transcript).
- [ ] Save raw transcripts and screenshots under `transcripts/`.

## 3. Annotate both sets blind

- [ ] Follow `annotation_template.md`.
- [ ] Save `generation/<run-id>/annotations.jsonl`.

## 4. Freeze the shared set

- [ ] Sample 8 questions (4 from A, 4 from B), source hidden, shuffled.
- [ ] At least one of each type + two code questions.
- [ ] Save `grading_shared/<run-id>/questions.jsonl`.

## 5. Simulate student answers

- [ ] Run `python scripts/simulate_student_answers.py grading_shared/<run-id>`.
- [ ] Four variants per question (`correct`, `partially_correct`, `wrong`,
      `ambiguous`).
- [ ] Save `grading_shared/<run-id>/answers.jsonl`.

## 6. Score developer ground truth

- [ ] Two annotators score every frozen item against the scoring points.
- [ ] Resolve disagreements by discussion.
- [ ] Save `grading_shared/<run-id>/ground_truth.jsonl`.

## 7. Run both graders

- [ ] A grades with the project agent; save `system-a-grades.jsonl`.
- [ ] B grades with the DeepSeek web UI; save `system-b-grades.jsonl`.
- [ ] Never show either grader the ground truth first.

## 8. Compute metrics

- [ ] `python -m verifiable_tutor.eval.cli rq2a generation/<run-id> --expected-points N`
- [ ] `python -m verifiable_tutor.eval.cli rq2b grading_shared/<run-id> --grader a`
- [ ] `python -m verifiable_tutor.eval.cli rq2b grading_shared/<run-id> --grader b`
- [ ] Save the generated `metrics.json` beside each run.
- [ ] Write a short failure note (`failures.md`).

## 9. Report

- [ ] Add RQ2a and RQ2b result tables.
- [ ] Fill the A-vs-B capability table.
- [ ] State every limitation from benchmark-protocol.md section 9.
