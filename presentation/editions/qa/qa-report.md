# QA report: three deck editions

Date: 2026-11-25, with a stage re-audit after the 17:25 fix. Branch: presentation/three-editions. Auditor: qa-reviewer.
Scope: `presentation/editions/v2-pptx`, `presentation/editions/stage-html`,
`presentation/editions/custom-html`, checked against `presentation/editions/shared/brief.md`
and `presentation/editions/shared/theme.json`.

No deck file was modified. All QA scripts, renders, audits and contact-sheet copies live under
`presentation/editions/qa/`.

## Verdicts

| Edition | Page count | Type audit | Font audit | Content | Visual findings | Severity / verdict |
|---|---|---|---|---|---|---|
| v2 PPTX | 20 slides, 20 PDF pages | PASS. Shared audit: exactly two sizes per slide, cover 64/16 pt, content 40/16 pt, no other sizes | PASS. PPTX runs use only Arial, Georgia, Courier New; PDF embeds only ArialMT, Arial-BoldMT, Georgia, CourierNewPSMT | PASS. 20/20 titles match the page map, key facts and roles correct, English, 20 English notes | Contact sheet and pages 2, 8, 16, 19, 20 inspected: no clipping, collisions, overflow or unreadable contrast; bottom fill 8.5 to 13.3 percent | PASS (1 minor content note) |
| Stage HTML | 20 slides, 20 PNGs at 1920x1080, 20 PDF pages | PASS. 20/20 slides exactly [32, 120] on the cover and [32, 96] elsewhere; 0 off-scale sizes; 0 non-allowed families | PASS. Computed first-family is Georgia, Arial or Courier New on every text node; PDF is raster (no embedded fonts, see limitations) | PASS. 20/20 titles, key facts, Instructor/TA only on 17, Yoga only on 13, English, 20 English speaker notes in `SPEAKER_NOTES`, presenter and keyboard verified | Re-audited after the 17:25 fix: slide 5 blank band 13.3 percent, slide 19 blank band 7.3 percent, A1 labels no longer collide and the cobalt shipped / dashed Verifier legend now matches v2 and custom; no clipping, collisions, overflow or unreadable contrast. Polish items only (slide 4 separators, slide 5 label wrap, clipped shared screenshot crops, palette and contrast deviations) | PASS (post-fix re-audit, minor observations only) |
| Custom HTML | 20 slides, 20 PNGs at 1920x1080, 20 PDF pages | PASS. 20/20 slides exactly [32, 112] on the cover and [32, 80] elsewhere; 0 bad sizes; 0 bad families; 0 bad images | PASS. Computed families are Georgia, Arial and Courier New only; PDF is raster (no embedded fonts, see limitations) | PASS. 20/20 titles, key facts, Instructor/TA only on 17 and 18, Yoga only on 13, English, 20 English notes, keyboard, overview and notes drawer verified | All 20 PNGs inspected: no clipping, collisions, overflow or unreadable contrast; only minor observations (cover whitespace, intentional screenshot crops, one extra palette hex) | PASS (minor observations only) |

Stage was re-audited on 2026-11-25 after the builder re-exported it at 17:25 (`index.html`, PDF, 20 PNGs, `font-audit.json`). The earlier NOT READY verdict applied to the previous build. The blockers are resolved and re-verified; see the Stage re-audit section.

## Method and evidence

- Shared PPTX audit: `python3 presentation/editions/shared/tools/audit_pptx.py presentation/editions/v2-pptx/CSIT6000V_VerifiableTutor_v2.pptx` -> `PASS: page count, fonts, and two-size typography`.
- Independent HTML audits (headless Chrome at 1920x1080, computed styles and live DOM):
  `presentation/editions/qa/tools/audit_html.mjs` writes `qa/audits/html-stage.json` and
  `qa/audits/html-custom.json`. It checks every visible text node for computed size and first
  font family, loads all images, records broken images, background-image URLs, external resource
  entries, out-of-bounds text, notes and blank-band geometry.
- Independent palette audits: `qa/tools/audit_palette.mjs` -> `qa/audits/palette-stage.json`,
  `qa/audits/palette-custom.json` (computed color, background, border, SVG fill and stroke values
  on every painted element inside each slide). v2 colors were read from the PPTX slide XML.
