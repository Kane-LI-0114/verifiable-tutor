# Practice evaluation: Doubao

Control result for the practice evaluation
([evaluation-runbook.md](../../docs/evaluation-runbook.md)), control assistant
Doubao.

- Date: 2026-11-23
- Material: `Tutorial_4.pdf` (FlashAttention, 40 pages) and the 10
  single-choice questions in
  [practice-eval-material.md](practice-eval-material.md).
- Treatment reference: the verifiable tutor, whose 10 questions carry a
  `correct_answer` and per-question `knowledge_points`.

## Dimension 1: generated questions (relevance)

- Grounded rate: 10/10. All ten questions are answerable from Tutorial 4, no
  invented content.
- Knowledge-point coverage: 3/5.

| Knowledge point | Doubao questions |
|---|---|
| FlashAttention core idea | 8 |
| tiled GEMM | 2 |
| online softmax | 1 |
| stable softmax | 0 |
| attention operator (QK^T / sqrt(d_k)) | 0 |

Doubao concentrated 8 of 10 questions on the core idea and missed two points
that the treatment's knowledge-point list forces it to cover.

## Dimension 2: grading accuracy

- Doubao graded all 10 questions correctly: the correct answer earned full
  marks and the wrong answer earned 0.
- Judgement accuracy: 10/10 = 100%.
- Scale note: Doubao reported a maximum score of 1 for every question, while
  the questions carry 2 or 3 points. The judgement is right, but Doubao did not
  use the question's actual point scale.

## Dimension 3: evaluation with citations

- Judgement: 10/10 correct (every wrong student answer was identified).
- Citation page accuracy: 8/10. Q1 and Q2 cited page 39 for content that is on
  page 40, a one-page offset. Q9 and Q10 cited a summarizing phrase rather than
  the exact source sentence.

## Comparison

| Dimension | Doubao | Treatment |
|---|---|---|
| Question groundedness | 10/10 | 10/10 |
| Knowledge-point coverage | 3/5 = 60% | 5/5 = 100% |
| Grading accuracy | 10/10 | 10/10 |
| Evaluation judgement | 10/10 | 10/10 |
| Citation page accuracy | 8/10 | 10/10 (programmatic `[ref_N]`) |

## Findings

1. Doubao and the treatment tie on grading accuracy and evaluation judgement.
2. Doubao lags on knowledge-point coverage because it has no knowledge-point
   list, so its questions cluster on one point.
3. Doubao's citations have a one-page offset on two questions, a smaller
   defect than DeepSeek's recall failure but still a citation-accuracy gap.
