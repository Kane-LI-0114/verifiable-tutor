# New-question citation: Doubao Q1-Q5

Control result for the new-question citation-accuracy experiment
([new-question-runbook.md](../../docs/new-question-runbook.md)), control
assistant Doubao, questions 1 to 5 on Lecture 2.

- Date: 2026-11-24
- Material: `ACS_lecture_2_2026F.pdf` (memory hierarchy).

## Positive citations

Doubao's positive citations are almost all real: 16 of 17 checked page-plus-quote
pairs were found on the cited page. The one miss, Q4 page 45 "block scope", is a
paraphrase rather than a quote; the underlying content (shared memory is block
scoped with block lifetime, `__syncthreads()` coordinates a block) is on pages
45 and 46.

Doubao answered Q2 (SRAM vs DRAM) from page 32 ("6 transistors/bit" vs "one
transistor/bit plus capacitor"), content the earlier DeepSeek run claimed the
PDF did not contain.

## Negative claims

Doubao made two false "the PDF does not contain X" claims:

| Claim | Reality |
|---|---|
| No definition of bank conflict | Page 51 defines it ("Bank Conflicts Serialize Otherwise Parallel Accesses") |
| No mention of CXL | Pages 60, 66, 67 discuss CXL memory extension and CXL switches |

Both failures match the earlier DeepSeek run, which also missed bank conflict
and CXL.

## Comparison with the earlier DeepSeek run

| Metric | Doubao | DeepSeek (earlier) |
|---|---|---|
| Positive citation accuracy | 16/17 | 18/18 |
| False "does not contain" claims | 2 (bank conflict, CXL) | 4 (also locality, registers/shared memory) |

Doubao retrieved locality and the register/shared-memory roles that DeepSeek
missed, so it fails fewer negative claims, but both assistants miss the
late-page content (bank conflict on page 51, CXL on pages 60-67).