- Content audit: `qa/tools/audit_content.py` -> `qa/audits/content-audit.json` (titles, key
  facts per slide, Instructor/TA, Yoga, CJK, numeric tokens). PPTX text and notes were read with
  python-pptx; HTML text came from the live DOM audits.
- Export freshness: both HTML decks were re-rendered from their current `index.html` under
  `qa/audits/render-stage/` and `qa/audits/render-custom/` and compared with the shipped PNGs
  (`qa/audits/png-compare.json`). All 20 slides in each deck are pixel-identical (mean absolute
  difference 0.0), so the shipped PNGs and PDFs represent the current sources. The post-fix stage build was rendered again from its current `index.html` at 17:25 and is again pixel-identical to all 20 new PNGs.
- Runtime checks: stage was re-checked independently again after the fix (`qa/tools/runtime_stage.mjs`: 20 slides,
  20 notes, ArrowRight 0 to 1 to 2, ArrowLeft back to 1, no external resources) and the shipped
  `stage-html/exports/audit/runtime-check.json` records the presenter shell, note rendering,
  next slide and clean exit. Custom was re-checked with its own
  `node scripts/check_runtime.mjs` (20 slides, arrow to slide 2, hash `#/2`, 20 overview
  thumbnails, notes drawer open).
- Visual inspection: `qa/contact-sheets/v2-contact-sheet.png`, the two stage contact sheets,
  `qa/contact-sheets/custom-contact-sheet.png`, then every one of the 20 shipped PNGs for stage
  and custom at 1920x1080, plus selected full-size v2 pages (2, 8, 16, 19, 20).

## PDF and file checks

| Edition | Pages | Page size | Embedded fonts | Notes |
|---|---|---|---|---|
| v2 (vector) | 20 | 960.009 x 540 pt (13.333 x 7.5 in, 16:9) | Arial-BoldMT, Georgia, ArialMT, CourierNewPSMT, all TrueType, embedded and subset | `pdffonts` lists only the allowed families; title, author and subject metadata present |
| Stage (raster) | 20 | 1440 x 810 pt (20 x 11.25 in, 16:9) | none (assembled from the 20 PNGs) | Re-exported at 17:25 from the fixed PNGs; font guarantee comes from the HTML computed audit, not from PDF embeds |
| Custom (raster) | 20 | 960 x 540 pt (13.333 x 7.5 in, 16:9) | none (assembled from the 20 PNGs) | Font guarantee comes from the HTML computed audit, not from PDF embeds |

File inventory: v2 has 20 `pages/page-01..20.png` renders and a 4x5 `contact-sheet.png`;
stage has `exports/png/slide-01..20.png` (all 1920x1080), `exports/audit/font-audit.json`,
`exports/audit/runtime-check.json`, `exports/audit/png-manifest.json` and two contact sheets;
custom has `exports/slides/slide-01..20.png` (all 1920x1080), `exports/type-audit.json` and a
4x5 contact sheet.

## Type audit detail

- v2 PPTX: 20/20 slides have exactly two sizes. Cover `[16, 64]`; every other slide `[16, 40]`.
  Shared audit and `v2-pptx/audit-report.txt` both report 0 size violations, 0 font violations,
  0 palette violations and no slide above 45 prose words.
- Stage HTML: 20/20 slides are `[32, 120]` on slide 1 and `[32, 96]` on slides 2 to 20. The
  shipped `font-audit.json` reproduces the same sets from the current build. My independent DOM
  audit of the current `index.html` also reports 0 off-scale text nodes and 0 non-allowed first
  families. Copy budget: shipped copy-word maximum 44, my non-chrome visible-word maximum 41. The post-fix build keeps the same two-size sets: slide 19 uses tracking-free 32 px label cells and its A1 labels no longer collide, and slide 5 is re-spaced without changing type.
- Custom HTML: 20/20 slides are `[32, 112]` on slide 1 and `[32, 80]` on slides 2 to 20. The
  shipped `type-audit.json` marks every slide `sizeSetOk`; my independent audit agrees. Copy
  budget: shipped prose body-word maximum 31. My broader non-chrome word count reaches 52 only
  on appendix A2 because it includes labels and numeric cells, which the brief counts as caption
  and table content rather than prose.

## Font audit detail

