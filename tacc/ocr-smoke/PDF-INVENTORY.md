# OCR smoke test PDF inventory

Measured on 2026-10-28 with PyMuPDF 1.26.3 (page text, embedded images, vector drawings) and pdfplumber 0.11.9 (`find_tables`). PDF paths here are relative to the course workspace root, `/Users/lijinchuan/Documents/HKUST/CSIT6000V`, not to this repository. The 12 PDFs total **342 pages**, about 58 MB. Every file parses cleanly and none is encrypted or password protected.

## How to read the table

- Text-layer pages: pages whose stripped text layer has more than 20 characters.
- Images/page and drawings/page: median and maximum counts over the document's pages.
- Table hints: pages where `find_tables` returned at least one table, plus the maximum table count on one page. Footer navigation bars, diagrams, and title rules trigger most of them, so this column is a hint only; verified real tables are named in Notes.
- Formula hints: pages with at least 10 math-symbol characters or at least 5 `=` signs, plus the maximum math-symbol character count on one page.

## Inventory

| PDF | Pages | Text-layer pages (> 20 chars) | Images/page (median / max) | Drawings/page (median / max) | Table hints | Formula hints | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ACS_Lecture_0_2026F.pdf` | 11 | 11 | 1 / 7 | 3 / 51 | 1 page, max 1 | 1 page, max 21 | 16:9 deck; cover and section pages carry little text. |
| `ACS_Lecture_1_2026F.pdf` | 67 | 67 | 2 / 4 | 5 / 625 | 21 pages, max 19 | 7 pages, max 31 | 16:9; most table hints are diagrams or code grids; p67 has 625 vector paths. |
| `ACS_lecture_2_2026F.pdf` | 69 | 69 | 2 / 4 | 8 / 96 | 68 pages, max 3 | 3 pages, max 17 | 720x540 pages; the footer navigation bar reads as a table on nearly every page. |
| `course_project.pdf` | 8 | 8 | 1 / 2 | 2.5 / 32 | 1 page, max 1 | 0 pages | 16:9; p7 is a diagram-only workflow page. |
| `hw1/Assignment_1_final.pdf` | 6 | 6 | 0 / 0 | 27.5 / 72 | 1 page, max 1 | 3 pages, max 21 | US Letter portrait; p3 has a genuine bordered file table; no embedded images. |
| `hw2/Assignment_2.pdf` | 5 | 5 | 0 / 0 | 3 / 3 | 0 pages | 4 pages, max 22 | US Letter portrait; p3 has a genuine table that `find_tables` misses (horizontal rules only); no embedded images. |
| `tutorial/TACC_Toturial.pdf` | 34 | 34 | 10 / 10 | 5 / 8 | 34 pages, max 1 | 2 pages, max 14 | Ten icon images on every page; only PDF with CJK text (p27, p28); no real tables. |
| `tutorial/Tutorial_1.pdf` | 16 | 0 | 1 / 1 | 1 / 1 | 0 pages | 0 pages | Image-only scan: one full-page raster per page, 2304x1728 px on a 720x540 page (about 230 DPI). |
| `tutorial/Tutorial_2.pdf` | 25 | 0 | 1 / 1 | 1 / 1 | 0 pages | 0 pages | Image-only scan: 4:3 pages of 960x720, raster 1920x1440 px (about 144 DPI). |
| `tutorial/Tutorial_3.pdf` | 28 | 28 | 2.5 / 6 | 3 / 17 | 2 pages, max 2 | 4 pages, max 33 | CUDA recipe deck; p22 and p25 are the formula pages. |
| `tutorial/Tutorial_4.pdf` | 40 | 40 | 2 / 10 | 7 / 20 | 39 pages, max 5 | 23 pages, max 70 | Highest formula density in the corpus; footer navigation bar causes almost all table hints. |
| `tutorial/Tutorial_5.pdf` | 33 | 33 | 2 / 26 | 7 / 44 | 32 pages, max 5 | 1 page, max 11 | Real data tables on p19 and p28; p3 has 26 icon images. |

## Image-only documents

Only `tutorial/Tutorial_1.pdf` (16 pages) and `tutorial/Tutorial_2.pdf` (25 pages) are image-only. Each page is a single full-page raster, and the text layer is empty on all 41 pages (0 extractable characters, confirmed with both PyMuPDF and pypdfium2).

## Transcripts

All 12 PDFs have a sibling transcript named `<name>.pdf_by_PaddleOCR-VL-1.6.md`. The transcripts carry no page markers, so they are a rough quality reference only; for the two image-only decks they were produced from the scanned page images.

## Selected pages

10 pages from 9 PDFs, covering the required minimum: 1 table, 2 formula, 2 two-column or side-by-side, 2 figure-only, 2 image-only, 1 dense-text.

| PDF | Page | Tags | Reason |
| --- | --- | --- | --- |
| `tutorial/Tutorial_5.pdf` | 19 | table | Five-column CXL performance table with shaded header, caption, and footnote. |
| `tutorial/Tutorial_4.pdf` | 33 | formula | Online softmax recurrence with 70 math characters and chained summation steps. |
| `tutorial/Tutorial_3.pdf` | 25 | formula | Attention(Q,K,V) and S=QK^T matrix expansions with nested summations. |
| `ACS_Lecture_1_2026F.pdf` | 59 | two-column | Barrier and condition variable panels side by side across a clean gutter. |
| `ACS_lecture_2_2026F.pdf` | 29 | two-column | Column-wise and blocked traversal comparisons side by side. |
| `tutorial/Tutorial_3.pdf` | 21 | figure-only | GPU and CPU code screenshots wired to memory boxes, 35 characters of text. |
| `course_project.pdf` | 7 | figure-only | STORM workflow diagram; the text layer holds only the title. |
| `tutorial/Tutorial_1.pdf` | 14 | image-only | Scanned slide with a C code block and three boxed guides; no text layer. |
| `tutorial/Tutorial_2.pdf` | 5 | image-only | Scanned slide with four bordered Rank/Value tables; no text layer. |
| `hw1/Assignment_1_final.pdf` | 4 | dense-text | Densest page in the corpus (1927 characters), portrait prose and command boxes. |

## Render command

Candidates and the 10 final pages were rendered with pypdfium2 (the renderer the GPU job uses) at 140 DPI and opened for visual inspection:

```python
python3 - <<'PY'
import pypdfium2 as pdfium
pdf = pdfium.PdfDocument("tutorial/Tutorial_5.pdf")
pdf[18].render(scale=140 / 72).to_pil().save("/tmp/vt-pages/selected/Tutorial_5_p19.png")
PY
```

The pypdfium2 index is 0-based, so page 19 is index 18. Verification renders are in `/tmp/vt-pages/selected/`. The GPU job can reuse the 1-based page numbers in `selected-pages.json` and render at 200 DPI.

## Unusual observations

- No PDF is encrypted, password protected, or damaged; all 12 parse cleanly.
- Page geometry varies. Lectures, `course_project.pdf`, and `TACC_Toturial.pdf` are 16:9 (960x540), most tutorials and `ACS_lecture_2_2026F.pdf` are 720x540, `Tutorial_2.pdf` is 4:3 (960x720), and the two homework PDFs are US Letter portrait (595x842). A fixed 16:9 canvas would pad or clip several selections.
- `Tutorial_2.pdf` rasters are about 144 DPI, so a 200 DPI render upsamples them (legible but soft). `Tutorial_1.pdf` rasters are about 230 DPI and upscale cleanly.
- `Tutorial_5.pdf` p3 carries 26 embedded images (icon grid), and `ACS_Lecture_1_2026F.pdf` p67 carries 625 vector paths. Both are layout stress cases.
- The only CJK text in the corpus is on `TACC_Toturial.pdf` p27 and p28 inside a CLI log. It did not make the 10-page set because the required coverage filled all 10 slots; it is the natural follow-up case for multilingual OCR.
- `find_tables` is unreliable on these decks because of footer bars and diagrams, and the genuine table on `hw2/Assignment_2.pdf` p3 is a false negative.
