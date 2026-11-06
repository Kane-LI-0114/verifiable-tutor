# ADR-0019: Step-event association for the work chain

| | |
|---|---|
| **Status** | Accepted; refined to reference the step id rather than the step name |
| **Date** | 2026-11-06 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

[ADR-0017](0017-ordered-work-chain-events.md) made the work chain an ordered event log and kept `message_steps` as a separate coarse checklist. The UI first rendered the checklist as its own block and the events as another block. The lead found that split confusing: a step such as "retrieve" and the tool calls it caused appeared in two places with different orders.

The lead asked for steps to appear inside the work chain, with each step followed by its events, and for steps that currently have no events (`understand`, `decide`, `cite`) to remain visible. The design therefore needs two things:

1. a persisted association between a work-chain event and the step it belongs to, so history reload and replay can rebuild the sections;
2. a section renderer that shows every step that actually exists, even when it has no events, without inventing steps that never ran.

The agent loop is not a sequential phase pipeline. `generate` starts with the first model call and overlaps `retrieve`; the same step can be active before and after a tool call. The decision must work with that shape rather than assume one clean pass through the six phases.

## Decision

**Every `message_events` row carries an optional `step_id` referencing one `message_steps` row.** Schema version 5 adds the column. New rows are tagged at write time:

- a reasoning event references the `generate` step row of the same answer;
- a tool-call event references the step row selected by the tool declaration. The built-in retrieval tools (`search_course`, `read_course_page`, `web_search`, `web_fetch`) declare `retrieve`; future verification and policy tools declare `verify` and `decide`;
- an event with no step row stays NULL for legacy rows and unknown tools.

The step declaration lives on `ToolSpec` as a stage name. The runner copies that name into `tool_start` and `tool_end`; the chat service resolves it to the current `message_steps.id`, persists the id on the event, and includes it in the `data-tool` stream payload. The `data-step` frame also carries the id. The live UI and replay therefore use the same value as history.

**The UI renders one section per step row that actually exists.** The `message_steps` rows supply the id, status, duration, detail, policy, and rule id. Sections are ordered by the canonical phase order `understand`, `retrieve`, `verify`, `decide`, `generate`, `cite`; duplicate phase rows, if a future writer creates them, keep their persisted tie order. All events whose `step_id` matches the row render under it in event order. A step row with no events still renders its header and detail. A step that has no row is not synthesized, so a real turn that only emitted `generate` and `retrieve` shows only those two sections.

**`message_steps` remains the aggregate stage record.** It is not replaced by event ids. An event whose `step_id` does not match a returned step row is rendered flat rather than guessed into a section.

**The header keeps the summary, not a second step display.** The phase rail added in an earlier iteration is removed. The header shows the work-chain title, the `N/N steps complete` summary, the policy badge, and the expand control. Steps exist only inside the expanded chain.

**Legacy rows stay flat.** An event with `step_id = NULL` renders without a section header; a turn whose events all have NULL ids keeps the previous flat event list. The step headers still come from the surviving `message_steps` rows. Old replay traces infer the step from the existing `data-step` and `start-step` frames; if none are present, the events render flat.

**The final answer text is not an event and is not duplicated.** `generate` is an ordinary section; when thinking is off it has no reasoning events but still shows its header, and the answer remains the message body below the chain.

## Consequences

**Positive:**

- Each step and its events now live in one place, and the same association survives history reload and replay.
- Steps that currently have no events remain visible instead of disappearing, which keeps the work chain honest about phases such as `decide` when no tool ran for them.
- New tools declare their step once, in the type-safe tool registry, instead of the API layer hard-coding tool names.
- Legacy rows and old traces still render.

**Negative:**

- Schema version 5 adds a column and a migration; the physical data model page and image must be regenerated.
- Sections are grouped by phase, so events under a phase are shown together rather than in one uninterrupted chronological stream. The event order within a section is preserved, and the phase order is canonical.
- A repeated phase is one section, so the UI does not show a new header each time the agent re-enters that phase.
- The section order is a UI constant; a future custom phase order would need a persisted order or a new ADR.

**Neutral:**

- The step vocabulary and `message_steps` table do not change.
- The stream contract gains one optional field on `data-tool`; old clients ignore it.
- Event step id is nullable, so the migration does not rewrite existing rows.

## Alternatives considered

**Persist step start and finish as their own `message_events` rows.** For: one timeline that includes phase boundaries. Against: it duplicates `message_steps`, reintroduces overlapping sections for `generate`, and complicates the event CHECK. The association on each event is enough to group.

**Link by step name instead of id.** For: a smaller payload and no step id in the response. Against: two same-name step instances cannot be distinguished, which is the ambiguity this ADR removes; a nullable id keeps legacy rows and the API simple.

**Always render all six phases, with absent ones as pending.** For: a complete pipeline view. Against: it would display phases that never ran as if they were planned or waiting, which is misleading and was rejected by the lead.

**Group consecutive events into repeated sections.** For: preserves an interleaved timeline. Against: it produces repeated headers for the same phase, and the lead asked for each step followed by its events in the canonical phase order.

**Keep the header phase rail.** For: a compact summary. Against: it duplicates the step display once the steps are inside the chain.

## Follow-ups

- VT-05: when the span verifier lands, tag its events `verify` and add the tool declaration.
- Add `decide` events when the disclosure gate emits policy actions rather than only step state.
- If a future phase order becomes configurable, revisit the canonical order constant.
- Consider a `text` or answer marker event only if the final answer must become a section event; it is not needed for this decision.

## References

- Ordered work-chain events: [ADR-0017](0017-ordered-work-chain-events.md)
- Agent loop and typed tools: [ADR-0016](0016-minimal-agent-loop-and-typed-tools.md)
- Work-chain requirement: [../prd.md](../prd.md) FR-B9
- Vocabulary: [../../GLOSSARY.md](../../GLOSSARY.md)
- Provider behavior: [../model-providers.md](../model-providers.md)
- Physical schema: [../physical-data-model.md](../physical-data-model.md)
