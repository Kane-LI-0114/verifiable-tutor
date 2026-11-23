# New-question citation: Doubao Q6-Q10

Control result for the new-question citation-accuracy experiment, assistant
Doubao, questions 6 to 10 on FlashAttention.

- Date: 2026-11-24
- Material: `Tutorial_4.pdf` (FlashAttention).

## Positive citations

18 of 20 checked page-plus-quote pairs were found on the cited page. The two
misses are wording differences, not wrong pages:

| Item | Doubao claim | Reality |
|---|---|---|
| Q8 page 7 "load once ... reuse" | quoted text | Page 7 shows the Naive/Tiled GEMM contrast; "load once, reuse" is the diagram caption, not OCR text |
| Q10 page 24 "Translation Invariance of Softmax" | quoted heading | Page 24 proves the invariance as math (`softmax(X) = softmax(X-c)`), without that literal heading |

## Q9: sqrt(d_k)

Doubao stated that `Tutorial_4.pdf` presents the attention formula but does not
explain the role of sqrt(d_k), and it quoted only the formula. This is accurate:
the tracked pages contain no explanation of the scaling factor (no "scaling",
"saturation", or "why sqrt(d_k)" text). Doubao did not invent an explanation.

## Summary for Doubao Q1-Q10

| Range | Positive accuracy | False "does not contain" claims |
|---|---|---|
| Q1-Q5 (Lecture 2) | 16/17 | 2 (bank conflict, CXL) |
| Q6-Q10 (Tutorial 4) | 18/20 (two wording differences) | 0 |

Across Q1-Q10 Doubao's positive citations are largely accurate, and its only
false negative claims are bank conflict and CXL in Lecture 2.
