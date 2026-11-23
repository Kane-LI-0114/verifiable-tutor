# New-question citation: Gemini Q11-Q13

Control result for the new-question citation-accuracy experiment, assistant
Gemini, questions 11 to 13 (cross-document).

- Date: 2026-11-24
- Material: `Tutorial_4.pdf` and `ACS_lecture_2_2026F.pdf`.

## Positive citations

22 of 23 checked page-plus-quote pairs were found on the cited page. The one
miss is a page error: Q12 cited page 52 for "Data reuse near the processor
reduces traffic across the memory hierarchy", which is on page 12.

## Bank conflict

Gemini answered Q11 with the full bank-conflict content from Lecture 2 page 51
(32 banks, `bank = (address / 4) mod 32`, multiple service rounds), which
DeepSeek and Doubao both missed. It also correctly noted that neither PDF
explicitly connects FlashAttention tiling to bank conflicts, so it did not
invent a link.

## Gemini new-question summary (Q1-Q13)

| Range | Positive accuracy | Notable |
|---|---|---|
| Q1-Q5 (Lecture 2) | 25/26 | retrieved bank conflict and CXL, no false "does not contain" |
| Q6-Q10 (Tutorial 4) | 18/22 | two invented quotes (IO-aware tiling, materializing S and P) |
| Q11-Q13 (cross-document) | 22/23 | one page error (p52 instead of p12) |

Gemini continues to have the best recall and page accuracy, with occasional
invented quotes and a single page slip.
