# Citation accuracy: Lecture 2 Q1-Q5

Control versus treatment for the new-question citation experiment
([evaluation-plan.md](../../docs/evaluation-plan.md), Part 2.1).

- Date: 2026-11-23
- Control: DeepSeek web with `ACS_lecture_2_2026F.pdf` uploaded.
- Treatment: the verifiable tutor (pre-vectorized corpus).
- Questions: Q1-Q5, five single-document questions on Lecture 2.

## Result 1: the control's positive citations are accurate (18/18)

Every positive citation the control gave (a page number plus a quoted claim)
was verified against the tracked page records and found on the cited page.

| Question | Page | Quoted claim (key span) | Verdict |
|---|---|---|---|
| Q1 | 3 | Bottleneck: Memory Wall | hit |
| Q1 | 3 | ...orders of magnitude faster than memory access | hit |
| Q1 | 7 | Performance Gap grows 50% per Year | hit |
| Q1 | 7 | Faster processors alone do not guarantee faster applications | hit |
| Q1 | 11 | ...memory performance typically the bottleneck of entire systems | hit |
| Q2 | 5 | On-chip SRAM, such as block RAM... | hit |
| Q2 | 6 | ...discrete GPU uses its own device DRAM: GDDR chips or HBM stacks | hit |
| Q2 | 13 | AMD Barcelona | hit |
| Q2 | 19 | Apple M1 Ultra System | hit |
| Q3 | 12 | Registers and caches reduce how often execution... | hit |
| Q3 | 12 | Data reuse near the processor reduces traffic... | hit |
| Q3 | 20 | Locality and cache performance | hit |
| Q4 | 17 | L1: 128KB per SM | hit |
| Q4 | 17 | L2: 6MB shared | hit |
| Q4 | 17 | Many SMs share the device-wide L2 cache... | hit |
| Q5 | 6 | Results can stay in device memory... | hit |
| Q5 | 8 | Tensor Core throughput has been growing much faster than the capacity of HBM | hit |
| Q5 | 8 | Widening the Memory Wall across Generations | hit |

## Result 2: the control's negative claims are all wrong (4/4)

Where the control claimed the PDF "does not" contain something, it was wrong in
every case. The material exists but the control did not retrieve it.

| Control claim | Where the material actually is |
|---|---|
| The PDF does not mention CXL anywhere | p60 ("CXL, LPDDR, and memory placement"), p66 ("Memory Extension: CXL"), p67 ("CXL Switches Enable Expansion, Pooling, and Sharing") |
| No page provides a definition of bank conflict | p51 ("Bank Conflicts Serialize Otherwise Parallel Accesses") |
| The PDF does not define temporal or spatial locality | p22-p24 ("Temporal Locality: a piece of data is quickly reused in the future..."; "Spatial Locality: the neighbors of the current data access..."; the `A[100], B[100], C[100], D` loop) |
| The PDF does not explain the roles of registers and shared memory | p43 ("Registers: allocated per thread, hardware managed"; "Shared Memory + L1 Cache: per SM, explicit scratchpad"), p50 ("Shared memory is an explicitly addressed scratchpad...") |

## Result 3: the treatment answered what the control missed

| Question | Control | Treatment |
|---|---|---|
| Q3 locality | "does not define" locality | Defined temporal and spatial locality, gave the Loops and array examples, cited the pages |
| Q4 registers / shared memory / bank conflict | "does not explain" them | Explained registers ("per thread, hardware managed"), shared memory ("per SM explicit scratchpad"), and bank conflict |
| Q5 HBM/GDDR/CXL | "does not mention CXL" | Contrasted DDR/GDDR/HBM and covered CXL memory extension |

## Conclusion

The control's citations are precise but low-recall: what it does cite is
correct, yet it misses material that is present and falsely reports it as
absent. The treatment retrieves the missing material and answers it. This is
the primary citation-accuracy differentiator, and a concrete failure case for
the evaluation.
