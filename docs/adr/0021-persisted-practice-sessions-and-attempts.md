# ADR-0021: Persisted practice sessions and attempts

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-25 |
| **Deciders** | Recorded by the engineering agent for the peter-dev branch |

## Context

The practice page kept the generated questions, the selected answers, and the grading results in React state. It saved one rendered Markdown summary only after the whole set was submitted, as a practice conversation with the `practice` kind. A reload before submission lost the questions and answers, a saved run could not be reopened as a quiz, and a redo had no history. The sidebar listed practice runs in the conversation list with only a different icon.

The product needs generated questions to survive a reload, a first attempt that fixes the status, unlimited redos, and a practical way to remove one attempt without discarding the session. The physical store also needs structured questions, because the saved Markdown cannot rebuild the per-question scoring view.

## Decision

**Two tables beside the conversation.** `practice_sessions` is one-to-one with a `practice` conversation and stores the topic, the structured `questions_json`, the sources, the status, the best score, the maximum score, and the completion time. `practice_attempts` stores one row per attempt with its answers, its stored results, its own option order, its score, and its timestamps. The conversation keeps `kind = 'practice'`, so the existing history and replay surfaces still work.

**Generation persists before the first answer.** `POST /api/practice/sessions` generates the questions through the agent loop and writes the conversation, the session, and attempt 1 in one transaction. An empty generation returns 502 and stores nothing. The client no longer holds the only copy.

**The first attempt owns the status.** A session is `not_started` until the first answer is saved, `in_progress` while that attempt is open, and `completed` when attempt 1 is submitted. Later attempts are `in_progress` or `completed` themselves but never change the session status. The best score is the maximum total across submitted attempts; it is not the first score.

**Answers autosave; submission grades.** `PATCH /api/practice/sessions/{id}/attempts/{n}/answers` writes the current answers and starts the session when needed. The browser grades choice questions deterministically and asks `POST /api/practice/runs` for open and code answers, then `POST /api/practice/sessions/{id}/attempts/{n}/submit` stores the answers and results and computes the total. Empty questions are stored as zero. Knowledge-point progress is written only from attempt 1.

**Choice order is per attempt.** The generator tends to put the correct choice first. Each attempt stores a shuffled choice order keyed by question id, seeded from the session and attempt number, and the UI renders that order. Answers are stored as choice text, so grading is unaffected. Question order is not shuffled.

**Delete one attempt.** `DELETE /api/practice/sessions/{id}/attempts/{n}` removes one attempt, renumbers the rest, and recomputes the status from the earliest remaining attempt and the best score from the remaining submitted attempts. The last attempt deletes the conversation. A session-level delete remains for a caller that wants to discard the whole run.

**Sidebar grouping.** Conversations and practice sessions are separate sidebar groups. A practice row shows the status and best score and opens `/practice/{id}`. A legacy practice conversation without a session row stays listed and opens in the chat view. A "not started" filter narrows the practice group.

**The schema moves to version 8 and then 9.** Version 8 adds the two tables. Version 9 adds `option_order_json` to an attempt.

## Consequences

**Positive:**

- A reload resumes the exact questions and answers, and an abandoned attempt is still visible in the sidebar.
- Redos are first-class history instead of overwriting the only saved result.
- The best score cannot be lowered by a worse redo, and deleting an attempt cannot silently rewrite the first attempt's status.
- The structured rows can rebuild the result page and support future analytics without parsing Markdown.

**Negative:**

- Two tables duplicate part of the conversation: the topic and title are stored in both places, by design.
- A redo page and the first page share a component, so the UI must keep the read-only and editable paths distinct.
- The sidebar now has two lists and a filter, which is more state than one flat list.

**Neutral:**

- Progress stays in `topic_progress` and is written only from attempt 1; redo scoring and long-term mastery are separate questions.
- Legacy practice conversations are not migrated; they open in the chat view.

## Alternatives considered

**One JSON column on `conversations`.** For: no new tables and one write. Against: autosave would rewrite the whole blob, unlimited attempts would grow one row, and status and best score could not be queried or constrained. Why not chosen: the two tables keep autosave to one attempt row and make the best score a SQL aggregate.

**One practice table with attempts as JSON.** For: one join fewer. Against: every autosave rewrites the growing attempts column. Why not chosen: the attempt rows are the natural write unit.

**Keep the questions in the browser and save on submit.** For: the smallest change. Against: a reload still loses the questions and answers, which is the defect being fixed. Why not chosen: persistence at generation is the requirement.

**Let a redo update the session status and score.** For: the badge always reflects the latest attempt. Against: it contradicts the stated rule that the first attempt decides the status and makes an abandoned redo look like progress. Why not chosen: the first attempt remains the canonical completion.