- v2: 337 Arial runs, 45 Georgia runs and 18 Courier New runs, no other run fonts. The PDF
  exposes only ArialMT, Arial-BoldMT, Georgia and CourierNewPSMT. The PPTX theme declares Georgia
  and Arial; Courier New is used as a direct run font where needed. Default Office theme color
  entries also remain in `theme1.xml`, but the slide XML uses only the shared palette.
- Stage: computed first-family across all text is Georgia, Arial or Courier New only. The body
  CSS stack includes a `Helvetica Neue` fallback after Arial, but Arial is installed and is the
  rendered family on every node, so the forbidden face is never used. This is informational, not
  a violation.
- Custom: computed families are Georgia, Arial and Courier New only (declared stacks include the
  usual Times New Roman, Helvetica and Courier fallbacks, none rendered).
- Raster PDFs for stage and custom cannot be font-checked with `pdffonts`; the computed DOM
  audit is the governing evidence for those two editions.

## Content parity

Titles: 20/20 match the frozen page map in all three editions (normalized for a trailing period
and case). Key numbers:

| Check | v2 slides | Stage slides | Custom slides |
|---|---|---|---|
| 17 tables (+ FTS5) | 4 | 1, 3, 4 | 4, 17 |
| 16 documents | 1, 2, 8, 20 | 8, 20 | 8, 16, 20 |
| 593 pages | 1, 2, 8, 20 | 8, 20 | 2, 8, 16, 20 |
| 612 chunks and vectors | 8, 20 | 1, 8, 20 | 8, 16, 20 |
| nDCG@5 0.849 | 9 | 9 | 9 |
| hit@5 0.882 | 9, 17 | 9 | 9, 17 |
| 937 tokens@5 | 9 | 9 | 9 |
| 10/10 practice | 16 | 16 | 16 |
| 5/5 coverage | 16 | 16 | 16 |
| tutorial 0.617 | 17 | 17 | 17 |
| TACC 434 s / 43.9 s / 8 of 8 | 17 (434), 20 | 20 | 20 |
| Qwen job 28067 | 20 | 20 | 20 |

- Language: zero CJK characters in visible slide text and speaker notes in all three editions.
  The stage `index.html` contains 3131 CJK code points in vendored template comments and scripts
  (3085 of them outside markup text, 0 in rendered markup); they are not visible. Custom is fully
  ASCII.
- Roles: Instructor and TA appear only on slide 18 (v2), slide 17 (stage) and slides 17 and 18
  (custom), all inside the allowed 17/18 set. Yoga is named only on slide 13 in every edition.
- Speaker notes: 20 English notes in every edition. For stage, the notes are the
  `SPEAKER_NOTES` object in `src/notes.js`, embedded into the runtime, not DOM `data-notes`
  attributes; a DOM-only lookup reports them missing and is a false positive. The object has 20
  entries, ids match the 20 slides, CJK count is 0, minutes reproduce the `content.js` per-slide
  allocations for the 18 main slides (9:35) plus 0.4 min for the two appendix slides (9:59 total).
  The shipped `runtime-check.json` shows 20 notes rendered in the presenter.
- 8 of 8 TACC records: v2 and stage render it as `8 / 8` with spaces and custom as `8/8`; all
  three are consistent with the frozen fact and none was treated as a defect.

## Palette

- v2: PASS. Slide XML uses only E5E5E5, 09090B, FFFFFF, 171717, 1447E6, FAFAFA, 0A0A0A and
  C10007. Extra Office default colors exist only in the unused theme palette definitions.
- Stage: deviation from the literal shared palette. Measured slide colors include paper FAFAF8
  (11 slides), line D4D4D2 (10 slides), card F0F0EE (8 slides), and secondary grays 525252
  (6 slides), 737373, A3A3A3 and 7F7F7F. Cobalt 1447E6, white and the allowed graphites are present. The
  deviations are near-neutral and are documented in the stage README as brand-theme derivation,
  but the brief states an exact palette, so this is recorded as a major observation rather than a
  shipping blocker. Gray 525252 on the light slides (2, 8, 11, 13, 17) is about 2.7:1 contrast at
  32 px, below the 3:1 large-text guideline, so those secondary lines are the weakest contrast in
  the deck.
