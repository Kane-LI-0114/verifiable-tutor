# Three final deck editions

This branch adds three presentation editions of the same 20-page Verifiable Tutor story. The `ppt-master` edition is built in another conversation and is not part of this branch.

| Edition | Directory | Output | Build |
|---|---|---|---|
| Native v2 | `v2-pptx/` | `CSIT6000V_VerifiableTutor_v2.pptx` and `.pdf` | `node build_v2.js` then `soffice --headless --convert-to pdf` |
| Stage HTML | `stage-html/` | `index.html`, slide PNGs, PDF | open `index.html`; export with Chrome headless |
| Custom HTML | `custom-html/` | `index.html`, slide PNGs, PDF | open `index.html`; export with Chrome headless |

All three use `shared/theme.json` and `shared/brief.md`, and the assets under `shared/assets/` plus the original `presentation/assets/screenshots/`.

## Hard rules

- 20 slides: 18 main plus 2 appendix.
- Palette: paper `#FAFAFA`, ink `#09090B`, cobalt `#1447E6`, line `#E5E5E5`, graphite `#0A0A0A` and `#171717`, failure `#C10007`.
- Fonts: Georgia display, Arial body, Courier New mono. No Source Serif 4, Helvetica Neue, or Menlo in PPTX or PDF.
- Every slide has exactly two type sizes. PPTX: Display 40pt (cover 64pt) and Body 16pt. Custom HTML: 80px (cover 112px) and 32px. Stage HTML: 96px (cover 120px) and 32px.
- Body copy at most 45 words per slide.
- Every content slide has an image, a diagram, a chart, or an icon cluster.
- English only. Instructor and TA only on slides 17 and 18. Verifier implementation is Yoga's.

## QA

`qa/` holds the independent audit. `qa-report.md` records page counts, font sizes, font names, image coverage, blank bands, content parity, and PDF checks. A deck is not done until it passes the report and the contact sheet is inspected at full size and 50 percent.

## Branch and commit

Branch: `presentation/three-editions`, based on `presentation/final-deck@9a5da3a`.

The root agent commits the three editions together after QA. Do not commit from a builder directory.

## Do not touch

`presentation/ppt-master/` and `presentation/ppt-master-sources/` belong to another conversation. They are untracked here and are not part of this branch.
