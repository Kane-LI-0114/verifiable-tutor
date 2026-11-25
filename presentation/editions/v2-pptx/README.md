# v2 PPTX edition, Verifiable Tutor final deck

Editable 20-slide 16:9 deck for CSIT6000V Fall 2026, built from the shared brief
(`presentation/editions/shared/brief.md`) and the shared palette and type rules
(`presentation/editions/shared/theme.json`). Story, claims, and speaker timing follow
`presentation/deck/content.js`; the deck is a condensed, larger-type edition of the shipped
`presentation/CSIT6000V_VerifiableTutor_Final_2026F.pptx`.

## Outputs

| File | What it is |
|---|---|
| `CSIT6000V_VerifiableTutor_v2.pptx` | 20 slides, 16:9 (12192000 x 6858000 EMU), native editable text and shapes, speaker notes |
| `CSIT6000V_VerifiableTutor_v2.pdf` | LibreOffice PDF export, 20 pages, 960 x 540 pt |
| `contact-sheet.png` | 4 x 5 QA contact sheet rendered from the PDF at 110 dpi |
| `pages/` | per-slide PDF renders used for the contact sheet and QA |
| `audit-report.txt` | font, size, palette, word-count, and bottom-fill audit output |
| `build_v2.js` | pptxgenjs CommonJS build (helpers reused in spirit from `presentation/deck/build_deck.js`) |
| `audit_v2.py` | PPTX/PDF size, font, palette, copy, and page-fill audit |
| `render_contact.py` | pdftoppm page render plus 4 x 5 contact sheet |

## Rebuild

```bash
cd presentation/editions/v2-pptx
node build_v2.js
soffice --headless --convert-to pdf --outdir . CSIT6000V_VerifiableTutor_v2.pptx
rm -rf pages && python3 render_contact.py
python3 audit_v2.py
pdffonts CSIT6000V_VerifiableTutor_v2.pdf
```

## Typography and palette

- Exactly two font sizes on every slide. Cover: Display 64pt and Body 16pt. Every other
  slide: Display 40pt and Body 16pt. Kickers, labels, captions, table cells, chart values,
  icons labels, page numbers, and the footer are all 16pt. Titles and big numbers are 40pt
  (64pt on the cover). No 14pt fallback, no 28pt or other intermediate sizes anywhere.
- Fonts: Georgia (display), Arial (body), Courier New (mono). The theme font scheme is
  rewritten after generation so the PPTX declares only these three faces; the PDF embeds
  only Arial (ArialMT and Arial-BoldMT), Georgia, and CourierNewPSMT.
- Palette only: paper #FAFAFA, white #FFFFFF, ink #09090B, graphite #0A0A0A / #171717,
  cobalt #1447E6, line #E5E5E5, failure #C10007. No extra tints, no gray ramp.
- Body copy: 45 words or fewer of prose per slide (audit counts alphabetic 16pt tokens and
  excludes the page footer and numeric table cells); the longest slide is 45.

## Visuals

- Real screenshots under `presentation/assets/screenshots/` and shared copies under
  `presentation/editions/shared/assets/screenshots/`: agent work chain, answer and source
  pane, page chat, practice question, policy refusal.
- Shared course page thumbnails `acs2-p09`, `acs2-p10`, `tutorial4-p40` are 4:3;
  they are placed at 4:3 inside white frames, never stretched.
- Shared Lucide icons (`presentation/editions/shared/assets/icons/`, ink and white PNG
  variants) supply three to five icons on the content pages. They are monochrome by design:
  the shared set has no cobalt variant, so emphasis is carried by cobalt text, fills, and
  rules instead of tinted icons.
- Shared repository QR `presentation/editions/shared/assets/qr/repo.png` sits on the
  conclusion slide with its white quiet zone intact.
- Textures `presentation/assets/backgrounds/` are the only full-bleed images; all copy
  and all layout geometry are native text boxes and shapes, not slide screenshots.

## Page map

1. Cover, 2. Problem and goal, 3. System, 4. Data model, 5. Stack, 6. Agent loop,
7. Agent demo, 8. RAG offline, 9. RAG online, 10. RAG demo, 11. Knowledge chat,
12. Knowledge demo, 13. Verifier, 14. Practice and policy, 15. Practice demo,
16. Evaluation, 17. Failure and limits, 18. Conclusion, A1. One question end to end,
A2. Evaluation method and TACC evidence.

Instructor and TA are mentioned only on slide 18 (next surface), as the brief requires.
The verifier is introduced as Yoga's implementation on slide 13.

## Frozen facts kept in the deck

17 application tables plus FTS5; 16 documents, 593 pages, 612 chunks and vectors, 16
summaries; hybrid nDCG@5 0.849, hit@5 0.882, 937 tokens@5; practice study 10/10 grounded,
0/10 off-topic, 5/5 coverage, grading tie 10/10; citation study 0 invented quotes; tutorial
slice nDCG@5 0.617; dual granularity hit@5 0.882 to 0.941 at 2.7 times index cost; TACC
Qwen job 28067 with 434 s cold start, 43.9 s build, 8/8 valid records. Speaker notes are
the English 9:35 script from `presentation/deck/content.js`.

## Compromises and notes

- The shared icon set is ink/white only, so icons are not cobalt; this is a deliberate
  palette-safe choice rather than a missing asset.
- Course thumbnails are 4:3 lecture pages inside 16:9 frames, so they letterbox inside white
  cards; they are not cropped and not stretched.
- Demo screenshots are placed as large as captions and the footer allow (for example the
  work-chain capture is 6.0 in wide, the answer detail 6.6 in, the source pane 4.75 in), so
  the smallest in-screenshot UI labels are legible on a projector rather than on a phone.
- The build reads shared assets read-only from their shared paths and does not copy or modify
  them; rerunning the build needs this repository's shared asset tree.
- `zip`-based re-packaging after theme sanitization is done in the build; PowerPoint and
  LibreOffice both open the result (`unzip -t` clean, PDF conversion clean).