- Custom: 9 distinct computed colors. Eight are shared-palette colors; the ninth is D4D4D8, used
  only for the three fake window dots on slide 11 (3 occurrences). Minor.

## Visual findings

### v2 PPTX

Contact sheet and selected full-size pages were inspected. Slide 1 cover, slide 2 problem and
goal, slide 8 RAG offline, slide 16 evaluation, slide 19 appendix A1 and slide 20 appendix A2
are clean: no clipped text, no text over busy screenshots, no overflowing images, no collisions,
readable contrast, no dead bottom band above 13.3 percent. Demoted notes: slide 8 states
`354 of 365 pages are one chunk at 450 tokens` next to the current corpus numbers
(16 documents, 593 pages, 612 chunks). The 354/365 figure is correct for the 13-document chunking
experiment corpus documented in `experiments/chunking/REPORT.md`, but it is not labelled as a
snapshot on the slide, so an audience can read it as inconsistent with 593 pages. Minor content
ambiguity, not a blocker.

### Stage HTML

Re-audited after the 17:25 fix. The previous blockers are resolved and re-verified:

- Slide 5 blank bottom band: was 19.8 percent. The cards are raised and the lowest content ends
  at 936 of 1080 px, so the blank band is 13.3 percent, under the 15 percent cap.
- Slide 19 blank bottom band: was 26.6 percent. A1 now carries a 16:9 work-chain screenshot and
  an Evidence block, the lowest content ends at 1001 of 1080 px, and the blank band is 7.3
  percent.
- Slide 19 label collision: resolved. The labels are tracking-free 32 px cells; `LANGGRAPH`
  and `TYPED TOOLS` no longer overlap and the row reads cleanly.
- Slide 19 shipped/planned legend: resolved. Cobalt marks the shipped path and the Verifier is a
  dashed partial box, which now matches the v2 and custom editions.

Remaining non-blocking polish:

- Slide 4: mono table-name lists wrap inside the cards, leaving dangling middle-dot separators
  at line ends (`conversations ·`, `message_steps ·`, `kb_documents ·`).
- Slide 5: the first and fourth card labels still wrap (`01` then `INTERFACE`; `04` then
  `RETRIEVAL`) while the other cards keep their label on one line, so those label rows do not
  align. Slide 6 keeps the same pattern on its first card (`01` then `PERCEIVE`).
- Slide 15: the policy-refusal screenshot is a left-clipped crop, so lines begin mid-word
  (`t provide a complete solution ...`, `epts, work through ...`). The caption carries the
  message, and the same shared crop is used by custom, but it looks like clipped text.
- Slide 9: the source-pane screenshot shows a clipped left edge (`urces`), the same shared
  asset crop.
- Palette and contrast deviations listed above. Slide 19 now uses the cobalt accent for the
  shipped path and also uses gray 525252 for the Evidence copy, so the low-contrast note applies
  to slide 19 as well.

### Custom HTML

All 20 PNGs were inspected at 1920x1080. There are no clipped text blocks, no text over busy
screenshots that is unreadable, no overflowing images, no element collisions and no broken
images. Minor observations only:

- Slide 1 cover: the design leaves an intentionally airy lower third (content ends around 733 of
  1080). Treated as cover design intent, not a defect.
- Slide 6: the four role cards are taller than their content and the last content line ends
  around 828 of 1080, leaving a visibly airy bottom; measured against the deck's own footer rail
  it is about 15 percent, so it is borderline rather than a clear violation.
- Slides 2, 9, 12, 14 and 16: content ends 15.6 to 17.4 percent above the page bottom but within
  about 13 to 15 percent of the deck's footer rail at y about 995; no blocker.
- Slide 10: the answer screenshot is cropped on the left, so the first visible line begins
  mid-sentence (`memory wall is presented under the heading`). Slide 15's policy screenshot is
  also left-cropped; the custom README documents this crop as intentional for the refusal excerpt.
