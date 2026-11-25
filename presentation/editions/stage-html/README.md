# Stage HTML edition: Verifiable Tutor

Swiss B (data-family swiss) stage deck for the CSIT6000V final presentation, built from
`guizang-ppt-skill`'s `template-swiss.html`. 20 slides: 18 main plus 2 appendix, 16:9,
authored on a fixed 1920x1080 stage.

## Deliverables

| Path | What it is |
|---|---|
| `index.html` | The deck (single page, local assets only, no network at runtime) |
| `exports/VerifiableTutor_stage.pdf` | 20-page PDF, 1440 x 810 pt (20 x 11.25 in), one slide per page |
| `exports/png/slide-01.png` ... `slide-20.png` | 20 PNG renders at exactly 1920x1080 |
| `exports/audit/font-audit.json` | Per-slide computed type and layout audit |
| `exports/audit/runtime-check.json` | Presenter and keyboard smoke test result |
| `exports/audit/contact-1.png`, `contact-2.png` | Visual QA contact sheets |

## Build and export

    cd presentation/editions/stage-html
    node build.mjs                 # assemble index.html from src/ + the installed template
    node scripts/render.mjs        # audit, 20 PNGs, PDF, presenter smoke
    node scripts/render.mjs --audit-only --skip-smoke

`build.mjs` reads the untouched template copy in `vendor/template-swiss.html`, injects the
brand theme, the override CSS, the 20 sections, the speaker notes, and the runtime, and inlines
the shared Lucide SVG icons. `scripts/render.mjs` serves the folder from a local ephemeral
HTTP server, drives headless Chrome over the DevTools protocol, and writes the exports.

## Source layout

| Path | Role |
|---|---|
| `src/slides.html` | 20 authored `<section class="slide">` blocks, one per page |
| `src/notes.js` | `SPEAKER_NOTES` for all 20 pages (timing from `presentation/deck/content.js`) |
| `src/deck.css` | Two-size typography, stage layout, print and export rules |
| `src/brand-theme.css` | Brand palette generated with `gz-theme.mjs brand '#1447E6' --family swiss` |
| `src/runtime.js` | Stage scaling, export mode, computed font and layout audits |
| `vendor/template-swiss.html` | Unmodified installed template |
| `vendor/icons/` | Shared Lucide icon pack, inlined at build time |
| `assets/motion.min.js` | Local Motion One copy (no CDN fallback) |
| `images/` | Screenshots, course thumbnails, and QR copied from the frozen shared asset pack |

## Hard typography rule (the deck's organizing constraint)

Every slide shows exactly two text sizes:

- Body: 32px (16pt at 1920x1080). Every label, kicker, caption, table cell, chrome line, page
  number and speaker-visible note stays at 32px.
- Display: 96px on content slides; 120px on the cover only.
- No 12, 14, 18, 22, 28px text anywhere on a slide. Copy is cut instead of shrunk.

The override is enforced by `src/deck.css`: `.stage *` pins every element to 32px Arial, and
only `.st-d` (96px) and `.st-cover` (120px) may use Georgia. This deliberately overrides the
skill's Swiss type scale and weight ladder (vmin sizes, ExtraLight display weights, Inter).
The two-size rule was prioritized, as the edition brief requires.

Fonts are a local system stack only: Georgia for display, Arial for body, Courier New for mono.
No Google Fonts, no CDN, no bundled font files.

## Swiss B theme and layout overrides

- Palette: paper `#FAFAF8`, ink `#0A0A0A`, cobalt `#1447E6`, line `#D4D4D2`, with
  `#F0F0EE` cards and `#171717` dark cards. One accent only: cobalt. Failure states use ink,
  never a second accent color.
- Brand theme: `node scripts/gz-theme.mjs brand '#1447E6' --family swiss` generated the
  `[data-theme="brand"]` block in `src/brand-theme.css`; `<html data-theme="brand">`.
- Fixed stage: each slide contains a 1920x1080 `.stage` scaled by `--stage-scale` so the
  presenter previews are pixel-accurate. At 1920x1080 the scale is 1.
- No WebGL, no ASCII canvas, no scroll animations. The stage look is pure CSS, screenshots, and
  SVG icons, so it survives headless rendering, PNG, and PDF.
- Layouts are registered with `data-layout` values (S02, S05, S07, S08, S11, S14, S15, S16,
  S17, S19, S20, S21, S22, SWISS-COVER-ASCII, SWISS-CLOSING-ASCII), but the page composition
  is a custom stage grid. The stock layout skeletons assume 5.6vh/5vw responsive type and
  cannot satisfy the two-size rule, which is the documented override.

## Validation evidence (last run)

