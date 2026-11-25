# Verifiable Tutor final deck, edition brief

This is the frozen brief for the three decks built on branch `presentation/three-editions`.
The `ppt-master` edition is built in another conversation and is not part of this branch.

## Hard rules

- 20 pages: 18 main + 2 appendix. All English. 16:9.
- Palette: paper `#FAFAFA`, ink `#09090B`, cobalt `#1447E6`, line `#E5E5E5`, graphite `#0A0A0A`/`#171717`, failure `#C10007`.
- Fonts: Georgia display, Arial body, Courier New mono. Do not use Source Serif 4, Helvetica Neue, or Menlo in PPTX/PDF.
- Typography, PPTX: exactly two sizes per slide. Display 40pt (cover 64pt) and body 16pt. Labels, captions, table cells, and page numbers use body 16pt. 14pt is a whole-page fallback only; never mix 14 and 16 on one page.
- Typography, HTML: exactly two sizes per slide. Custom HTML display 80px (cover 112px) and body 32px. Stage HTML display 96px (cover 120px) and body 32px. All labels, captions, table cells, and page numbers use body 32px.
- Body copy target: at most 45 English words per slide. Prefer 20-35. Cut text instead of shrinking type.
- Every content slide needs at least one real visual: UI screenshot, course page thumbnail, icon cluster, or chart. Three to five Lucide-style icons per page is a good target.
- Blank space at the bottom of a slide should not exceed 15 percent of slide height.
- The verifier implementation is presented as Yoga's work. Kane's pages show the `verify_span` tool call, not verifier internals.
- Instructor and TA appear only on slides 17 and 18. The main narrative is the student loop.
- Use "source" for a retrieved page. Use "citation" only for a page plus a quoted span that passed the verifier. The `citations` table is still empty; do not claim every claim is verified.
- Ties are reported as ties. Grading is a tie across all four systems.
- Speaker notes are English and follow the 9:35 timing in `presentation/deck/content.js`.

## Page map

| # | Section | Title | Core message | Visual direction |
|---|---|---|---|---|
| 1 | Title | Verifiable Tutor | A course-grounded agent with evidence you can check. | Large title, blurred UI texture, team and three evidence chips. |
| 2 | 01 / Problem & Goal | A study loop students can trust. | A fluent answer is not a checkable answer. | Knowledge-base grid or course page image, three pain icons, three contract cards. |
| 3 | 02 / System | One local product. One batch backend on TACC. | Local product, TACC batch jobs, one turn flow. | Four-zone architecture with icons, chat inset, TACC job card. |
| 4 | 03 / Data | The data model makes the evidence chain durable. | 17 tables and FTS5; message_sources is the bridge; citations is next. | Four cluster cards, table names at body size, source-pane inset. |
| 5 | 04 / Stack | A small stack with one job per layer. | React, FastAPI, LangGraph, SQLite, BGE-M3, TACC. | Five-layer icon grid, large labels, no micro chips. |
| 6 | 05 / Functions / Agent | A typed loop, not a prompt. | Perception, planning, execution, reflection in a closed tool loop. | Four role cards with icons, loop arrows, tool chips. |
| 7 | 06 / Demo / Agent | Watch the loop work. | Five retrievals, two page reads, four span checks. | Full-bleed work-chain screenshot plus three callouts. |
| 8 | 07 / Functions / RAG offline | Build the evidence base on TACC. | OCR, page-first chunks, BGE-M3, local SQLite. 16 docs / 593 pages / 612 chunks. | Four-step pipeline with icons, course thumbnails, big stats. |
| 9 | 08 / Functions / RAG online | Retrieve pages, then let the model read. | BM25 plus BGE-M3, RRF, page-anchored tools. nDCG@5 0.849; hit@5 0.882. | Flow diagram plus source-pane inset and three bars. |
| 10 | 09 / Demo / RAG | Every paragraph names its source. | 14 retrieved pages, page-exact markers, source not yet citation. | Full-bleed source pane detail plus three callouts. |
| 11 | 10 / Functions / Knowledge | A conversation that lives beside the file. | Each turn carries doc_id and page_no; chat belongs to the file. | Full-bleed document chat screenshot plus three callouts. |
| 12 | 11 / Demo / Knowledge | From a marker to the exact page. | Click [3] on page 9, PDF moves to page 10, chat stays. | Before/after page images, chat excerpt, one arrow. |
| 13 | 12 / Verifier | A source is not a citation until the span passes. | Normalize, require exact page span, one repair, else abstain. | Pass/fail cards, page thumbnail, four step icons. |
| 14 | 13 / Functions / Practice & Policy | Practice and integrity. | Five question types, reference answer, five policy states. | Two large cards with icons, practice record example, timeline. |
| 15 | 14 / Demo / Practice & Policy | Practice, then check. | FlashAttention question; Assignment 3 refusal before deadline. | Full-bleed practice screenshot plus refusal screenshot. |
| 16 | 15 / Evaluation | We win on coverage. We tie on grading. | Coverage 5/5 vs 3/5; zero invented quotes; grading tie. | Three scorecards plus compact table at body size. |
| 17 | 16 / Failure & Limits | Tutorials are the hard slice. | Tutorial nDCG@5 0.617; dual granularity not free; four limits. | Bar chart, tutorial page thumbnail, four limit icons. |
| 18 | 17 / Conclusion | Verifiability is a system property. | Page-first retrieval, policy as code, coverage and quote integrity. Student loop end to end. | Three large takeaways, QR, team, Questions. |
| A1 | Appendix / A1 | One question, end to end. | SPA, API, gate, LangGraph, tools, verifier, model, store, SSE. | Icon sequence with shipped/planned legend. |
| A2 | Appendix / A2 | Evaluation method and TACC evidence. | 10 practice, 15 citation, 51 chunking; job 28067. | Two columns, big TACC numbers, method icons. |

## Key facts, frozen

- 17 application tables plus FTS5. `message_sources` bridges answer to doc/page. `citations` is empty.
- 16 documents, 593 pages, 612 chunks and vectors, 16 summaries.
- RAG online: hybrid nDCG@5 0.849, hit@5 0.882, 937 tokens@5. Two arms, 30 candidates each, RRF k=60.
- Citation study: invented quotes 0 vs 0, 2, 1; false "not in PDF" 0 vs 3, 0, 0; page accuracy exact vs good, best, minus one page.
- Practice: grounded 10/10 vs 10/10, 6/10, 6/10; off-topic 0/10 vs 0/10, 4/10, 4/10; coverage 5/5 vs 3/5; grading 10/10 all; citation accuracy 10/10 vs 8/10, 10/10, 9/10.
- Chunking failure: tutorial 0.617; concept 0.912; assignment 0.909; mechanism 0.875. Dual granularity hit@5 0.882 to 0.941, nDCG interval crosses zero, index cost 2.7 times. 51 test questions.
- TACC Qwen job 28067: 434 s cold start, 43.9 s eight-chunk build, 8/8 valid records.
- Timing 9:35; demo about 2:20; 25 s buffer.

## Source assets

Use `presentation/assets/screenshots` and `presentation/editions/shared/assets`.
Do not capture new screenshots unless the asset owner supplies them. Do not modify the originals.

## Files

- v2 PPTX: `presentation/editions/v2-pptx/`
- stage HTML: `presentation/editions/stage-html/`
- custom HTML: `presentation/editions/custom-html/`
- shared: `presentation/editions/shared/`
- QA: `presentation/editions/qa/`

Each builder owns only its directory. Do not commit; the root commits.