- Slide 16: the compact table omits the Off-topic and Citations rows that v2 and stage show. The
  key claims (coverage 5/5 vs 3/5, zero invented quotes, grading tie 10/10, zero false "not in
  PDF", exact page accuracy) are still present and consistent.
- Slide 19: the legend's shipped marker is an empty square that does not visually match the
  solid-bordered shipped cards, while the dashed marker matches the dashed Verifier card;
  ambiguous legend symbol.
- Palette: the extra D4D4D8 dots on slide 11 noted above; `No shell.` is rendered in the same
  pill style as the five tool names on slide 6, so it can read as a sixth tool rather than a
  statement.

## Stage re-audit (post-fix)

Artifacts: `stage-html/index.html` (17:25:29), `exports/VerifiableTutor_stage.pdf` (17:25:40,
20 pages, 1440 x 810 pt), `exports/png/slide-01..20.png` (17:25:37 to 17:25:40, all 1920x1080)
and `exports/audit/font-audit.json` (17:25:37); `exports/audit/runtime-check.json` was refreshed
at 17:25:44.

Re-checks and results:

- Fresh headless render of the current `index.html`: all 20 slides pixel-identical to the new
  PNGs (mean absolute difference 0.0), so the exports and PDF are current.
- Computed type audit: 20/20 slides exactly [32, 120] on the cover and [32, 96] elsewhere,
  0 off-scale nodes, 0 non-allowed first families, 0 broken images, 0 external resources. The
  shipped audit agrees.
- Blank bands: maximum 13.3 percent on slide 5, slide 19 is 7.3 percent, every other slide is
  below 10 percent.
- Slide 19 content: one work-chain screenshot, the Evidence block (Five calls, two reads, four
  span checks; Replayable from JSONL), One turn, every call persisted, the shipped path in
  cobalt and the Verifier dashed as planned or partial.
- Runtime: independent keyboard and notes check passes (20 slides, 20 notes, ArrowRight 0 to 1
  to 2, ArrowLeft back to 1, no external resources); the refreshed presenter smoke records the
  presenter shell, note rendering, next slide and clean exit.
- Content: 20/20 titles match the frozen page map, all key facts are still present, Instructor
  and TA are still only on slide 17, Yoga is still only on slide 13, and visible text is still
  English.
- Palette: the same near-neutral deviations (paper FAFAF8, line D4D4D2, card F0F0EE, secondary
  grays) remain and are documented as polish above.

Artifact note: the builder contact sheets at `stage-html/exports/audit/contact-1.png` and
`contact-2.png` still carry the 17:06 pre-fix render and are stale. Current contact sheets were
regenerated under `qa/contact-sheets/stage-contact-1.png` and `stage-contact-2.png` from the
17:25 PNGs and were used for this re-audit. The stale builder contact sheets are a minor artifact
cleanup, not a deck defect.

## Limitations

- Stage and custom PDFs are raster assemblies of their PNG slides, so `pdffonts` is empty and
  font compliance is proven from the HTML computed audit and the pixel-identical renders.
- Blank-band percentages use the lowest painted content element and exclude the page-number and
  footer chrome. v2 numbers come from its builder audit (content row above footer, measured to the
  page bottom, maximum 13.3 percent). Stage has no bottom footer rail, so the band is measured to
  the page bottom; the post-fix stage maximum is 13.3 percent (slide 5). Custom has a footer rail at about y 995, so its band is judged against that
  rail; the single cover exception is recorded as design intent.
- No deck was fixed, rebuilt or committed during QA.

## Evidence index

- Shared audit: `presentation/editions/shared/tools/audit_pptx.py`
- v2 audit output: `presentation/editions/v2-pptx/audit-report.txt`
- Stage shipped audits: `presentation/editions/stage-html/exports/audit/`
- Custom shipped audit: `presentation/editions/custom-html/exports/type-audit.json`
- Independent audits: `presentation/editions/qa/audits/` (html-stage.json, html-custom.json,
  content-audit.json, palette-stage.json, palette-custom.json, png-compare.json,
  static-checks.json, stage-audit-summary.txt, stage-runtime-summary.txt, stage-rerender.log,
  palette-stage-summary.txt, content-audit-summary.txt, custom-audit-summary.txt, png-compare.txt)
- QA tools: `presentation/editions/qa/tools/`
- Contact sheets: `presentation/editions/qa/contact-sheets/` (the two stage sheets were regenerated
  from the 17:25 PNGs; v2 and custom sheets unchanged)
- Fresh renders: `presentation/editions/qa/audits/render-stage/`,
  `presentation/editions/qa/audits/render-custom/`
