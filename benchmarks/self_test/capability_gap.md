# Capability gap table (template)

Fill after the RQ2 run. Each capability is marked supported / partial / absent
for A and B, with the measured evidence. From benchmark-protocol.md section 6.

## Side-by-side table

| Capability | A status | A evidence | B status | B evidence |
|---|---|---|---|---|
| Verified reference answers | | | | |
| Grounding | | | | |
| Execution evidence | | | | |
| Grounded grading | | | | |
| Student usability | | | | |

## How to fill each row

- **Verified reference answers.** Share of generated questions whose reference
  answer passed verification (compiled and ran tests where applicable).
  Report the share for both systems.
- **Grounding.** Share of questions with a course source that passes the
  citation check. If B cites no course page, mark it absent, not zero quality.
- **Execution evidence.** Share of code questions whose reference or student
  answer actually ran on a test harness. A may use `tacc/exec`; B has no
  execution path, so mark absent.
- **Grounded grading.** Share of grading explanations with a course citation
  that passes the span verifier, plus the share of code grades backed by a
  recorded execution result. Mark B absent.
- **Student usability.** Share of a sampled set rated usable-as-is: no factual
  error, no ambiguity, no missing answer, no feedback a student cannot act on.

## Outcome

State the measured difference. A tie on any metric is reported as a tie; the
protocol does not assume the agent wins.
