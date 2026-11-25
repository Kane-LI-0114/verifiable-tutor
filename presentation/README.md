# Final presentation deck

The final CSIT6000V presentation for **Verifiable Tutor**, 18 main slides plus 2 appendix slides. Two editions are kept.

## A edition: pptxgenjs

- **Deck:** `CSIT6000V_VerifiableTutor_Final_2026F.pptx`
- **PDF:** `CSIT6000V_VerifiableTutor_Final_2026F.pdf`
- **Source branch:** `presentation/final-deck`, based on `main@2b2b3a8`

## B edition: ppt-master native deck

- **Deck:** `CSIT6000V_VerifiableTutor_B_2026F.pptx`
- **PDF:** `CSIT6000V_VerifiableTutor_B_2026F.pdf`
- **Source and build notes:** `ppt-master/README.md`
- **Difference:** hand-authored SVG pages compiled to native DrawingML, with Georgia / Arial / Courier New, 16pt body, 40pt page titles, real UI and course-page evidence.

Both editions use 16:9, static pages, English throughout, and the same 18+2 content. The PDF is the submitted artifact.

## Build

Prerequisites on this machine:

- Node with `pptxgenjs` available (the workspace already has it globally)
- Python 3 with Pillow and python-pptx
- LibreOffice, Poppler, and the `pptx` skill validator
- Source Serif 4 installed for PDF rendering (see below)

    cd project/verifiable-tutor
    node presentation/deck/build_deck.js
    python3 ~/.agents/skills/pptx/scripts/office/validate.py presentation/CSIT6000V_VerifiableTutor_Final_2026F.pptx
    soffice --headless --convert-to pdf --outdir presentation presentation/CSIT6000V_VerifiableTutor_Final_2026F.pptx
    pdfinfo presentation/CSIT6000V_VerifiableTutor_Final_2026F.pdf | grep Pages

The build is offline. It reads only files under `presentation/assets` and writes the PPTX, then strips ZIP folder entries with `zip -d`.

## Fonts

Install the OFL Source Serif 4 variable font once:

    bash presentation/scripts/install_font.sh

Then verify:

    fc-match "Source Serif 4"

The PDF embeds Source Serif 4, Helvetica Neue, and Menlo. If Source Serif 4 is unavailable, the fallback is Iowan Old Style; this changes the display face, not the content. The PPTX keeps the font name so a machine with the font installed renders it correctly.

## Screenshots

The deck uses English-only screenshots captured from the running app at `main@2b2b3a8`:

- `agent-workchain.png`: expanded `verify_span` call in a real turn.
- `rag-answer-detail.png`: answer body with inline markers.
- `rag-source-detail.png`: per-answer source pane.
- `kb-chat-before.png`: page-chat answer with page markers.
- `kb-page9-detail.png` / `kb-page10-detail.png`: PDF page before and after a citation click.
- `practice-question.png`: generated single-choice question.
- `policy-refusal.png`: Assignment 3 refusal before the deadline.

The processed assets and `manifest.json` are committed. Raw captures are written to `/tmp/vt-deck-capture` and are not committed. The capture runbook is `scripts/capture.sh`; it assumes the app is running at `http://127.0.0.1:8000` and the demo account is available. Screenshots are point-in-time: re-capture after a UI change and rebuild the deck.

The English capture flow is important:

1. The UI language toggle shows `中文` when English is active. If it shows `English`, switch it.
2. Ask the chat question with `Answer in English only.`
3. Do not reuse a conversation whose answer is not English.
4. Visually inspect each crop before committing it.

## Backgrounds

`scripts/render_backgrounds.py` writes `paper.jpg`, `graphite.jpg`, and `title.jpg`. The title texture is a blurred crop of `rag-source-pane.png`; the source is committed, so the background build does not depend on raw captures.

## Slide map

| # | Slide | Source |
|---|---|---|
| 1 | Title | Team and course |
| 2 | Problem & Goal | `docs/prd.md`, `proposal/proposal_v3.md`, course brief |
| 3 | Architecture | `docs/prd.md` Figure 1, `docs/figures/prd-containers.dot` |
| 4 | Database | `docs/physical-data-model.md`, `docs/figures/prd-er.dot` |
| 5 | Tech Stack | `package.json`, `pyproject.toml`, `docs/tech-selection.md` |
| 6 | Agent feature | `src/verifiable_tutor/orchestrator/`, ADR-0016 |
| 7 | Agent demo | Live app, English turn, `verify_span` |
| 8 | RAG offline | `scripts/ingest_corpus.py`, `tacc/ocr`, `tacc/index`, `docs/tech-selection.md` |
| 9 | RAG online | `src/verifiable_tutor/evidence/`, `experiments/chunking/RESULTS.md` |
| 10 | RAG demo | Live app, source pane |
| 11 | Knowledge chat | `src/verifiable_tutor/ui/web/src/routes/knowledge/document-page.tsx`, `components/knowledge/doc-chat-pane.tsx`, `api/chat.py` |
| 12 | Knowledge demo | Live app, page 9 to page 10 citation |
| 13 | Verifier | `src/verifiable_tutor/evidence/verify.py`; implementation owner Yoga |
| 14 | Practice & policy | `docs/prd.md` 5.3-5.4, `config/deadlines.yaml` |
| 15 | Practice & policy demo | Live app |
| 16 | Evaluation | `docs/evaluation-report.md`, `benchmarks/results/practice-eval-summary.md`, `benchmarks/results/new-question-summary.md` |
| 17 | Failure & limits | `experiments/chunking/RESULTS.md`; code inspection |
| 18 | Conclusion | Synthesis |
| A1 | One question, end to end | `docs/prd.md` sequence, `orchestrator/runner.py` |
| A2 | Evaluation method + TACC | `data/kb/builds/kb-20261102-01.json`, evaluation docs |

## Content rules

- Use **source** for a retrieved page. Use **citation** only for a page plus quoted span that passed the verifier.
- `citations` is currently empty; the deck says this explicitly.
- Instructor/TA appears only on slides 17 and 18. The main narrative is the student loop.
- Verifier implementation is Yoga's. Kane's agent demo shows the `verify_span` tool call, not the verifier algorithm.
- Ties are reported as ties; grading is a tie across all four systems.

## QA

    python3 presentation/scripts/audit_content.py
    pdftoppm -png -r 110 presentation/CSIT6000V_VerifiableTutor_Final_2026F.pdf /tmp/vt-deck-qa/page
    pdffonts presentation/CSIT6000V_VerifiableTutor_Final_2026F.pdf

Check:

- PDF has 20 pages: 18 main plus 2 appendix.
- No CJK in slide text or notes; no Chinese UI in screenshots.
- `Instructor/TA` only on slides 17 and 18.
- Body text is 10 pt or larger; dense diagram and table labels are 8-9 pt and are checked at full size.
- Full-size and 50% renders have no clipping or overflow.
- PPTX validation passes; PDF fonts are embedded.

## Scope

This directory adds the presentation only. It does not modify app code, API, schema, config, or tests. It does not merge `peter-dev`.
