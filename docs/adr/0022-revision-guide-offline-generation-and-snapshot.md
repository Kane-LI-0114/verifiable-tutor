# ADR-0022: Revision guide generated offline and shipped as a snapshot

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-25 |
| **Deciders** | Recorded by the engineering agent for the peter-dev branch |

## Context

Students need a way to review the course beyond asking questions and taking self-tests. The existing `config/knowledge_points.yaml` has 24 hand-written points over five topics; it is coarse, it does not cover the later lectures, tutorials, or assignments, and it is not tied to document ids. The 16 tracked documents already have Qwen summaries and page-anchored OCR chunks, so the outline and the review text can be built from material the repository already ships.

Generating a chapter on every page view would be slow, costly, and unstable. A fresh checkout also has no runtime database, so a guide stored only in the local SQLite file would be invisible to a reviewer who clones the repository.

## Decision

**The outline comes from the summaries.** `build_revision_guide.py outline` reads the 16 `kb_documents` summaries, makes one DeepSeek call, and asks for study themes. The model chooses how many themes the material needs. The parser requires every document to appear exactly once and rejects an unknown, missing, or repeated document. `revision_themes` and a one-theme-per-document `revision_documents` row store the result.

**Each chapter is generated offline from the document's chunks.** `build_revision_guide.py docs --doc <id>` reads the document's OCR chunks, batches them by size, and calls DeepSeek once per batch in English. The prompt fixes only three things: the chapter is a key-point review, every knowledge point is an H2 heading, and the heading ends with an invisible `<!-- page: N -->` marker. The rest of the structure is the model's. The batches are merged in order, duplicate headings are dropped, and a multi-batch chapter uses the document summary as its overview, because the first batch sees only the first pages.

**The parser stores clean Markdown and structured points.** `revision/document.py` splits on H2 headings outside code fences, extracts the page number, removes every page comment from the title, body, and overview, and rebuilds the chapter without comments. `revision_points` stores each heading and body; `revision_documents` stores the clean chapter and its overview. A document with no knowledge points is rejected.

**The UI is a mind map with three-level progress.** `/revision` shows the course node, full-width theme nodes, and each theme's documents below it. Generated documents show `mastered/total` and open `/revision/docs/:docId`; ungenerated ones are disabled. The detail page renders the overview and one H2 point after another with a checkbox, and records self-checks in `revision_progress`. The download route returns the stored clean Markdown, so the internal page markers never reach the reader.

**The guide ships with the repository.** `build_revision_guide.py export` writes `data/revision/guide.json` (themes, chapters, points, no user progress) and the snapshot is tracked. On a first start, the backend imports the tracked corpus and then the snapshot when the tables are empty. A fresh checkout therefore opens a populated guide without a TACC job or a paid model call. The import is skipped once the tables have rows.

**The schema moves to version 10 and then 11.** Version 10 adds the outline tables. Version 11 adds the generated chapter columns, the points, and the per-user progress.

## Consequences

**Positive:**

- Opening the guide costs no model call, and the same content is reproducible from the tracked snapshot.
- The outline and chapter rules are deterministic enough to test without the model: the parsers validate the mapping, the headings, and the page markers.
- The page anchors connect a self-check back to the PDF page, and the clean download is a normal study document.
- A fresh clone is usable immediately because the corpus and the guide are both tracked.

**Negative:**

- Regenerating a chapter after the prompt or corpus changes can change point titles, which changes point ids and resets the self-check for the changed headings. There is no regeneration UI in this iteration.
- The snapshot adds about 0.6 MB to the repository and duplicates the chapter text in both the document row and the point bodies.
- A multi-batch chapter uses the document summary as its overview instead of a model-written whole-document overview; the overview is less tailored than a single-batch intro.

**Neutral:**

- The guide is English content with bilingual UI chrome.
- Self-check progress is separate from the practice mastery bars; the two are not merged in this iteration.
- The outline stores model and prompt version, but a rebuild currently replaces the outline and its chapters.

## Alternatives considered

**Generate the chapter on first view.** For: no build step and always current. Against: a slow first paint, a paid call per document, and content that changes between readers. Why not chosen: an offline build with a tracked snapshot is reproducible and free at view time.

**Keep the guide only in `data/app/app.sqlite3`.** For: no JSON parser and no import step. Against: a fresh checkout has no database and no guide, which is the exact problem this change fixes. Why not chosen: the snapshot is the deliverable.

**Commit a seed SQLite database.** For: one file and no import logic. Against: a binary artifact, duplicated corpus data, and a store that is hard to review in a diff. Why not chosen: the tracked JSON follows the existing `data/index` and `data/kb` snapshot pattern.

**Render the chapter from the raw Markdown with a custom H2 renderer.** For: the literal document string. Against: mapping a rendered heading back to a point id is fragile. Why not chosen: the parser stores intro and points separately, and the page renders those in one continuous column, which preserves the document feel without string matching.

**Reuse `config/knowledge_points.yaml` as the leaves.** For: no generated taxonomy. Against: 24 points over five topics, no document anchors, and no coverage of the later material. Why not chosen: the leaves must be per document and fine-grained.
