<!-- ppt-master-schema: design-spec/v1 -->
# Verifiable Tutor B Edition - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | Verifiable Tutor B Edition |
| Canvas Format | PPT 16:9, 1280 x 720 |
| Page Count | 20 |
| Primary Language | en |
| Target Audience | CSIT6000V instructor, TA, and classmates. They know the course brief and have seen many agent demos; they will judge whether this is a task-oriented system with evidence, not a wrapper. |
| Communication Intent | Explain the student study loop and its evidence chain, demonstrate the three implemented surfaces, then persuade with an honest evaluation. Priority: establish the problem, prove it works, then bound the claims. |
| Desired Audience Outcome | They can say why page-anchored retrieval plus span verification differs from a fluent answer, have seen agent, RAG, knowledge, and practice work, and accept the wins, ties, and limits as credible. |
| Core Message / Ask / Action | Verifiability is a system property: page-anchored retrieval, a span verifier, and policy as code make answers and practice checkable. The evaluation also shows where it still fails. |
| Delivery Context | Primary: a 10-minute live course presentation on the same machine, including an embedded demo, with a hard stop. Secondary: the submitted PDF is read afterward without the presenter. |
| Artifact Afterlife | Submitted as the course final-presentation PDF and kept in the repository as the project record; appendix pages answer questions after the talk. |
| Reading Mode | presentation |
| Content Strategy | Balanced: keep every fact and number from the approved v1, preserve the 18+2 page structure, and re-architect copy and visuals for 16pt body text, larger evidence, and a 10-minute live talk. No invented claims. |
| Design Style | Evidence Ledger: editorial grid, hard-edged evidence plates, no glass, no shadows |
| AI Image Acquisition Path | not applicable |
| Generation Mode | continuous |
| Spec Refinement | disabled |
| Speaker Notes | enabled - final Stage-2 proactive policy |
| Custom Animations | disabled - final Stage-2 proactive policy |
| Narration Audio | disabled - final Stage-2 proactive policy |
| Created Date | 2026-11-25 |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| Format | PPT 16:9 |
| Dimensions | 1280 x 720 |
| viewBox | 0 0 1280 720 |
| Margins | 64 px left and right; 56 px top; 48 px bottom |
| Content Area | x 64..1216, y 56..672 |

## III. Visual Theme

### Theme Style

- **Mode**: custom
- **Mode References**: pyramid, briefing
- **Mode Behavior**: Pyramid for the main argument: each page opens with a judgment and then shows one field of evidence; the three demo pages act as proof turns, and the closing page names the system property before the limits. Briefing restraint is used for architecture, data, and stack pages so they inform without becoming extra theses.
- **Visual style**: custom
- **Visual Style References**: editorial, swiss-minimal
- **Visual Style Behavior**: Editorial column rules and running heads meet a Swiss twelve-column grid. Georgia display sits hard against the upper-left margin; Arial 16pt body sits on a strict baseline. No rounded cards, no shadows, no glass. Course pages and UI screenshots are full rectangular evidence plates. Cobalt marks the page edge, rules, markers, and key numbers only.
- **Theme**: A course dossier whose pages can be audited
- **Tone**: composed, academic, evidence-first, not promotional

### Color Scheme

| Role | HEX | Purpose |
| --- | --- | --- |
| Background | #FAFAFA | Paper field for every light page |
| Secondary background | #F4F4F5 | Quiet bands, table zebra, inset mats |
| Primary | #09090B | Display type and the darkest rules |
| Accent | #1447E6 | Page edge, markers, key numbers, one active state |
| Secondary accent | #52525B | Graphite for secondary labels and muted evidence |
| Body text | #18181B | Body copy and table text |
| Secondary text | #52525B | Captions, source lines, page folios |
| Divider | #E4E4E7 | Hairlines, grid, frame edges |
| Failure | #C10007 | Failure marks, refusal state, negative comparison only |
| Surface | #FFFFFF | Mat under screenshots and course pages |
| Grid | #E4E4E7 | Twelve-column construction lines at low contrast |

## IV. Typography System

### Font Plan

| Role | Character (Reference) | Primary | English if non-English | Fallback tail |
| --- | --- | --- | --- | --- |
| Title | Editorial serif, high contrast, old-style figures | Georgia | - | serif |
| Body | Neutral grotesque, high legibility at projection size | Arial | - | sans-serif |
| Code | Monospace for paths, identifiers, and file names | Courier New | - | monospace |

