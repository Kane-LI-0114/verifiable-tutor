# Shared deck assets

Frozen asset pack for the three deck editions on branch `presentation/three-editions`
(v2 PPTX, stage HTML, custom HTML). The edition brief is `../brief.md` and the palette is
`../theme.json`.

## Frozen: builders must not modify these files

Everything under this directory is a read-only input for the deck builders:

- Do not modify, move, rename, overwrite, re-encode, or delete any file in this directory.
- Copy a file into your own edition directory if you need a crop, a recolor, or a different size.
- If an asset is missing, wrong, or unsuitable, report it to the lead instead of changing the
  shared copy.

## Inventory

| Path | Count | Notes |
|---|---|---|
| `course/` | 3 PNG | ACS lecture 2 pages 9 and 10, Tutorial 4 page 40; 1800x1350 px (4:3) |
| `icons/*.svg` | 16 | Lucide v1.66.0; 24x24 viewBox, stroke `currentColor`, transparent |
| `icons/*.png` | 16 | 256x256 RGBA, ink `#09090B`, transparent |
| `icons/white/*.png` | 16 | 256x256 RGBA, white `#FFFFFF`, transparent; for graphite cards |
| `qr/repo.png` | 1 | 1230x1230 QR code for the public repository |
| `screenshots/` | 11 | Seeded UI captures, copied from `presentation/assets/screenshots/` |
| `manifest.json` | 1 | Path, source, license, dimensions, English-only flag, and sha256 for all 63 assets |

## Course page thumbnails

Rendered from the tracked corpus PDFs, not captured from the app:

```bash
pdftoppm -png -r 180 -f 9  -l 9  -singlefile data/corpus/corpus-pdf/ACS_lecture_2_2026F.pdf presentation/editions/shared/assets/course/acs2-p09
pdftoppm -png -r 180 -f 10 -l 10 -singlefile data/corpus/corpus-pdf/ACS_lecture_2_2026F.pdf presentation/editions/shared/assets/course/acs2-p10
pdftoppm -png -r 180 -f 40 -l 40 -singlefile data/corpus/corpus-pdf/Tutorial_4.pdf presentation/editions/shared/assets/course/tutorial4-p40
```

The source PDFs are 720x540 pt (4:3), so `-r 180` produces 1800x1350 px. The brief suggested
`-r 110`, but because the pages are 10 in wide that setting gives only 1100 px; `-r 180` is what
lands at about 1800 px wide.

All three requested pages exist in the tracked corpus, so no substitute source was needed: ACS
lecture 2 has 69 pages and Tutorial 4 has exactly 40 pages, which makes page 40 its last page.
The three pages are English-only: their tracked OCR page records in `data/corpus/pages/` contain
zero CJK characters. Crop or letterbox them into a 16:9 slide; do not stretch.
`data/corpus/corpus-pdf/` is the canonical tracked corpus; the copies under `data/corpus/pdf/`
have identical checksums.

## Icons

The 16 names are: `search`, `file-text`, `shield-check`, `flask-conical`, `database`, `cpu`,
`git-branch`, `quote`, `check`, `x`, `layers`, `boxes`, `gauge`, `book-open`, `arrow-right`,
`terminal`.

They are rebuilt from the local `lucide-react` 1.66.0 package at
`src/verifiable_tutor/ui/web/node_modules/lucide-react/dist/esm/icons/<name>.mjs`, using the
canonical Lucide SVG attributes: `viewBox="0 0 24 24"`, `fill="none"`,
`stroke="currentColor"`, `stroke-width="2"`, round caps and joins. Lucide is ISC licensed, not
MIT; the package `LICENSE` is the authority. The brief's "Lucide (MIT)" wording is inaccurate,
so cite ISC wherever the license is recorded.

- SVG: transparent, scalable, and tintable through CSS or the `stroke` attribute.
- PNG ink: stroke `#09090B` for paper and white backgrounds.
- PNG white: stroke `#FFFFFF` for graphite and dark cards.
- Raster command: `rsvg-convert -w 256 -h 256 -f png -o <name>.png <name>.svg` after replacing
  `stroke="currentColor"` with the target color. All PNGs are 256x256 RGBA with a transparent
  background.

## QR code

`qr/repo.png` encodes `https://github.com/Kane-LI-0114/verifiable-tutor`. It was generated
locally with `python-qrcode` 8.2 (version 4, error correction M, 30 px modules, 4-module quiet
zone) and decoded back with the OpenCV 4.11 `QRCodeDetector`. Keep the white quiet zone and do
not recolor or crop it when placing it. `python-qrcode` is BSD-3-Clause; the generated image is
output rather than a licensed creative work.

## Screenshots (seeded)

The 11 files in `screenshots/` were seeded before this pack was built by copying
`presentation/assets/screenshots/*.png`. Their capture metadata (commit 2b2b3a8, viewport
1600x1000 at 2x, crop boxes) lives in `presentation/assets/screenshots/manifest.json`. Treat
them as read-only; the originals remain the canonical copy.

## Manifest

`manifest.json` (schema `vt-shared-assets/1`) lists every file in this directory with:

- `path`: repository-root relative path
- `source`: exact source and render method
- `license`: license or ownership note
- `dimensions`: pixel size, plus the viewBox for SVGs
- `english_only`: `true` for every asset
- `sha256`: integrity hash

After copying an asset, compare its hash with the manifest entry using `shasum -a 256`; a mismatch
means the copy or the original was altered.

## English only

All assets are English-only. The course pages were checked for CJK text, the icons and the QR code
contain no text, and the seeded screenshots use the English UI.

## Contact

Owned by `asset-librarian` for shared task `task-1`. Report missing or incorrect assets to the
lead; do not patch shared files yourself.
