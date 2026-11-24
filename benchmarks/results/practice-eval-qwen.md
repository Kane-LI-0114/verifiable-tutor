# Practice evaluation: Qwen

Control result for the practice evaluation
([evaluation-runbook.md](../../docs/evaluation-runbook.md)), control assistant
Qwen.

- Date: 2026-11-23
- Material: `Tutorial_4.pdf` (FlashAttention, 40 pages) and the 10
  single-choice questions in
  [practice-eval-material.md](practice-eval-material.md).

## Dimension 1: generated questions (relevance)

Qwen invented 4 of 10 questions outside the PDF, the same pattern as Gemini.
Q6-Q9 tested FA-2, FA-3, MHA/MQA/GQA, and PagedAttention. None of these appear
in `Tutorial_4.pdf` (verified: FA-2, FA-3, FlashAttention-2, FlashAttention-3,
MHA, MQA, GQA, PagedAttention, and KV cache have zero occurrences in the
tracked page records).

| Metric | Qwen |
|---|---|
| Grounded rate | 6/10 = 60% |
| Off-topic rate | 4/10 = 40% |
| Knowledge-point coverage of the grounded questions | 3/5 (core idea, tiled GEMM, online softmax) |

## Dimension 2: grading accuracy

10/10. Qwen scored the correct answer 1 and the wrong answer 0 for every
question, normalizing the maximum score to 1 as the other controls did.

## Dimension 3: evaluation with citations

- Judgement: 10/10 correct.
- Citation accuracy: 9/10. Q2 cited page 39 for "Avoid writing the full", which
  is on page 40, the same one-page offset Doubao made.

## Comparison

| Dimension | Gemini | Qwen | Doubao | Treatment |
|---|---|---|---|---|
| Question groundedness | 6/10 | 6/10 | 10/10 | 10/10 |
| Off-topic questions | 4/10 | 4/10 | 0/10 | 0/10 |
| Knowledge-point coverage | 3/5 | 3/5 | 3/5 | 5/5 |
| Grading accuracy | 10/10 | 10/10 | 10/10 | 10/10 |
| Evaluation judgement | 10/10 | 10/10 | 10/10 | 10/10 |
| Citation accuracy | 10/10 | 9/10 | 8/10 | 10/10 |

## Findings

1. Gemini and Qwen both invented out-of-chapter questions (FA-2/FA-3,
   PagedAttention, and head-sharing schemes), ignoring the "only the PDF"
   constraint. Doubao did not. This is the clearest split among the controls:
   two general models expand into the FlashAttention paper's follow-on work
   that the course does not teach.
2. On grading and evaluation judgement all controls tie with the treatment.
3. The treatment's edge remains knowledge-point coverage (5/5) and
   programmatic `[ref_N]` citations.
