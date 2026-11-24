# Evaluation report

Final report for the two cross-evaluations: the practice evaluation and the
new-question citation evaluation, each run against three control assistants
(Doubao, Gemini, Qwen) and the verifiable tutor.

- Date: 2026-11-24
- Materials: `Tutorial_4.pdf` (FlashAttention), `ACS_lecture_2_2026F.pdf`
  (memory hierarchy), `Tutorial_1.pdf` (MPI).
- Per-experiment summaries:
  [practice-eval-summary.md](../benchmarks/results/practice-eval-summary.md),
  [new-question-summary.md](../benchmarks/results/new-question-summary.md).

## Practice evaluation

Three dimensions: question relevance, grading accuracy, and evaluation citation
accuracy.

| Dimension | Doubao | Gemini | Qwen | Treatment |
|---|---|---|---|---|
| Question groundedness | 10/10 | 6/10 | 6/10 | 10/10 |
| Off-topic questions | 0/10 | 4/10 | 4/10 | 0/10 |
| Knowledge-point coverage | 3/5 | 3/5 | 3/5 | 5/5 |
| Grading accuracy | 10/10 | 10/10 | 10/10 | 10/10 |
| Evaluation judgement | 10/10 | 10/10 | 10/10 | 10/10 |
| Citation accuracy | 8/10 | 10/10 | 9/10 | 10/10 |

## New-question citation evaluation

One dimension: whether each assistant's page citations and quoted sentences are
real and support its claims.

| Dimension | Doubao | Gemini | Qwen | Treatment |
|---|---|---|---|---|
| Recall of bank conflict + CXL | missed both | full | full (one page early) | full |
| Invented quotes | 0 | 2 | 1 | 0 |
| False "does not contain" | 3 | 0 | 0 | 0 |
| Page accuracy | good | best | systematic -1 on Lecture 2 | programmatic, exact |
| Document label | Tutorial 4 called "Tutorial 3" | correct | correct | correct |

## Findings

1. On objective tasks (grading single-choice answers, judging a wrong answer),
   all four systems tie.
2. The controls have three distinct failure modes: Doubao misses late-page
   content, Gemini and Qwen invent quotes from the FlashAttention paper, and
   Qwen's Lecture 2 page numbers are systematically one too low.
3. The treatment's two durable advantages are knowledge-point coverage (5/5)
   and programmatic, page-exact citations. Its `[ref_N]` come from retrieval,
   so they cannot drift by a page, quote a sentence the page does not contain,
   or point at a document that was not retrieved.
4. The clearest control failure for the report is off-topic generation: Gemini
   and Qwen both invented FA-2/FA-3 and PagedAttention questions that the
   course does not cover.
