# Practice evaluation: Gemini

Control result for the practice evaluation
([evaluation-runbook.md](../../docs/evaluation-runbook.md)), control assistant
Gemini.

- Date: 2026-11-23
- Material: `Tutorial_4.pdf` (FlashAttention, 40 pages) and the 10
  single-choice questions in
  [practice-eval-material.md](practice-eval-material.md).

## Dimension 1: generated questions (relevance)

Gemini invented 4 of 10 questions outside the PDF. Q7-Q10 tested the
FlashAttention family (FA-2, FA-3, FA-4), PagedAttention, and Blackwell/Hopper
hardware. None of these appear in `Tutorial_4.pdf` (verified: the strings FA-2,
FA-3, FA-4, PagedAttention, Blackwell, Hopper, H100, B200, and KV cache have
zero occurrences in the tracked page records).

| Metric | Gemini |
|---|---|
| Grounded rate | 6/10 = 60% |
| Off-topic rate | 4/10 = 40% |
| Knowledge-point coverage of the grounded questions | 3/5 (core idea, tiled GEMM, online softmax) |

## Dimension 2: grading accuracy

10/10. Gemini scored the correct answer 1 and the wrong answer 0 for every
question. Like Doubao, it normalized the maximum score to 1 instead of using
the question's 2 or 3 points.

## Dimension 3: evaluation with citations

- Judgement: 10/10 correct.
- Citation page and quote accuracy: 10/10. Every cited page and quoted sentence
  was found on the cited page, including the Q5 dual citation (pages 14 and 19)
  and Q6 page 17.

## Comparison

| Dimension | Gemini | Doubao | Treatment |
|---|---|---|---|
| Question groundedness | 6/10 | 10/10 | 10/10 |
| Off-topic questions | 4/10 | 0/10 | 0/10 |
| Knowledge-point coverage | 3/5 | 3/5 | 5/5 |
| Grading accuracy | 10/10 | 10/10 | 10/10 |
| Evaluation judgement | 10/10 | 10/10 | 10/10 |
| Citation accuracy | 10/10 | 8/10 | 10/10 |

## Findings

1. Gemini has the strongest citation accuracy of the two controls so far (10/10,
   better than Doubao's 8/10).
2. Gemini is the only control that invented out-of-chapter questions: it ignored
   the "only the PDF" constraint and produced 4 questions on the FlashAttention
   family and PagedAttention, none of which the course covers. This is the
   clearest off-topic failure among the controls and a concrete failure case
   for the evaluation.
3. All three systems tie on grading accuracy and evaluation judgement; the
   treatment's edge is knowledge-point coverage and programmatic citations.
