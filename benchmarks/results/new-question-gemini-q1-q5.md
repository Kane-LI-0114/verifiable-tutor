# New-question citation: Gemini Q1-Q5

Control result for the new-question citation-accuracy experiment, assistant
Gemini, questions 1 to 5 on Lecture 2.

- Date: 2026-11-24
- Material: `ACS_lecture_2_2026F.pdf` (memory hierarchy).

## Positive citations

25 of 26 checked page-plus-quote pairs were found on the cited page. The one
miss, Q4 page 45 "thread lifetime", is a diagram label not present in the OCR
text; the scope/lifetime facts are in the page 46 table.

## Negative claims

None. Gemini is the only control that answered Q4 (bank conflict) and Q5 (CXL)
from the late pages instead of claiming the PDF does not cover them:

| Content | Page | Gemini |
|---|---|---|
| bank conflict | 51 | cited it |
| CXL | 66-67 | cited it |

## Comparison with DeepSeek and Doubao on Q1-Q5

| Metric | Gemini | Doubao | DeepSeek |
|---|---|---|---|
| Positive citation accuracy | 25/26 | 16/17 | 18/18 |
| False "does not contain" claims | 0 | 2 (bank conflict, CXL) | 4 (also locality, registers/shared memory) |

Gemini retrieved the full span of Lecture 2, including the late-page bank
conflict and CXL content that DeepSeek and Doubao missed.
