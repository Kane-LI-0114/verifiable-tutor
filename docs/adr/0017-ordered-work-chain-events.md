# ADR-0017: Ordered work-chain events for reasoning and tool calls

| | |
|---|---|
| **Status** | Accepted; extended by [ADR-0019](0019-step-event-association.md) with the step tag on each event |
| **Date** | 2026-11-06 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

[ADR-0016](0016-minimal-agent-loop-and-typed-tools.md) added the first agent loop and persisted tool calls, but the work chain had no definition beyond a list of high-level steps. The UI rendered the work steps, the aggregated reasoning as one separate block, and the tool calls as a trailing list at the end of the answer bubble. That loses the order in which the model reasoned and acted: a reasoning segment that preceded a tool call was detached from it, and a second model call's reasoning was concatenated with the first.

The product requires the work chain to be a visible, replayable record of what the agent did for one answer (FR-B9). The lead clarified that the expanded work chain must contain the model reasoning and the tool calls in the order they happened, with each reasoning segment shown immediately before the tool calls it precedes, and that both must be persisted.

## Decision

**The work chain is an ordered, persisted event log for one assistant answer.** An event is one of:

- `reasoning`: the reasoning text produced by one model invocation. It is stored as a `reasoning` event before the events of the actions that invocation requested.
- `tool_call`: one tool invocation, stored as an event that references the matching `tool_calls` row.

The event order is the order the model produced them: reasoning for model call N, then the tool calls from call N, then reasoning for call N+1, and so on. The final answering call contributes one final reasoning event, and its text is the answer, not an event.

**A new `message_events` table stores the ordered events** (schema version 4). Columns: `id`, `message_id`, `position`, `kind`, `reasoning`, and `tool_call_position`; a check constrains each kind to its required fields, and the pair `(message_id, position)` is unique. A tool-call event references the `tool_calls` row by its position, so the detailed tool record stays in one place. `message_steps` remains the coarse step checklist (understand, retrieve, verify, decide, generate, cite); it is not the event log.

**`messages.reasoning` remains a compatibility aggregate.** It continues to hold the concatenated reasoning for older clients and for search; `message_events` is canonical for the work chain. New turns write both. Rows written before schema version 4 have no events; the UI builds a fallback chain from the aggregate reasoning and the tool calls so legacy answers still render.

**The runner reports each model call's reasoning with its `model_end` event.** The chat service uses those events to append one `reasoning` chain event per call with text, and one `tool_call` chain event per executed tool, before persisting the turn. A reasoning segment with no text is not stored.

**The UI renders the chain in order.** The expanded work chain shows the step checklist, then the ordered events: a reasoning block followed by its tool-call traces. The separate reasoning block outside the chain and the trailing tool-call list are removed. Live frames and stored history use the same event model; replay applies the same ordering to recorded frames.

## Consequences

**Positive:**

- The chain answers what the agent thought and did, in order, and the same order survives history reload and replay.
- Reasoning is attached to the action it explains, which makes multi-step tool use auditable.
- The event table is extensible: later evidence, verification, or policy events can join the same log without overloading `tool_calls` or `messages`.
- The API exposes events as first-class records, so the UI does not reconstruct order from unrelated fields.

**Negative:**

- Schema version 4 adds a table and a persistence path; the physical data model page and image must be regenerated.
- Reasoning is stored twice for new turns: the aggregate on the message and the ordered segments in events. This is a deliberate compatibility cost.
- Legacy turns have no events and rely on a fallback that cannot recover the original interleaving.
- A model that emits reasoning without text or a tool call contributes nothing to the chain, by design.

**Neutral:**

- Tool-call detail remains in `tool_calls`; events carry only the order and the reasoning.
- The AI SDK frame contract does not change; `data-tool` and `reasoning-*` frames remain the live transport, and the UI composes them into events.

## Alternatives considered

**Add a `reasoning` column to `tool_calls`.** For: one fewer table. Against: reasoning belongs to a model call, not to a tool, and a model call can issue several tool calls; it also cannot express a final reasoning segment with no tool call.

**Store the whole chain as one JSON document on the message.** For: a single write. Against: no ordered query, no per-event schema checks, and the API would return an opaque blob.

**Keep reasoning only in the aggregated `messages.reasoning` column and render tool calls after it.** For: no migration. Against: it cannot show which thinking preceded which action, which is the requirement.

**Use only the JSONL trace as the chain.** For: no schema change. Against: replay works, but history reload and the UI cannot show the chain without reading files outside the API contract, and the trace is not per-message queryable.

## Follow-ups

- VT-05: add `verify` and `cite` events to the same log when span verification and citations land.
- VT-02: add token usage to the event log or a sibling model-call record.
- Backfill old turns only if a demo needs them; the fallback covers legacy rows.
- Add a retention or pruning rule if event rows become large.

## References

- Agent loop and tool persistence: [ADR-0016](0016-minimal-agent-loop-and-typed-tools.md)
- Work chain requirement: [../prd.md](../prd.md) FR-B9
- Vocabulary: [../../GLOSSARY.md](../../GLOSSARY.md)
- Physical schema: [../physical-data-model.md](../physical-data-model.md)
