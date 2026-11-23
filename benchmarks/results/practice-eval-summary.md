# Practice evaluation: control summary

Summary of the practice evaluation across three control assistants (Doubao,
Gemini, Qwen) and the verifiable tutor (the treatment). The per-assistant
reports are in the files listed below.

- Date: 2026-11-23
- Material: `Tutorial_4.pdf` (FlashAttention, 40 pages) and the 10
  single-choice questions in
  [practice-eval-material.md](practice-eval-material.md).
- Dimensions: question relevance (1), grading accuracy (2), and evaluation
  citation accuracy (3), as designed in
  [evaluation-runbook.md](../../docs/evaluation-runbook.md).

## Aggregate results

| Dimension | Doubao | Gemini | Qwen | Treatment |
|---|---|---|---|---|
| 1. Question groundedness | 10/10 | 6/10 | 6/10 | 10/10 |
| 1. Off-topic questions | 0/10 | 4/10 | 4/10 | 0/10 |
| 1. Knowledge-point coverage | 3/5 | 3/5 | 3/5 | 5/5 |
| 2. Grading accuracy | 10/10 | 10/10 | 10/10 | 10/10 |
| 3. Evaluation judgement | 10/10 | 10/10 | 10/10 | 10/10 |
| 3. Citation accuracy | 8/10 | 10/10 | 9/10 | 10/10 |

## Dimension 1: question relevance

- Doubao and the treatment stayed inside the PDF (0 off-topic).
- Gemini and Qwen both invented 4 out-of-chapter questions. They expanded into
  the FlashAttention paper's follow-on work (FA-2, FA-3, PagedAttention, and
  MHA/MQA/GQA), none of which `Tutorial_4.pdf` contains. This is the clearest
  failure among the controls.
- The treatment is the only system that covered all 5 knowledge points; every
  control covered 3 of 5, missing stable softmax and the attention operator.

## Dimension 2: grading accuracy

All four systems graded the 10 questions exactly, so grading accuracy is not a
differentiator on single-choice questions. The three controls normalized the
maximum score to 1 point, while the treatment used each question's real 2 or 3
points.

## Dimension 3: evaluation citation accuracy

- All four systems judged the student answers correctly.
- Citation accuracy differs: Gemini 10/10, Qwen 9/10, Doubao 8/10. Qwen and
  Doubao made the same one-page error (citing page 39 for content on page 40).
- The treatment's `[ref_N]` citations are programmatic and verifiable, so it
  cannot drift by a page.

## Conclusion

1. On objective grading and evaluation judgement, the treatment and the three
   controls tie.
2. The treatment's two durable advantages are knowledge-point coverage (5/5)
   and programmatic, page-exact citations.
3. The controls' clearest failures are off-topic generation (Gemini and Qwen)
   and one-page citation drift (Qwen and Doubao).

## Per-assistant reports

- [practice-eval-doubao.md](practice-eval-doubao.md)
- [practice-eval-gemini.md](practice-eval-gemini.md)
- [practice-eval-qwen.md](practice-eval-qwen.md)
- [grading-accuracy-dim2.md](grading-accuracy-dim2.md) (treatment grading and the
  deterministic-scoring fix)
