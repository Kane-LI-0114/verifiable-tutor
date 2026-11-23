# New-question citation: cross-control summary

Summary of the new-question citation-accuracy experiment across three control
assistants (Doubao, Gemini, Qwen), the earlier DeepSeek run, and the verifiable
tutor (treatment).

- Date: 2026-11-24
- Questions: 15 (5 memory hierarchy, 5 FlashAttention, 3 cross-document, 1 MPI,
  1 GEMM), in [new-question-runbook.md](../../docs/new-question-runbook.md).
- Measurement: whether each assistant's page citations and quoted sentences are
  real and support its claims, checked against the tracked page records.

## Aggregate picture

| Dimension | Gemini | Doubao | Qwen | DeepSeek (Q1-Q5) | Treatment |
|---|---|---|---|---|---|
| Recall of bank conflict + CXL | full | missed both | full (one page early) | missed both | full |
| Invented quotes | 2 ("IO-aware tiling", "materializing S and P") | 0 | 1 ("materializing S and P") | 0 | 0 |
| False "does not contain" | 0 | 3 (bank conflict x2, CXL) | 0 | 4 | 0 |
| Page accuracy | best | good | systematic -1 on Lecture 2 | truncated at ~p20 | programmatic, exact |
| Document label | correct | Tutorial 4 called "Tutorial 3" | correct | correct | correct |

## Three failure modes, three assistants

1. **DeepSeek: truncation.** It read only about the first 20 pages of the
   69-page Lecture 2, so it reported late-page content (bank conflict, CXL) as
   absent.
2. **Doubao: recall gaps.** Its citations were accurate, but it missed bank
   conflict and CXL, and it mislabeled Tutorial 4 as Tutorial 3.
3. **Gemini and Qwen: invention plus offset.** Both had full recall, but both
   invented "materializing S and P" from the FlashAttention paper, Gemini added
   "IO-aware tiling", and Qwen's Lecture 2 page numbers are systematically one
   too low.

## What the treatment does differently

The treatment's `[ref_N]` citations come from the retrieval pipeline, not from
the model's memory, so they cannot drift by a page, cannot point at a document
that was not retrieved, and cannot quote a sentence the page does not contain.
Its only measured gap in this comparison is none of the three failure modes.

## Per-assistant reports

- [new-question-doubao-q1-q5.md](new-question-doubao-q1-q5.md),
  [new-question-doubao-q6-q10.md](new-question-doubao-q6-q10.md),
  [new-question-doubao-q11-q15.md](new-question-doubao-q11-q15.md)
- [new-question-gemini-q1-q5.md](new-question-gemini-q1-q5.md),
  [new-question-gemini-q6-q10.md](new-question-gemini-q6-q10.md),
  [new-question-gemini-q11-q13.md](new-question-gemini-q11-q13.md),
  [new-question-gemini-q14-q15.md](new-question-gemini-q14-q15.md)
- [new-question-qwen.md](new-question-qwen.md)
- [citation-accuracy-lecture2-q1-q5.md](citation-accuracy-lecture2-q1-q5.md)
  (the earlier DeepSeek run)