- **Title stack**: Georgia, Times New Roman, serif
- **Body stack**: Arial, Helvetica, sans-serif
- **Code stack**: Courier New, monospace

### Font Size Hierarchy

| Purpose | Anchor Size (px) |
| --- | ---: |
| Body | 21.33 |
| Title | 53.33 |
| Subtitle | 21.33 |
| Annotation | 21.33 |
| Cover title | 85.33 |
| Code | 21.33 |

- **Two-size rule**: the cover uses 85.33 px and 21.33 px; every other page uses 53.33 px and 21.33 px. Subtitle, annotation, and code are aliases at body size, never extra sizes. Page numbers, captions, table cells, labels, and source lines all use 21.33 px.
- **Normalization note**: the Stage-2 role defaults 38 / 28 / 16 px were normalized to 40pt / 16pt / 64pt because the 16 px annotation equals 12pt, below the explicit 14pt floor, and a third role would violate the one-page-two-sizes rule.

## V. Layout Principles

### Deck-wide Direction

- **Hierarchy direction**: page title first, then one dominant evidence field, then a short interpretation line; the eye never has to hunt for the claim.
- **Composition tendency**: a twelve-column grid with a hard left margin; large rectangular evidence plates; rules instead of cards; asymmetric splits at 5/7 or 7/5, not centered decks.
- **Cross-page continuity**: a thin top rule with section number, a cobalt page-edge tick, a Georgia title at the same x, a source/page folio at the lower right, and a repeated paper field. Demo pages switch the field to a full plate while keeping the folio.
- **Spacing posture**: open around titles, dense inside evidence plates; no page ends with more than 15% empty height.
- **Spacing anchors**: page margin 64 px; block gap 24 px; column gutter 24 px; corner radius 0 px; body leading 30 px.

## VI. Icon Usage Specification

- **Primary bundled library**: tabler-outline
- **Stroke Width**: 2
- **Brand-logo library**: none

