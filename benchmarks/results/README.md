# Evaluation results

This directory holds the evaluation artifacts for the two experiments designed
in [docs/evaluation-plan.md](../docs/evaluation-plan.md): citation accuracy
(Part 2) and chapter knowledge-point coverage (Part 3).

## Design documents

| File | Content |
|---|---|
| [../docs/product-differentiation.md](../docs/product-differentiation.md) | What a plain DeepSeek web session cannot do (Part 1) |
| [../docs/evaluation-plan.md](../docs/evaluation-plan.md) | The two experiments, metrics, and procedure (Parts 2 and 3) |

## Results so far

| File | Content |
|---|---|
| [citation-accuracy-lecture2-q1-q5.md](citation-accuracy-lecture2-q1-q5.md) | Q1-Q5: the control's positive citations are accurate (18/18) but its negative claims are all wrong (4/4) |
| [citation-accuracy-tutorial4-q6-q10.md](citation-accuracy-tutorial4-q6-q10.md) | Q6-Q10: the control truncated the 40-page PDF at page 12 and missed everything after |

## Raw experiment data

| File | Content |
|---|---|
| [part2b_answers.jsonl](part2b_answers.jsonl) | The treatment's 15 answers with `[ref_N]` sources (Part 2, experiment group) |
| [part3a_questions.json](part3a_questions.json) | The treatment's 11 generated FlashAttention questions with knowledge points (Part 3, experiment group) |
| [run_eval.py](run_eval.py) | The script that produced the two files above |

## Key findings

1. **Precision vs recall.** The control cites accurately what it cites, but it
   misses material that is present and reports it as absent (Lecture 2: CXL,
   bank conflict, locality, registers/shared memory).
2. **Length-dependent recall.** The control truncates a long PDF (Tutorial 4
   stopped at page 12 of 40), so its recall degrades with document length,
   while the treatment retrieves across all pages.

## Status

The control (DeepSeek web) is paused: the web version currently reads only the
first ~20 pages of an uploaded PDF, which prevents a fair long-document
comparison. The experiment will resume with another model or a version of
DeepSeek that reads full documents.
