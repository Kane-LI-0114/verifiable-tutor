# New-question citation: Gemini Q14-Q15

Control result for the new-question citation-accuracy experiment, assistant
Gemini, questions 14 to 15 (MPI and GEMM).

- Date: 2026-11-24
- Material: `Tutorial_1.pdf` (Q14), `Tutorial_4.pdf` (Q15).

## Positive citations

Q15 is fully accurate (7 of 7). Q14 has two page offsets:

| Claim | Gemini page | Actual page |
|---|---|---|
| "One sender, one receiver, one matching message" | 14 | 13 |
| "Next tutorial: how multiple local values become a global result using MPI collectives" | 16 | 15 |

## Gemini new-question summary (Q1-Q15)

| Range | Positive accuracy | Notable |
|---|---|---|
| Q1-Q5 (Lecture 2) | 25/26 | retrieved bank conflict and CXL, no false "does not contain" |
| Q6-Q10 (Tutorial 4) | 18/22 | two invented quotes (IO-aware tiling, materializing S and P) |
| Q11-Q13 (cross-document) | 22/23 | one page error (p52 instead of p12) |
| Q14-Q15 (MPI, GEMM) | 9/11 | two page offsets (p14 instead of p13, p16 instead of p15) |

Across all 15 questions Gemini has the best recall (it retrieved bank conflict
and CXL) and the most accurate page citations, with a small number of invented
quotes and one-page offsets.