| Icon Path | Suitable Scenarios |
| --- | --- |
| tabler-outline/search | retrieval, query, find the page |
| tabler-outline/file-text | sources, documents, course pages |
| tabler-outline/shield-check | verification, policy, pass state |
| tabler-outline/flask | practice, experiment, question generation |
| tabler-outline/database | SQLite, tables, index |
| tabler-outline/cpu | model, backend, TACC batch |
| tabler-outline/git-branch | graph, replay, branch of reasoning |
| tabler-outline/quote | span, citation, exact quote |
| tabler-outline/check | pass, success, agreement |
| tabler-outline/x | fail, refusal, missing evidence |
| tabler-outline/layers-intersect | stack layers, fusion, RRF |
| tabler-outline/box | package, container, chunk |
| tabler-outline/gauge | evaluation metric, score |
| tabler-outline/book | course material, study loop |
| tabler-outline/arrow-right | next step, handoff, sequence |
| tabler-outline/terminal-2 | typed tools, execution, code |
| tabler-outline/alert-triangle | limitation, warning, failure |
| tabler-outline/clock | deadline, time budget, latency |
| tabler-outline/route | turn flow, pipeline, path |
| tabler-outline/zoom-scan | span locate, exact page, inspection |
| tabler-outline/link | marker to page, bridge, URL target |
| tabler-outline/message-chatbot | chat, tutor, conversation |
| tabler-outline/list-check | scoring points, rubric, checklist |
| tabler-outline/calendar-event | dated policy, deadline registry |
| tabler-outline/lock | disclosure gate, server-side 403 |
| tabler-outline/eye | perception, visible evidence |
| tabler-outline/scan | OCR, page parse, index build |
| tabler-outline/bulb | planning, hint, reflection |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Image pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| images/ui-rag-source-pane.png | 2756 x 1626 | 1.695 | Cover field and RAG source-pane demo | Screenshot | Full-width evidence plate; on the cover it sits under a graphite scrim with the title at left | no-crop | user | Existing | presentation/assets/screenshots/rag-source-pane.png | none | hero_page |
| images/course-lecture2-p09.webp | 2000 x 1500 | 1.333 | Course page evidence for problem, offline RAG, verifier | Course page | Tall page plate with a cobalt rule at its left edge; preserve the page number and footer | no-crop | user | Existing | data/corpus/images/ACS_lecture_2_2026F.p009.webp | none | local |
| images/ui-agent-workchain.png | 1556 x 1231 | 1.264 | Agent work-chain demo | Screenshot | Full-width evidence panel; three callouts on the right align to the tool rows | no-crop | user | Existing | presentation/assets/screenshots/agent-workchain.png | none | hero_page |
| images/course-lecture2-p10.webp | 2000 x 1500 | 1.333 | Corpus sample in offline RAG | Course page | Small staggered page plate beside p09 and p11 | no-crop | user | Existing | data/corpus/images/ACS_lecture_2_2026F.p010.webp | none | local |
| images/course-lecture2-p11.webp | 2000 x 1500 | 1.333 | Corpus sample in offline RAG | Course page | Small staggered page plate beside p09 and p10 | no-crop | user | Existing | data/corpus/images/ACS_lecture_2_2026F.p011.webp | none | local |
| images/ui-rag-source-detail.png | 756 x 1436 | 0.526 | Source-list close-up in online RAG | Screenshot | Narrow tall inset at the right edge, cropped only by the page edge, never inside the list | no-crop | user | Existing | presentation/assets/screenshots/rag-source-detail.png | none | local |
| images/ui-knowledge-page9.png | 2776 x 1876 | 1.480 | Knowledge chat beside PDF page 9 | Screenshot | Large two-up evidence plate; chat left, PDF right; callouts above the PDF | no-crop | user | Existing | presentation/assets/screenshots/kb-page9.png | none | hero_page |
| images/ui-knowledge-page10-detail.png | 1896 x 1676 | 1.131 | Page 10 after clicking marker [3] | Screenshot | Right-hand after panel; keep the chat strip and page number visible | no-crop | user | Existing | presentation/assets/screenshots/kb-page10-detail.png | none | hero_page |
| images/ui-practice-question.png | 1786 x 1321 | 1.352 | Practice question demo | Screenshot | Left demo plate; question, [3] marker, and points stay visible | no-crop | user | Existing | presentation/assets/screenshots/practice-question.png | none | hero_page |
| images/ui-policy-refusal.png | 1506 x 571 | 2.637 | Policy refusal demo | Screenshot | Full-width refusal banner; the policy sentence and offer stay legible | no-crop | user | Existing | presentation/assets/screenshots/policy-refusal.png | none | local |
| images/course-tutorial4-p40.webp | 2000 x 1500 | 1.333 | Tutorial page for the failure case | Course page | Right-side page plate; preserve the tutorial footer and page number | no-crop | user | Existing | data/corpus/images/Tutorial_4.p040.webp | none | local |

## IX. Content Outline

### Part 1: Opening

#### Slide 01 - Verifiable Tutor

- **Audience move**: Arrives expecting another course demo -> sees a product whose evidence is visible before the claim.
- **Relationships**: Product name is the hook; three demo counters are the proof; team and course are ownership and context.
- **Composition**: Full-bleed UI field under a graphite scrim; oversized Georgia title at left; counters along the bottom; team line at the lower left.
- **Title**: Verifiable Tutor
- **Core message**: A course tutor whose answers and practice items can be checked.
- **Content**:
  - Kicker: CSIT6000V / FINAL PRESENTATION / FALL 2026
  - Display: Verifiable Tutor
  - Lead: Every answer names its page. Every practice item carries a reference.
  - Counters: 5 retrieval calls · 2 page reads · 4 span checks
  - Team: LI Jinchuan · TIAN Yujia · XIE Yifeng / 21188271 · 21201619 · 21322152
  - Course: Advanced AI Computing and Systems · Fall 2026
- **Images**: images/ui-rag-source-pane.png full bleed, graphite scrim at about 55%, cobalt hairline at the lower edge.
- **Cover impact**: The product name over a real source pane: evidence before claim.

#### Slide 02 - A study loop you can check

- **Audience move**: Accepts the generic tutoring problem -> recognizes three concrete trust gaps in one student's week.
- **Relationships**: Three gaps are parallel; each maps to one product surface; the bottom success strip is their conjunction.
- **Composition**: Three ruled rows at left; a full-height course page at right; a contract strip along the bottom.
- **Title**: A study loop you can check.
- **Core message**: One CSIT6000V student, three trust gaps, one measurable loop.
- **Content**:
  - Lead: Dense slides. Assignment-scale practice. A deadline policy.
  - FIND THE PAGE: A fluent answer can still be wrong; the student cannot inspect it.
  - PRACTISE SAFELY: Questions drift off-course; grading hides its reasoning.
  - KNOW THE RULES: A complete solution may be forbidden before the deadline.
  - SUCCESS: grounded answer · page-exact source · reference answer · dated policy
  - Baselines: Doubao · Gemini · Qwen
