# B edition: ppt-master native deck

The B edition is the native, editable version built through the `ppt-master` workflow. It keeps the approved 18 main slides plus 2 appendix slides, the English content, the paper and cobalt visual system, and the 10-minute delivery target.

- **Deck:** `../CSIT6000V_VerifiableTutor_B_2026F.pptx`
- **PDF:** `../CSIT6000V_VerifiableTutor_B_2026F.pdf`
- **Source project:** `verifiable-tutor-ppt-master_ppt169_20261125/`
- **Build chain:** Design Spec and lock -> hand-authored SVG pages -> final quality gate -> speaker notes -> native DrawingML PPTX -> PDF.
- **Canvas:** 16:9, 1280 x 720.
- **Type:** Georgia for titles, Arial for body, Courier New for paths. Body 16pt, page title 40pt, cover 64pt. No page uses more than two sizes.
- **Palette:** `#FAFAFA`, `#09090B`, `#1447E6`, `#F4F4F5`, `#52525B`, `#18181B`; failure `#C10007` only.
- **Images:** real UI screenshots and course PDF pages, with no cropping of evidence. No stock photography.
- **Icons:** 28 prepared `tabler-outline` icons, 2px stroke.
- **Notes:** English, 20 pages, about 1,240 words, estimated at 9:30 including demo pauses.

## Reproduce

The working directory for every command is the repository root.

    python3 ~/.agents/skills/ppt-master/scripts/project_manager.py validate presentation/ppt-master/verifiable-tutor-ppt-master_ppt169_20261125
    python3 ~/.agents/skills/ppt-master/scripts/svg_quality_checker.py presentation/ppt-master/verifiable-tutor-ppt-master_ppt169_20261125 --canonical-authoring --stage final --json
    python3 ~/.agents/skills/ppt-master/scripts/total_md_split.py presentation/ppt-master/verifiable-tutor-ppt-master_ppt169_20261125
    python3 ~/.agents/skills/ppt-master/scripts/finalize_svg.py presentation/ppt-master/verifiable-tutor-ppt-master_ppt169_20261125
    python3 ~/.agents/skills/ppt-master/scripts/svg_to_pptx.py presentation/ppt-master/verifiable-tutor-ppt-master_ppt169_20261125
    soffice --headless --convert-to pdf --outdir presentation presentation/CSIT6000V_VerifiableTutor_B_2026F.pptx

The export is timestamped under the project's `exports/` directory. The files at the top of `presentation/` are the copies to submit.

## Quality checks

- Final SVG quality gate: 20 pages, 0 blocking errors, 37 advisory warnings from explicit repeated styling and split text frames.
- PDF: 20 pages, 16:9, 960 x 540 pt.
- Embedded fonts: Georgia, Arial, Arial Bold, Courier New, Courier New Bold. No Source Serif 4, Helvetica Neue, or Menlo.
- PPTX: 20 slides, 20 notes pages, 15 placed pictures, native editable text and shapes.
- No CJK in slides, notes, or PDF text.
- Instructor/TA appears only on slides 17 and 18.
- The confirmed Stage-2 role sizes were normalized to the explicit two-size rule: 40pt title and 16pt body, with 64pt only on the cover. The 12pt annotation default was rejected because it violated the 14pt floor.

## Scope

The B edition is presentation work only. It does not modify app code, API, schema, config, or tests, and it does not touch `peter-dev`.
