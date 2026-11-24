# New-question citation: Doubao Q11-Q15

Control result for the new-question citation-accuracy experiment, assistant
Doubao, questions 11 to 15 (cross-document, MPI, and GEMM).

- Date: 2026-11-24
- Material: `Tutorial_4.pdf`, `ACS_lecture_2_2026F.pdf`, `Tutorial_1.pdf`.

## Positive citations

18 of 20 checked page-plus-quote pairs were found on the cited page. The two
misses are wording differences: Q11 page 7 "load once" is a diagram caption not
present in the OCR text, and Q15 page 18 "tile for A" is a paraphrase of the
tile-loading code. The MPI citations in Q14 are real (`One sender, one
receiver` on page 13, `collective communication is covered in Tutorial 2` on
page 1).

## Document-name error

Doubao repeatedly called the uploaded `Tutorial_4.pdf` "Tutorial 3" (for
example "CSIT6000V Tutorial 3"). The page numbers and quoted content are from
Tutorial 4, but the document identifier is wrong throughout Q11-Q13 and Q15.

## Negative claim

Q11 again states that the uploaded PDFs "do not define or mention bank
conflicts". Lecture 2 page 51 defines bank conflict ("Bank Conflicts Serialize
Otherwise Parallel Accesses"), so this is Doubao's third false "no bank
conflict" claim (also in Q4).

## Doubao new-question summary (Q1-Q15)

| Range | Positive accuracy | False "does not contain" | Other |
|---|---|---|---|
| Q1-Q5 | 16/17 | bank conflict, CXL | |
| Q6-Q10 | 18/20 (two wording diffs) | none | |
| Q11-Q15 | 18/20 (two wording diffs) | bank conflict (again) | calls Tutorial 4 "Tutorial 3" |

Doubao's page citations are largely accurate, but it misses late-page Lecture 2
content (bank conflict on page 51, CXL on pages 60-67) and mislabels the
Tutorial 4 document as Tutorial 3.