- **Images**: images/course-lecture2-p09.webp at right; preserve the page number and footer.

### Part 2: System

#### Slide 03 - One product, one batch backend

- **Audience move**: Expects a cloud service -> understands one local product plus a required batch dependency.
- **Relationships**: SPA is parent to the API; the API contains five services; TACC is a batch dependency, not an inbound service; the bottom strip orders five turn stages.
- **Composition**: Four-zone map; the TACC rail is separated by a heavy rule; the turn flow runs along the bottom.
- **Title**: One product, one batch backend.
- **Core message**: The laptop runs the product; TACC runs batch jobs; no inbound service.
- **Content**:
  - Lead: One origin, one local database, one required batch backend.
  - Client: React SPA
  - Local backend: FastAPI + SSE; LangGraph + typed tools; policy gate; retrieval + verifier; practice + grading; SQLite + local files
  - External: DeepSeek · MiMo · QQ Mail
  - TACC batch: OCR · index · Qwen KB (required); exec / eval (next)
  - Turn flow: Ask -> Plan -> Act -> Reflect -> Answer + cite
  - Note: Aligned with PRD Figure 1
- **Visualization**: custom container map, no catalog chart.

#### Slide 04 - Every claim keeps its page

- **Audience move**: Sees a list of tables -> sees one evidence bridge from an answer to a document page.
- **Relationships**: Four clusters; message_sources bridges conversation to knowledge; citations is a named but empty child of knowledge; topic_progress is separate.
- **Composition**: Four-column table map; the bridge line runs from message_sources to the knowledge cluster; citations is dashed.
- **Title**: Every claim keeps its page.
- **Core message**: The schema makes the evidence chain durable; one bridge exists, one verified layer is still empty.
- **Content**:
  - Lead: 17 application tables + FTS5. One local SQLite file.
  - Access: users · login_sessions · verification_codes
  - Conversation: conversations · messages · message_steps · message_events · tool_calls · message_sources
  - Knowledge: kb_folders · kb_documents · kb_chunks · kb_chunks_fts · kb_index_state · knowledge_builds · citations
  - Learning: topic_progress
  - Highlight: message_sources = answer -> document / page
  - Honest label: citations = verified layer, next
- **Visualization**: custom table map, no catalog table.

#### Slide 05 - Small stack, clear jobs

- **Audience move**: Expects a long vendor list -> sees five layers, one job each.
- **Relationships**: Six bands stack; interface depends on API; agent and evidence live inside the API; batch and external are edges.
- **Composition**: Full-width bands, icon at the left, three chips at the right, a cobalt layer number at the far left.
- **Title**: Small stack, clear jobs.
- **Core message**: Five layers, one job each, with no hidden framework.
- **Content**:
  - Lead: Pinned in package.json and pyproject.toml.
  - INTERFACE: React SPA · Vite · Tailwind
  - API: FastAPI · SSE · SQLite
  - AGENT: LangGraph · typed tools
  - EVIDENCE: FTS5 · BGE-M3 · span verifier
  - BATCH: TACC · PaddleOCR · Qwen
  - EXTERNAL: DeepSeek · MiMo · QQ Mail
  - Note: One process; one origin; local data.
- **Visualization**: custom stack bands, no catalog chart.

### Part 3: Agent and retrieval

#### Slide 06 - A typed loop, not a prompt

- **Audience move**: Assumes an agent is a prompt -> can name four stages and the five tools it may call.
- **Relationships**: Four stages form a loop; tools are a closed set called in execution; reflection returns to planning or to an answer.
- **Composition**: Circular loop at the left; a tool column at the right; one-sentence stage labels on the ring.
- **Title**: A typed loop, not a prompt.
- **Core message**: Perception, planning, execution, reflection; one closed tool set.
- **Content**:
  - PERCEPTION: message, history, document context, tool results.
  - PLANNING: model-driven inside the agent node; closed tool set.
  - EXECUTION: validate arguments; stream results.
  - REFLECTION: verify_span; retry; abstain when evidence is missing.
  - Tools: course_search · read_course_page · web_search · web_fetch · verify_span
  - Note: Every step persisted; every turn replayable.
