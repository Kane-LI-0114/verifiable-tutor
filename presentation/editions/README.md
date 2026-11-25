# Three final deck editions

This branch adds three presentation editions of the same 20-page Verifiable Tutor story. The `ppt-master` B edition was built in another conversation and is committed separately at `d0a15c6`; it is not part of this QA scope.

All three are **PASS** in `qa/qa-report.md` after the final stage re-audit on 2026-11-25.

| Edition | Directory | Deliverables | Format |
|---|---|---|---|
| Native v2 | `v2-pptx/` | `CSIT6000V_VerifiableTutor_v2.pptx`, `.pdf`, `contact-sheet.png` | Editable native PPTX |
| Stage HTML | `stage-html/` | `index.html`, `exports/VerifiableTutor_stage.pdf`, `exports/png/slide-01..20.png` | Single-file stage deck, 1920x1080 |
| Custom HTML | `custom-html/` | `index.html`, `exports/CSIT6000V_VerifiableTutor_CustomHTML_2026F.pdf`, `exports/slides/slide-01..20.png` | HTML PPT Studio deck, 1920x1080 |

All three use `shared/theme.json` and `shared/brief.md`, and the assets under `shared/assets/` plus the original `presentation/assets/screenshots/`.

## Hard rules

- 20 slides: 18 main plus 2 appendix.
- Palette: paper `#FAFAFA`, ink `#09090B`, cobalt `#1447E6`, line `#E5E5E5`, graphite `#0A0A0A` and `#171717`, failure `#C10007`.
- Fonts: Georgia display, Arial body, Courier New mono. No Source Serif 4, Helvetica Neue, or Menlo in PPTX or PDF.
- Every slide has exactly two type sizes. PPTX: Display 40pt (cover 64pt) and Body 16pt. Custom HTML: 80px (cover 112px) and 32px. Stage HTML: 96px (cover 120px) and 32px.
- Body copy at most 45 words per slide.
- Every content slide has an image, a diagram, a chart, or an icon cluster.
- English only. Instructor and TA only on slides 17 and 18. Verifier implementation is Yoga's.
- 16:9 everywhere. Speaker notes are English.

## Open and build

Native v2:

    cd presentation/editions/v2-pptx
    node build_v2.js
    soffice --headless --convert-to pdf --outdir . CSIT6000V_VerifiableTutor_v2.pptx

Stage HTML:

    cd presentation/editions/stage-html
    node build.mjs
    node scripts/render.mjs --skip-pdf
    # PDF is assembled from the 20 PNGs; see README and scripts/render.mjs

Custom HTML:

    cd presentation/editions/custom-html
    bash scripts/build_all.sh

Open either HTML deck from a local HTTP server, not `file://`, so module imports and relative assets behave the same as in the checked build:

    cd presentation/editions/stage-html && python3 -m http.server 8081
    cd presentation/editions/custom-html && python3 -m http.server 8082

## QA

`qa/qa-report.md` is the independent audit. All three editions pass: 20 slides each, exactly two type sizes, allowed fonts, no CJK, roles confined to slides 17/18, verifier only on slide 13, content parity of the frozen numbers, and no open blockers.

- v2 PDF is vector and embeds only ArialMT, Arial-BoldMT, Georgia, CourierNewPSMT.
- Stage and custom PDFs are raster assemblies of 20 PNGs; font compliance is proven from computed DOM audits, not PDF embeds.
- Stage PDF is 1440x810 pt; custom PDF is 960x540 pt. Both are 16:9.
- The v2 PPTX is the editable artifact. The HTML decks are the presentation artifacts.

## Branch and commit

Branch: `presentation/three-editions`, based on `presentation/final-deck@9a5da3a`.

The root agent commits after QA. Builder directories do not commit.

## Do not touch

`presentation/ppt-master/` and the top-level `CSIT6000V_VerifiableTutor_B_2026F.*` files belong to the other conversation and its `d0a15c6` commit. Do not edit or QA them as part of this branch's three-edition work.
