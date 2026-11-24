# New-question citation: Gemini Q6-Q10

Control result for the new-question citation-accuracy experiment, assistant
Gemini, questions 6 to 10 on FlashAttention.

- Date: 2026-11-24
- Material: `Tutorial_4.pdf` (FlashAttention).

## Positive citations

18 of 22 checked page-plus-quote pairs were found on the cited page. Four
misses fall into two kinds:

| Kind | Item | Note |
|---|---|---|
| Wording / diagram caption | Q8 page 7 "load once", Q10 page 24 "Translation Invariance" | content is present, the literal phrase is a diagram caption or math heading |
| Invented quote | Q6 page 40 "Exact full attention with IO-aware tiling", Q6 page 40 "Avoid materializing S and P in HBM" | neither appears in Tutorial 4; page 40 says "Avoid writing the full S=QK^T and P=softmax(S)" |

"IO-aware tiling" is FlashAttention-paper terminology, not course material. This
matches Gemini's practice-generation result, where it invented FA-2/FA-3 and
PagedAttention content the course does not cover.

## Q9: sqrt(d_k)

Like Doubao, Gemini correctly stated that Tutorial 4 presents the formula but
does not explain the role of sqrt(d_k), and it did not invent an explanation.

## Gemini new-question summary (Q1-Q10)

| Range | Positive accuracy | Notable |
|---|---|---|
| Q1-Q5 (Lecture 2) | 25/26 | retrieved bank conflict and CXL, no false "does not contain" |
| Q6-Q10 (Tutorial 4) | 18/22 | two invented quotes (IO-aware tiling, materializing S and P) |

Gemini has the best recall among the controls but also invents quotes from the
FlashAttention paper's terminology.