- **Visualization**: custom loop diagram, no catalog chart.

#### Slide 07 - Watch the loop verify a span

- **Audience move**: Has heard the loop described -> sees a real turn prove it.
- **Relationships**: Three counters describe one turn; the expanded call is the fourth verify_span; span verified is the terminal state.
- **Composition**: Full-width work-chain panel; three callouts on the right aligned to the tool rows; one cobalt rule under the result.
- **Title**: Watch the loop verify a span.
- **Core message**: A real turn: five retrievals, two page reads, four span checks, one span verified.
- **Content**:
  - Lead: doc_id ACS_lecture_2_2026F · page 9 · exact quote.
  - Counter: 5 retrieval calls
  - Counter: 2 page reads
  - Counter: 4 verify_span calls
  - Output: span verified
  - Note: The work chain and trace are persisted.
- **Images**: images/ui-agent-workchain.png full-width.

#### Slide 08 - Build the evidence base on TACC

- **Audience move**: Wonders where the course evidence comes from -> sees the offline build and its scale.
- **Relationships**: Four ordered steps; three page images are samples of the corpus; the numbers are the resulting scale.
- **Composition**: Horizontal pipeline at the top; three course-page plates at the bottom; the scale numbers sit between them.
- **Title**: Build the evidence base on TACC.
- **Core message**: OCR, page-first chunk, BGE-M3 embed, local import; the index never runs at request time.
- **Content**:
  - OCR: PaddleOCR on TACC
  - CHUNK: page-first, 450-token budget
  - EMBED: BGE-M3 vectors
  - IMPORT: local SQLite + float32
  - Scale: 16 docs · 593 pages · 612 chunks · 612 vectors
- **Images**: images/course-lecture2-p09.webp, images/course-lecture2-p10.webp, images/course-lecture2-p11.webp as three staggered plates.

#### Slide 09 - Retrieve pages, then verify

- **Audience move**: Assumes retrieval returns text -> sees a page-anchored, two-retriever, verified path.
- **Relationships**: Two retrievers are parallel; RRF fuses; the page read precedes verify; the answer is last.
- **Composition**: Five-step horizontal flow; a metrics strip below; a tall source-list inset at the right.
- **Title**: Retrieve pages, then verify.
- **Core message**: The model writes the query; FTS5 and BGE-M3 return pages; RRF fuses; the model reads and checks.
- **Content**:
  - Flow: query -> FTS5 BM25 + BGE-M3 -> RRF -> read page -> verify_span -> answer
  - Metrics: nDCG@5 0.849 · hit@5 0.882 · 937 tokens@5
  - Note: 30 candidates per retriever; page-anchored text with a marker.
- **Images**: images/ui-rag-source-detail.png as a narrow tall inset at the right.

#### Slide 10 - Every paragraph names its source

- **Audience move**: Has seen retrieval described -> sees the source pane for one answer.
- **Relationships**: Fourteen sources are a flat ordered list; markers link paragraphs to pages; citation status is explicitly deferred.
- **Composition**: Full-bleed source pane; three labels on a left rail; markers enlarged, not decorated.
- **Title**: Every paragraph names its source.
- **Core message**: Fourteen retrieved pages in marker order; a source is not yet a citation.
- **Content**:
  - Lead: The source pane for one answer: 14 course pages.
  - Label: marker -> exact page
  - Label: source != citation
  - Label: verifier is next
  - Note: Markers are ordered by retrieval, not by confidence.
- **Images**: images/ui-rag-source-pane.png full-bleed.

### Part 4: Knowledge and verification

#### Slide 11 - Chat beside the exact page

- **Audience move**: Expects a file upload box -> sees a conversation that belongs to a file and a page.
- **Relationships**: The chat turn is parent to file context; system note and tool read are separate inputs; the file pane is a sibling view.
- **Composition**: Large UI plate; three callouts on the right; the page number circled with a cobalt rule.
- **Title**: Chat beside the exact page.
- **Core message**: Every turn carries doc_id and page_no; the conversation belongs to the file.
- **Content**:
  - Every turn: doc_id + page_no
  - System note: names the file and page; it does not inject page text
  - Model: must call read_course_page
  - Note: The file pane and chat share one route.
- **Images**: images/ui-knowledge-page9.png large two-up plate.

#### Slide 12 - From marker to page 10

