# Evaluation results

Index of everything produced during the evaluation. The final report is
[docs/evaluation-report.md](../docs/evaluation-report.md).

## 1. Design (evaluation, new question, practice)

| File | Content |
|---|---|
| [../docs/evaluation-plan.md](../docs/evaluation-plan.md) | Overall design: the three practice dimensions, metrics, and the citation-accuracy experiment |
| [../docs/evaluation-runbook.md](../docs/evaluation-runbook.md) | Step-by-step procedure for the practice evaluation against each control assistant |
| [../docs/new-question-runbook.md](../docs/new-question-runbook.md) | Step-by-step procedure for the new-question citation evaluation, with the 15 questions |
| [../docs/product-differentiation.md](../docs/product-differentiation.md) | Capabilities a plain DeepSeek web session cannot reproduce |

## 2. Control assistants (Doubao, Gemini, Qwen) answers and results

Practice evaluation, per assistant:

| File | Content |
|---|---|
| [practice-eval-doubao.md](practice-eval-doubao.md) | Doubao practice result (three dimensions) |
| [practice-eval-gemini.md](practice-eval-gemini.md) | Gemini practice result |
| [practice-eval-qwen.md](practice-eval-qwen.md) | Qwen practice result |

New-question citation evaluation, per assistant and question range:

| File | Content |
|---|---|
| [new-question-doubao-q1-q5.md](new-question-doubao-q1-q5.md), [new-question-doubao-q6-q10.md](new-question-doubao-q6-q10.md), [new-question-doubao-q11-q15.md](new-question-doubao-q11-q15.md) | Doubao Q1-Q15 |
| [new-question-gemini-q1-q5.md](new-question-gemini-q1-q5.md), [new-question-gemini-q6-q10.md](new-question-gemini-q6-q10.md), [new-question-gemini-q11-q13.md](new-question-gemini-q11-q13.md), [new-question-gemini-q14-q15.md](new-question-gemini-q14-q15.md) | Gemini Q1-Q15 |
| [new-question-qwen.md](new-question-qwen.md) | Qwen Q1-Q15 |

## 3. The verifiable tutor's own results

| File | Content |
|---|---|
| [part2b_answers.jsonl](part2b_answers.jsonl) | The treatment's 15 new-question answers with `[ref_N]` sources |
| [part3a_questions.json](part3a_questions.json) | The treatment's 10 generated FlashAttention questions with `correct_answer` and `knowledge_points` |
| [part2_dim2_grading.jsonl](part2_dim2_grading.jsonl) | The treatment's 22 graded samples and the deterministic-scoring bug data |
| [grading-accuracy-dim2.md](grading-accuracy-dim2.md) | Grading-accuracy result and the deterministic-scoring fix |
| [citation-accuracy-lecture2-q1-q5.md](citation-accuracy-lecture2-q1-q5.md), [citation-accuracy-tutorial4-q6-q10.md](citation-accuracy-tutorial4-q6-q10.md) | Early new-question findings |

## 4. Conclusions

| File | Content |
|---|---|
| [practice-eval-summary.md](practice-eval-summary.md) | Practice cross-control summary (three dimensions, four systems) |
| [new-question-summary.md](new-question-summary.md) | New-question cross-control summary |

## 5. Final report

| File | Content |
|---|---|
| [../docs/evaluation-report.md](../docs/evaluation-report.md) | Final evaluation report combining both evaluations |

## Shared material

| File | Content |
|---|---|
| [practice-eval-material.md](practice-eval-material.md) | The 10 questions with correct and wrong student answers used by every assistant |
| [run_eval.py](run_eval.py) | Script that produced the treatment's raw data |
