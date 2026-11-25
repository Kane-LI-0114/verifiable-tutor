# Custom HTML edition

The third presentation edition for CSIT6000V Fall 2026, built with the installed
`html-ppt` skill. 20 slides: 18 main plus 2 appendix, 1920 x 1080, English only,
offline at runtime. This directory is self-contained and was built on branch
`presentation/three-editions`.

## Open it

Open `index.html` in Chrome. It must be opened from this folder so the relative
asset paths resolve; a local static server works too.

| Key | Action |
|---|---|
| `←` `→` / Space / PageUp / PageDown / Home / End | navigate |
| `O` | slide overview grid (20 thumbnails) |
| `N` | speaker-notes drawer (timing and script for the current slide) |
| `S` | presenter window (current/next preview, script, timer) |
| `F` | fullscreen |
| `#/N` in the URL | deep link to slide N |

The keyboard runtime, overview, speaker notes and presenter mode come from the
vendored `assets/vendor/runtime.js` (copied unchanged from the html-ppt skill).

## Typography and theme

- Palette is exactly the shared theme: paper `#FAFAFA`, ink `#09090B`, cobalt
  `#1447E6`, line `#E5E5E5`, graphite `#0A0A0A`/`#171717`, failure `#C10007`.
- Georgia display, Arial body, Courier New mono. No external fonts, no CDN, no
  network requests.
- Exactly two text sizes per slide: 32px body and 80px display, except the cover
  at 112px. Every label, kicker, caption, table cell and page number is 32px.
- The html-ppt base typography is overridden in `assets/vt.css`; no third size
  exists anywhere in the deck.

## Layout

| File | Role |
|---|---|
| `index.html` | the complete deck, 20 `<section class="slide">` blocks |
| `assets/vt.css` | custom vt theme, type enforcement, per-slide layout |
| `assets/vendor/base.css` | copied unchanged from the html-ppt skill |
| `assets/vendor/runtime.js` | copied unchanged from the html-ppt skill |
| `assets/shots/` | read-only copies of the shared UI screenshots |
| `assets/course/` | read-only copies of the shared course page thumbnails |
| `assets/icons/`, `assets/icons-white/` | read-only copies of the shared Lucide icons |
| `assets/img/qr-repo.png` | read-only copy of the shared repository QR |
| `assets/backgrounds/` | read-only copies of the shared paper/title textures |
| `scripts/cdp.mjs` | minimal Chrome DevTools Protocol client (no npm dependencies) |
| `scripts/check_type.mjs` | computed-font-size and body-word audit |
| `scripts/check_runtime.mjs` | keyboard navigation, overview and notes check |
| `scripts/render.mjs` | export all 20 slides to 1920x1080 PNG |
| `scripts/build_pdf.py` | combine the PNGs into the 20-page 16:9 PDF |
| `scripts/build_all.sh` | run all checks, the export and the PDF build |
| `exports/slides/` | `slide-01.png` to `slide-20.png` at 1920x1080 |
| `exports/CSIT6000V_VerifiableTutor_CustomHTML_2026F.pdf` | final 20-page PDF |
| `exports/contact-sheet.png` | 4x5 overview of all 20 slides |
| `exports/type-audit.json` | machine-readable computed-size audit |

## Build and validate

```bash
cd presentation/editions/custom-html
node scripts/check_type.mjs          # exits non-zero on any size/word violation
node scripts/check_runtime.mjs       # exits non-zero if keyboard/notes/overview break
node scripts/render.mjs              # writes 20 PNGs to exports/slides
python3 scripts/build_pdf.py         # writes the PDF, asserts exactly 20 pages
bash scripts/build_all.sh            # all of the above in order
```

The audit drives headless Chrome through CDP, collects the computed
`font-size` of every visible text element under each slide, and fails unless the
set of sizes on a slide is exactly `{32, 80}` (or `{32, 112}` on the cover).
It also checks the slide count, notes, image presence, external network
requests, the Georgia/Arial/Courier New stacks, and a 45-word cap on body copy.
Hidden speaker notes are not counted. The runtime check opens the overview and
the notes drawer, then verifies arrow navigation and the hash deep link.

## Content notes

The deck follows the shared brief page map and the speaker notes in
`presentation/deck/content.js`. `source` means a retrieved course page;
`citation` is reserved for a page plus a span that passed the verifier, and the
deck says the `citations` table is still empty. Instructor/TA appears only on
slides 17 and 18. The verifier is presented as Yoga's work on slide 13.

## Compromises and limitations

- The PDF is produced from the 20 PNG slides (Pillow, 144 dpi, 13.333 x 7.5 in),
  not from a vector print path. It is pixel-faithful to the screenshots but text
  is raster.
- `policy-refusal.png` is a wide crop whose source image is clipped at the left
  edge; slide 15 shows it as a framed excerpt, so the first characters of the
  answer line are intentionally not visible.
- In the S presenter window, the browser may block the popup; the runtime's own
  alert is the only presenter limitation.
- Icons are the shared Lucide SVG/PNG assets. Screenshots and course pages are
  copied from the shared read-only asset folder and were not modified.