- **Audience move**: Has seen the file-chat layout -> sees the exact jump from a marker to a page.
- **Relationships**: Before and after are two states; the chat is invariant; the PDF page changes.
- **Composition**: Two equal panels; a cobalt arrow between; labels above; before at left, after at right.
- **Title**: From marker to page 10.
- **Core message**: Clicking [3] moves the PDF to page 10 while the chat stays in place.
- **Content**:
  - BEFORE: p.9; answer cites [1] p.9 and [3] p.10
  - AFTER: p.10; chat unchanged
  - Note: The target is a URL to the exact page.
- **Images**: images/ui-knowledge-page9.png and images/ui-knowledge-page10-detail.png.

#### Slide 13 - A source is not a citation

- **Audience move**: Has seen sources -> understands the extra check that turns one into a citation.
- **Relationships**: Four ordered checks; pass and fail are a contrast; citation is the pass terminal, abstain the fail terminal.
- **Composition**: Four-step rail at the left; course page with a quote highlight at the right; pass/fail cards along the bottom.
- **Title**: A source is not a citation.
- **Core message**: A quoted span must occur on the cited page; pass becomes a citation, fail repairs once or abstains.
- **Content**:
  - NORMALIZE: whitespace and case
  - LOCATE: quoted span on the cited page
  - REPAIR ONCE: one bounded retry
  - CITATION / ABSTAIN: pass or no answer
  - Pass: exact quote on p.9 -> pass
  - Fail: missing span -> repair -> abstain
  - Honest label: persisting the verified layer is next.
- **Images**: images/course-lecture2-p09.webp with one highlight over the quoted passage.

### Part 5: Practice, evaluation, limits

#### Slide 14 - Practice, then check the policy

- **Audience move**: Separates practice from permission -> sees two guardrails with different mechanisms.
- **Relationships**: Practice and policy are parallel surfaces; five policy states are ordered from disclosure to refusal; refusal is the terminal state before the deadline.
- **Composition**: Two columns split by a heavy rule; practice at the left, policy timeline at the right.
- **Title**: Practice, then check the policy.
- **Core message**: One question record, five types, one dated disclosure gate.
- **Content**:
  - Practice: 5 types · reference answer · scoring points · page markers
  - Grading: choice deterministic; open and code model-graded
  - Policy: allowed · hint · outline · concepts · refuse
  - Enforcement: server-side 403
  - Before 2026-11-29: a complete Assignment 3 solution is refused; concepts, example, and hint are offered
  - Note: Policy is code, not prompt.
- **Visualization**: custom policy timeline, no catalog chart.

#### Slide 15 - A question, then a refusal

- **Audience move**: Has heard the guardrails described -> sees both work on the real UI.
- **Relationships**: Two screenshots are parallel evidence; practice shows generation, policy shows refusal; both share the course context.
- **Composition**: Practice plate at 60% left; refusal banner at 40% right; two large labels.
- **Title**: A question, then a refusal.
- **Core message**: A real practice item, and a real policy refusal.
- **Content**:
  - PRACTICE: FlashAttention single choice; [3] marker; 2 points.
  - POLICY: Assignment 3 complete solution refused before 2026-11-29; concepts, example, hint offered.
  - Note: Same user, same course, two guardrails.
- **Images**: images/ui-practice-question.png and images/ui-policy-refusal.png.

#### Slide 16 - We win coverage; we tie grading

- **Audience move**: Expects a broad claim -> sees a narrow win, two ties, and a separate integrity strip.
- **Relationships**: Three practice metrics are parallel; citation integrity is a separate three-part strip; baselines are a contrast, not decoration.
- **Composition**: Three KPI tiles across the top; citation strip along the bottom; no table.
- **Title**: We win coverage; we tie grading.
- **Core message**: On ten practice questions, groundedness ties the best baseline, coverage leads, grading ties.
- **Content**:
  - GROUNDED: 10/10; best baseline 10/10; tie
  - COVERAGE: 5/5; best baseline 3/5; win
  - GRADING: 10/10; all systems; tie
  - Citation integrity: 0 invented quotes (baselines 0 / 2 / 1); 0 false "not in PDF" (3 / 0 / 0); page exact (good / best / -1)
  - Method: 10 practice + 15 citation questions; ties reported as ties.
- **Visualization**: custom KPI tiles, no catalog table.

#### Slide 17 - Tutorials are the hard slice