- Font audit: 20/20 slides have exactly the allowed pair, `[32, 120]` on the cover and
  `[32, 96]` elsewhere. 0 off-scale text nodes, 0 unexpected font families, 0 broken images,
  0 external runtime resources.
- Copy budget: 44 words maximum body copy per slide (limit 45), unchanged by the QA fixes.
- Layout audit: no element crosses the 1920x1080 stage and no content extends below the 1040px
  safe line. Every bottom blank band is under 15%: the largest is 13.3% on slide 5, and A1 is
  7.8%. Slide 2 cards are 160px with a 16px row gap; slide 5 layer cards are 540px so the
  five-column composition fills the stage. Slide 19/A1 uses a 9-column 32px timeline with
  tracking-free labels that stay inside their 1/9 cells; cobalt boxes and the solid legend
  swatch mark the shipped path (SPA, API, Gate, LangGraph, tools, model, store, SSE), and the
  verifier is a dashed outlined box matching the dashed planned/partial legend. A 16:9
  work-chain screenshot with a body-32 caption ("One turn, every call persisted") and a
  body-32 evidence block fills the previously empty middle band.
- Presenter smoke: ArrowRight navigation, ESC overview open and close, presenter shell mount,
  per-slide notes rendered, next-page advance, and clean presenter exit all pass.
- `validate-swiss-deck.mjs`: passed, 20 slides.
- `validate-presenter-mode.mjs` stock script: 3 errors, only because it asserts the original
  Chinese timer labels ("开始计时" / "重置计时" / "继续计时") while the deck is English-only. The
  local English-label fork `scripts/validate-presenter-en.mjs` (generated by
  `scripts/make-presenter-en.mjs`) reports 20 slides, 20 notes, 10.0 planned minutes, 0 errors,
  0 warnings.

## Export method and compromises

- Chrome `Page.printToPDF` stalls on this 20-page, image-heavy deck in headless mode. The PDF is
  therefore assembled from the 20 verified 1920x1080 PNGs with Pillow at 96 dpi
  (`scripts/png_to_pdf.py`), which the task brief explicitly allows. `pdfinfo` reports 20 pages
  at 1440 x 810 pt.
- Speaker-visible presenter chrome was translated to English. The stock skill validator checks
  the original Chinese button text literally, hence the three documented assertions above.
- The cover uses solid graphite plus a cobalt evidence panel, with no background screenshot,
  after lead visual QA. Course thumbnails are 4:3 sources letterboxed or cropped, never
  stretched.
- `citations` is presented as the next layer, and the verifier is presented as Yoga's work, as
  the frozen brief requires. Instructor and TA appear only on slides 17 and 18.
- No files outside `presentation/editions/stage-html` are modified. The shared asset pack and the
  template copy are read-only inputs. Nothing is committed by this builder.

## Slide map

| # | id | Section | Title |
|---|---|---|---|
| 1 | cover | CSIT6000V / FINAL PRESENTATION / FALL 2026 | Verifiable Tutor |
| 2 | problem-goal | 01 / PROBLEM & GOAL | A study loop students can trust. |
| 3 | system | 02 / SYSTEM | One local product. One batch backend on TACC. |
| 4 | data | 03 / DATA | The data model makes the evidence chain durable. |
| 5 | stack | 04 / STACK | A small stack with one job per layer. |
| 6 | agent | 05 / FUNCTIONS / AGENT | A typed loop, not a prompt. |
| 7 | agent-demo | 06 / DEMO / AGENT | Watch the loop work. |
| 8 | rag-offline | 07 / FUNCTIONS / RAG OFFLINE | Build the evidence base on TACC. |
| 9 | rag-online | 08 / FUNCTIONS / RAG ONLINE | Retrieve pages, then let the model read. |
| 10 | rag-demo | 09 / DEMO / RAG | Every paragraph names its source. |
| 11 | knowledge | 10 / FUNCTIONS / KNOWLEDGE | A conversation that lives beside the file. |
| 12 | knowledge-demo | 11 / DEMO / KNOWLEDGE | From a marker to the exact page. |
| 13 | verifier | 12 / VERIFIER | A source is not a citation until the span passes. |
| 14 | practice-policy | 13 / FUNCTIONS / PRACTICE & POLICY | Practice and integrity. |
| 15 | practice-demo | 14 / DEMO / PRACTICE & POLICY | Practice, then check. |
| 16 | evaluation | 15 / EVALUATION | We win on coverage. We tie on grading. |
| 17 | failure-limits | 16 / FAILURE & LIMITS | Tutorials are the hard slice. |
| 18 | conclusion | 17 / CONCLUSION | Verifiability is a system property. |
| 19 | appendix-a1 | APPENDIX / A1 | One question, end to end. |
| 20 | appendix-a2 | APPENDIX / A2 | Evaluation method and TACC evidence. |
