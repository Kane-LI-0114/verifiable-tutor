# New-question citation: Qwen Q1-Q15

Control result for the new-question citation-accuracy experiment, assistant
Qwen, all 15 questions.

- Date: 2026-11-24
- Material: `ACS_lecture_2_2026F.pdf`, `Tutorial_4.pdf`, `Tutorial_1.pdf`.

## Systematic one-page offset on Lecture 2

Qwen's page numbers for Lecture 2 are almost all one lower than the real page.
Checked examples:

| Claim | Qwen page | Real page |
|---|---|---|
| "In modern computing systems..." | 10 | 11 |
| "The arithmetic intensity shifts..." | 7 | 8 |
| "DRAM DIMM capacity..." | 8 | 9 |
| "Requires 6 transistors/bit" | 31 | 32 |
| "A piece of data is quickly reused..." | 21 | 22 |
| "Allocated per thread, hardware managed" | 42 | 43 |
| "Bank Conflicts Serialize..." | 50 | 51 |
| "Capacity Wall: HBM..." | 64 | 65 |
| "Unified memory across host DRAM/HBM and CXL" | 65 | 66 |
| "Better locality: blocking / tiling" | 28 | 29 |

The Tutorial 4 page numbers are mostly correct. Qwen retrieved bank conflict and
CXL (so its recall is full), but it labels them one page early.

## Invented quote

Like Gemini, Qwen quoted "Avoid materializing S and P in HBM" as a page-40
FlashAttention-family summary. Neither "materializing S and P" nor "Avoid
materializing" appears in Tutorial 4; page 40 says "Avoid writing the full
S=QK^T and P=softmax(S)".

## Q14 (MPI)

Qwen correctly stated that Tutorial 1 does not define collective communication
(only point-to-point, with collectives deferred to Tutorial 2), and it did not
invent a comparison.

## Comparison across the three controls

| Metric | Gemini | Doubao | Qwen |
|---|---|---|---|
| Recall of bank conflict + CXL | full | missed both | full (one page early) |
| Invented quotes | "IO-aware tiling", "materializing S and P" | none | "materializing S and P" |
| Page accuracy | best | good | systematic -1 offset on Lecture 2 |

Qwen has full recall like Gemini, shares Gemini's "materializing S and P"
invention, and has the weakest page accuracy because of the systematic one-page
offset on Lecture 2.