- **Audience move**: Has seen the wins -> sees the specific failure and the limits of the fix.
- **Relationships**: Four question types are a descending comparison; four limits are parallel caveats; the chart is evidence, the limits are interpretation.
- **Composition**: Horizontal score bars at the left; tutorial page at the right; four limits along the bottom.
- **Title**: Tutorials are the hard slice.
- **Core message**: Tutorial nDCG@5 is 0.617; dual-granularity helps hit@5 but not enough at 2.7x cost.
- **Content**:
  - Bars: Tutorial 0.617 · Mechanism 0.875 · Assignment 0.909 · Concept 0.912
  - Limit: tutorial pages bundle several sub-tasks on one page
  - Limit: dual chunking 0.882 -> 0.941 hit@5; +0.059; 2.7x cost; nDCG CI crosses zero
  - Limit: citations are not persisted yet
  - Limit: instructor/TA console is partial
- **Images**: images/course-tutorial4-p40.webp at right.
- **Visualization**: custom horizontal score bars, no catalog chart.

#### Slide 18 - Verifiability is a system property

- **Audience move**: Has seen the evidence and the failure -> leaves with three system properties and a bounded next list.
- **Relationships**: Three takeaways are a conjunction; future items are parallel next surfaces; Q&A is the terminal move.
- **Composition**: Three large takeaways at the left; future list and Q&A at the right; team line along the bottom.
- **Title**: Verifiability is a system property.
- **Core message**: Page as retrieval unit, policy as code, evaluation that separates grounding from grading.
- **Content**:
  - PAGE IS THE UNIT: retrieval, citation, and UI all use the page.
  - POLICY IS CODE: five states from a dated registry; server-side 403.
  - EVALUATION SPLITS GROUNDING FROM GRADING: wins and ties are reported separately.
  - Future: operator console for instructor/TA · citation persistence · TACC exec · multi-course.
  - Close: Questions / github.com/Kane-LI-0114/verifiable-tutor / LI Jinchuan · TIAN Yujia · XIE Yifeng
- **Closing impact**: The takeaway names the system property; Q&A follows without a cover reprise.

### Part 6: Appendix

#### Slide 19 - Appendix A1: One question, end to end

- **Audience move**: Wants the full path after the talk -> can trace one question through the system.
- **Relationships**: Nine ordered nodes; the policy gate branches before the agent; the verifier sits between tool output and the model answer; SSE returns to the SPA.
- **Composition**: Horizontal swimlane with numbered nodes; solid and dashed legend at the top.
- **Title**: One question, end to end.
- **Core message**: SPA -> API -> policy -> LangGraph -> tools -> verifier -> model -> store -> SSE; solid is shipped, dashed is planned.
- **Content**:
  - Nodes: React SPA · FastAPI · policy gate · LangGraph · typed tools · span verifier · model adapter · SQLite + JSONL · SSE
  - Legend: solid = shipped; dashed = planned
  - Note: TACC is a batch lane, not an inbound node.

#### Slide 20 - Appendix A2: Method and TACC evidence

- **Audience move**: Wants the evidence behind the numbers -> sees the method and one job receipt.
- **Relationships**: Method and infrastructure evidence are parallel; the TACC numbers are one job, not a benchmark average.
- **Composition**: Two columns: method at the left, TACC receipt at the right; numbers in Courier New at body size.
- **Title**: Method and TACC evidence.
- **Core message**: Ten practice and fifteen citation questions against three hosted assistants; job 28067 is one TACC receipt.
- **Content**:
  - Method: 10 practice questions · 15 citation questions · Doubao / Gemini / Qwen
  - Retrieval: 51 test questions; nDCG@5 and hit@5
  - TACC job 28067: 434 s cold start · 43.9 s 8-chunk build · 8/8 valid
  - Note: TACC is required for batch model serving; no inbound service.

## X. Speaker Notes Requirements

- **Generation**: enabled
- **Filename**: match each SVG filename under notes/
- **Content**: English, one paragraph per slide, 20-45 seconds; open with the claim, give one piece of evidence, and hand off to the next page. Never read the slide text. Treat source and citation as different states; state the empty citations table whenever verification persistence is discussed.
- **Total duration**: 9:30, with a 30-second buffer under the 10-minute hard stop
- **Notes style**: conversational, precise, honest; no promotional adjectives
- **Presentation purpose**: Explain the student study loop and its evidence chain, demonstrate the three implemented surfaces, then persuade with an honest evaluation. Priority: establish the problem, prove it works, then bound the claims.
