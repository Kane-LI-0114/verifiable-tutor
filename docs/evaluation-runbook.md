# Practice evaluation runbook: four control AIs

Step-by-step instructions for running the practice evaluation against four
control assistants: DeepSeek, Doubao, Qwen, and Gemini. Repeat the same
procedure for each assistant using the same materials so the results are
comparable.

The three measured dimensions and their definitions are in
[evaluation-plan.md](evaluation-plan.md#part-2-citation-accuracy) and the
practice evaluation section. This file owns the operational steps.

## Materials

| Material | Where |
|---|---|
| Course PDF | `data/corpus/corpus-pdf/Tutorial_4.pdf` (FlashAttention chapter, 40 pages) |
| 10 single-choice questions with the correct answer and one wrong answer per question | [../benchmarks/results/practice-eval-material.md](../benchmarks/results/practice-eval-material.md) |

The 10 questions are the treatment's generated set. The "wrong answer" listed
for each question is the student answer to feed the assistant in steps 2 and 3.

## Procedure (repeat for each assistant)

Use the same PDF, the same questions, the same student answers, and the same
prompts for every assistant.

### Step 1: generate questions (relevance)

1. Start a new chat and upload `Tutorial_4.pdf`.
2. Send:
   > Generate 10 single-choice questions about FlashAttention based only on the
   > uploaded PDF. Each question must have a question stem, four options, and
   > the correct answer. Do not use your general knowledge or web search.
3. Wait for it to finish.
4. Copy the 10 questions and answers verbatim and save them.

### Step 2: grade answers (grading accuracy)

1. Start a new chat and upload `Tutorial_4.pdf` (a fresh chat avoids context
   carry-over, and the PDF lets it grade from the material instead of memory).
2. Send:
   > Below are 10 single-choice questions. Each question has two student
   > answers, answer 1 and answer 2. For each question, determine the correct
   > choice using ONLY the uploaded PDF, then grade each answer: a correct
   > choice earns full marks and a wrong choice earns 0. Do not use your
   > general knowledge or web search. Output, for each question, the question
   > number, answer 1 score, answer 2 score, and the maximum score.
3. Paste the 10 questions, and for each question paste two student answers:
   answer 1 = the correct answer, answer 2 = the listed wrong answer. Do not
   tell the assistant which answer is correct.
4. Wait for it to finish.
5. Copy the scores verbatim and save them.

### Step 3: evaluate with citations (citation accuracy)

1. Start a new chat and upload `Tutorial_4.pdf` again.
2. Send:
   > A student answered the question below. Judge whether the student's answer
   > is correct, and cite the specific page number or exact sentence of the
   > uploaded PDF that supports your judgement.
3. Paste the question and the student's wrong answer.
4. Wait for it to finish.
5. Copy the evaluation and every page number or quote it claims, verbatim, and
   save them.

## How to report results

For each assistant, send the three outputs in this shape:

```
[assistant name]
### Step 1: generated questions
<paste verbatim>
### Step 2: grading
<paste verbatim>
### Step 3: evaluation with citations
<paste verbatim>
```

## Notes

- Paste everything verbatim. Do not reword or summarize, because the page
  numbers and quotes are checked against the tracked page records.
- Turn off web search when the assistant has such a toggle.
- Record how many pages of the 40-page PDF each assistant actually read. For
  example DeepSeek web currently reads only about the first 20 pages.
- If an assistant refuses to upload, cannot generate 10 questions, or refuses
  to grade, record that as the result instead of working around it.
