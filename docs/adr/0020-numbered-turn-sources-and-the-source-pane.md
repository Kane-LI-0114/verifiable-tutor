# ADR-0020: Numbered turn sources and the citation source pane

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-11 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The chat thread shows citations as page-level records. The right pane was an evidence viewer: it took one citation at a time, rendered the page image from `/api/corpus/<doc_id>/pages/<page_no>.webp`, and drew a highlight box. It could not show several sources from one answer as a list, it had no place for web sources, and its entry points were spread across a citation chip row, an inline Sources disclosure, and a collapsed 44px rail. The model was also told to cite as `[doc_id p.N]`, which does not map cleanly onto the hybrid retriever's top-k results.

The PRD requires page-level citations with quoted spans (FR-B3), deterministic span verification with one repair round or abstention (FR-B4), and an evidence surface (FR-B5). The verified citation path is still deferred and tracked by [issue #1](https://github.com/Kane-LI-0114/verifiable-tutor/issues/1). This ADR settles the layer below it: how retrieved sources are numbered, streamed, persisted, listed, and opened. It does not claim that a source supports the sentence that cites it.

## Decision

**One turn-scoped source registry.** Each chat turn creates one `SourceRegistry`. It assigns markers from 1 upward in first-seen order across every retrieval and web tool call in the turn. A course source is identified by `(doc_id, page_no)`; multiple chunks from one page share one marker and one row. A web source is identified by its URL with the fragment removed. A second retrieval never renumbers an existing source, and a later `web_fetch` of a URL already returned by `web_search` keeps the marker and may replace the summary with the fetched content.

**The model cites the registry marker.** `search_course`, `read_course_page`, `web_search`, and `web_fetch` attach `marker` and `citation: "[n]"` to the data the model reads. The system prompt requires `[n]` markers, placed at the end of each paragraph in ascending numeric order, and forbids inventing a marker. The frontend matches the same `[n]` form. It renders a marker as a source link and never renumbers or moves it.

**Sources are streamed and persisted separately from verified citations.** After a tool run changes the registry, the runner emits a `sources` event and the chat service writes a `data-sources` custom data part carrying the full current snapshot. The turn end carries the same snapshot, and `Storage.add_assistant_turn` writes it to the new `message_sources` table in the same transaction as the answer. The history endpoint returns `sources`. The existing `citations` table keeps its meaning: a reference with a verified quoted span. This iteration leaves it empty, so the UI never presents an unverified source as a verified citation.

**The source capsule is the only entry.** Each assistant answer with at least one source shows a capsule at the end of its content, above the answer actions. The capsule stacks up to three source thumbnails, shows a `+N` remainder, and summarizes the counts as course pages and web pages. Clicking it opens the source pane for that answer; clicking it again, or the pane's close button, closes the pane. The pane starts closed on every page load and does not persist an open flag. The old citation chip row, the inline Sources disclosure, the collapsed rail, and the automatic pane expansion on a citation click are removed.

**Navigation follows the source kind.** A course row and a course marker navigate in the app to `/knowledge/docs/<doc_id>?page=<page_no>`, which is the knowledge browser's paginated file view. A web row and a web marker open the source URL in a new tab with `noopener noreferrer`. Hovering a marker shows the same row content the pane shows, using one shared `SourceItem` composition.

**No verification in this iteration.** `[n]` means the source was retrieved for the turn. It does not mean the source supports the surrounding claim. Span verification, claim support, repair, abstention, and writing verified rows to `citations` remain [issue #1](https://github.com/Kane-LI-0114/verifiable-tutor/issues/1), [VT-05](../todo.md), FR-B3, and FR-B4.

## Consequences

**Positive:**

- The marker is stable across repeated retrieval calls, so the model and the UI share one numbering without a second mapping.
- The source list can mix course pages and web pages, which the page-image viewer could not represent.
- Sources survive a reload, a conversation switch, and replay because they are persisted beside the answer and re-emitted in the trace.
- The verified citation table keeps its narrow meaning, so the later verifier does not have to migrate or reinterpret unverified rows.
- The answer has one source entry point instead of three, and the default view is quieter.

**Negative:**

- `message_sources` duplicates part of what a future verified citation will carry: doc id, page, and a text excerpt. The later verifier will write `citations` and may not need all source columns, but the duplication is deliberate until verification exists.
- The history response grows by one row per retrieved source, including sources the answer never cites. At the course-demo scale this is acceptable; the tool budget bounds the list.
- A model that ignores the paragraph-end instruction can place markers mid-paragraph. The frontend preserves the model's placement instead of rewriting the answer, so the prompt contract is the only enforcement in this iteration.
- The web thumbnail is a best-effort favicon; the layout must remain readable when the image fails.

**Neutral:**

- The schema version moves to 7. Existing answers keep no sources and therefore show no capsule.
- The `citations` API field stays in place and stays empty until verification lands.
- Source text is untrusted data. Titles and summaries are rendered as text, and only http or https URLs become links.

## Alternatives considered

**Reuse the `citations` table for every source.** For: one table, one history field, no new schema object. Against: the table's check and documentation require a quoted span, and its rows are meant to pass the span verifier. Storing unverified sources there would blur the one distinction the PRD uses to define a citation. Why not chosen: a separate `message_sources` table keeps verified and unverified evidence separable at the storage layer.

**Store the source list as one JSON column on `messages`.** For: one write and one read, and the list is always fetched with its answer. Against: the rows are first-class review evidence, the physical data model documents each table, and a JSON column would need a migration to become queryable when the verifier arrives. Why not chosen: the normalized table is cheap at this scale and matches the existing `message_steps` and `tool_calls` pattern.

**Derive the source list only from `data-tool` parts in the frontend.** For: no new stream frame and no backend snapshot. Against: every consumer would need to know the internal result shape of four tools, replay would need the same parsing, and a tool result cap could change the payload the UI depends on. Why not chosen: the explicit `data-sources` frame is the stable contract and is persisted in the trace for replay.

**Keep the pane aggregated across all answers.** For: one list for the whole conversation, no selection state. Against: markers restart at 1 for each answer, so one flat list would contain several `[1]` rows with different meanings. Why not chosen: the pane is scoped to the answer whose capsule was clicked.

**Keep the citation chip row and the inline Sources disclosure, and add the capsule.** For: no removal risk. Against: three entry points with different semantics and duplicated source content. Why not chosen: one entry point is the point of the change.
