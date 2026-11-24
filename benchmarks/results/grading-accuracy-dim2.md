# Grading accuracy: dimension 2

Grading-accuracy experiment for the practice evaluation
([evaluation-plan.md](../../docs/evaluation-plan.md), Part 2.2).

- Date: 2026-11-23
- Setup: 11 generated single-choice questions, each answered correctly and
  wrongly, giving 22 graded samples.
- Treatment paths measured:
  - deterministic grading (the frontend choice scorer), and
  - model grading (`POST /api/practice/runs`, DeepSeek).
- Ground truth: a correct choice earns full marks, a wrong choice earns 0.

## Result 1: grading now cites sources (Part 3 enabler)

The model-grading explanation now carries `[ref_N]` citations, for example
"matching the course's stated core algorithmic idea ... [ref_2]". This is the
prerequisite for the citation-accuracy dimension (Part 3).

## Result 2: deterministic grading misjudges (63.6%)

The frontend deterministic scorer compares the first letter of the reference
answer, but the reference answer is a full sentence (for example "Naive
attention ... Materializes ..."), not an option letter, so the comparison is
wrong in 8 of 22 samples.

| Kind | Count | Examples |
|---|---|---|
| correct answer scored 0 | 5 | Q2, Q3, Q4, Q5, Q11 |
| wrong answer scored full | 3 | Q7, Q8, Q10 |
| exact | 14 | the rest |

## Result 3: model grading is mostly right but under-scores (72.7%)

The DeepSeek grader scored 16 of 22 exactly. Its failures are almost all
under-scoring a correct answer, not over-scoring a wrong one.

| Kind | Count | Examples |
|---|---|---|
| correct answer under-scored | 5 | Q4 1/2, Q5 2/3, Q7 2/3, Q9 2/3, Q10 1/2 |
| wrong answer over-scored | 1 | Q11 1/3 |
| exact | 16 | the rest |

## Raw data

The 22 samples (per-question answer, model score, deterministic score,
expected score, and explanation) are in
[part2_dim2_grading.jsonl](part2_dim2_grading.jsonl).

## Conclusion

The deterministic choice scorer needs a fix (it does not know the correct
choice), and the model grader under-scores correct answers because it applies
scoring points that a choice question cannot satisfy. Both are actionable for
the next iteration.

## Fix applied

The generator now emits a `correct_answer` field for choice questions, and the
frontend deterministic scorer compares the student's selection against it by
exact match instead of by first letter. Choice questions no longer go through
the model grader. Regenerating 10 single-choice questions produced a valid
`correct_answer` on all 10, and the deterministic scorer was exact on all 10
correct and wrong answers, bringing the treatment's choice grading to 100%
accuracy.

