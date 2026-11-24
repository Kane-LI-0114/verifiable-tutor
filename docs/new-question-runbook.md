# New-question evaluation runbook: citation accuracy

Step-by-step instructions for running the new-question citation-accuracy
experiment against three control assistants: Doubao, Gemini, and Qwen. Repeat
the same procedure for each assistant.

The experiment measures citation accuracy: whether the assistant's page
citations and quoted sentences are real and support its claims. The design is
[evaluation-plan.md](evaluation-plan.md#part-2-citation-accuracy).

## Materials

| Material | Path |
|---|---|
| memory hierarchy PDF | `data/corpus/corpus-pdf/ACS_lecture_2_2026F.pdf` |
| FlashAttention PDF | `data/corpus/corpus-pdf/Tutorial_4.pdf` |
| MPI PDF | `data/corpus/corpus-pdf/Tutorial_1.pdf` |

## Questions and which PDF to upload

| Questions | Upload |
|---|---|
| Q1-Q5 (memory hierarchy) | `ACS_lecture_2_2026F.pdf` |
| Q6-Q10 (FlashAttention) | `Tutorial_4.pdf` |
| Q11-Q13 (cross-document) | `Tutorial_4.pdf` and `ACS_lecture_2_2026F.pdf` together |
| Q14 (MPI) | `Tutorial_1.pdf` |
| Q15 (GEMM) | `Tutorial_4.pdf` |

### The 15 questions

1. According to Lecture 2, what does the "memory wall" specifically refer to? What is its impact on system performance?
2. According to Lecture 2, what are the differences between DRAM and SRAM in terms of speed, density, and cost?
3. What are temporal locality and spatial locality? Give one example of each.
4. In the GPU memory hierarchy, what are the roles of registers and shared memory respectively? What is a bank conflict?
5. According to Lecture 2, what problems do HBM/GDDR and CXL each solve?
6. What is the core idea of FlashAttention? Why does it avoid materializing the attention matrix?
7. What is online softmax? How does it differ from regular softmax?
8. How does FlashAttention's tiled GEMM use shared memory?
9. In the attention operator QK^T / sqrt(d_k), what is the role of sqrt(d_k)?
10. Why does stable softmax subtract the maximum value?
11. How does FlashAttention's shared-memory tiling relate to the GPU shared memory and bank conflicts described in Lecture 2?
12. Why does FlashAttention avoid materializing the N×N attention matrix? How does this relate to the "memory wall" in Lecture 2?
13. What memory-access pattern does FlashAttention's online softmax require, and how does it relate to the concept of locality in Lecture 2?
14. What is the difference between point-to-point and collective communication in MPI?
15. How does shared-memory tiling in GEMM reduce global memory accesses?

## Uniform prompt

Send this prompt together with each question:

> Please answer the following question using ONLY the uploaded PDF(s). Do not
> use your general knowledge or web search. For every factual claim in your
> answer, state the specific page number and quote the exact sentence that
> supports it.

## Procedure (repeat for each assistant)

1. For Q1-Q5: start a chat, upload `ACS_lecture_2_2026F.pdf`, send the prompt
   above plus one question at a time, and copy each answer verbatim.
2. For Q6-Q10: start a chat, upload `Tutorial_4.pdf`, and repeat.
3. For Q11-Q13 (cross-document): start a chat, upload BOTH PDFs, and repeat.
4. For Q14: start a chat, upload `Tutorial_1.pdf`, and repeat.
5. For Q15: start a chat, upload `Tutorial_4.pdf`, and repeat.

Ask one question at a time and wait for the answer before the next. Turn off
web search when the assistant has such a toggle.

## How to report results

For each assistant, send the answers in this shape:

```
[assistant name]
Q1:
<paste verbatim>
Q2:
<paste verbatim>
...
Q15:
<paste verbatim>
```

Paste everything verbatim, including every page number and quote the assistant
claims, so it can be checked against the tracked page records.
