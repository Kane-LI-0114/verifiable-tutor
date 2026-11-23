# Citation accuracy: Tutorial 4 Q6-Q10

Control versus treatment for the new-question citation experiment
([evaluation-plan.md](../../docs/evaluation-plan.md), Part 2.1).

- Date: 2026-11-23
- Control: DeepSeek web with `Tutorial_4.pdf` uploaded.
- Treatment: the verifiable tutor (pre-vectorized corpus).
- Questions: Q6-Q10, five single-document questions on FlashAttention.

## Result 1: the control truncated the PDF at page 12

`Tutorial_4.pdf` has 40 pages in the tracked corpus, but the control stated
"the provided text ends at Page 12". Everything after page 12 was therefore
invisible to it:

| Content | Actual pages | Seen by the control |
|---|---|---|
| tiled GEMM CUDA kernel | 13-20 | no |
| stable softmax | 22-31 | no |
| online softmax | 32-38 | no |
| FlashAttention core idea | 39-40 | no |

As a result the control answered every question with "the PDF does not explain
this", even though the material is present after page 12.

## Result 2: the treatment answered all five questions

| Question | Control | Treatment |
|---|---|---|
| Q6 core idea of FlashAttention | "no explicit explanation" | Tiled GEMM + Online Softmax; why the N×N matrix is never materialized; "exact attention, not approximation" |
| Q7 online softmax | "no explanation" | The running m and d recurrence, the rescale factor, and a stable-vs-online comparison |
| Q8 tiled GEMM and shared memory | "no explanation of FlashAttention's tiled GEMM" | `__shared__` tiles, `__syncthreads()`, and the 32-to-16 global-load reduction |
| Q9 role of sqrt(d_k) | "no explanation of the role of sqrt(d_k)" | Variance normalization, softmax saturation, gradient vanishing, numerical stability |
| Q10 why stable softmax subtracts max | "no explanation" | Overflow and underflow prevention, the shift-invariance of softmax, the e^{-m} cancellation |

## Conclusion

The control truncates a long PDF and therefore misses everything past the
first dozen pages, reporting present material as absent. The treatment
retrieves across all 40 pages and answers the questions. This matches the
Lecture 2 finding: the control's recall degrades with document length, while
the treatment's does not.
