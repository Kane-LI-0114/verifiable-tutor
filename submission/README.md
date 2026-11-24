# Repository submission PDF

This folder renders [`CSIT6000V_Project_Repository_Submission_LI_TIAN_XIE.pdf`](../CSIT6000V_Project_Repository_Submission_LI_TIAN_XIE.pdf), the one PDF per group the course asks for. It holds the repository link, the group contributions, and the full README.

The PDF is generated, not edited: the body is the repository [README.md](../README.md), and the cover is [`cover.html`](cover.html). Change those two files, rerun the renderer, and commit the new PDF.

## What the PDF contains

| Part | Source |
|---|---|
| 1. Repository link | `cover.html` |
| 2. Group contributions | `cover.html` |
| 3. Full README | `../README.md`, rendered with GitHub-flavored Markdown |

Relative links in the README are rewritten to `github.com/Kane-LI-0114/verifiable-tutor/blob/main/`, so they stay clickable in the PDF, and local figures are inlined.

## Prerequisites

- Node 18 or later.
- Google Chrome, or any Chromium build. The renderer looks for Chrome in the usual macOS and Linux locations; set `CHROME=/path/to/chrome` to point at another binary.

## Render

```bash
npm --prefix submission install    # once, installs marked
node submission/build.mjs          # rewrites the PDF at the repository root
```

Run both commands from the repository root. The renderer prints the HTML and PDF it wrote; the PDF must stay at the repository root, because that is the file the course collects.

## Checks before committing

- `pdfinfo CSIT6000V_Project_Repository_Submission_LI_TIAN_XIE.pdf | grep Pages` reports 16 pages.
- The repository link on page 1 is clickable and opens the public repository.
- Page 2 starts the README, and the Getting Started Instructions section follows the cover.

## Editing

- **Names, date, contributions**: edit [`cover.html`](cover.html) directly. It is plain HTML with the print styles at the top.
- **Body**: edit [`README.md`](../README.md). Do not edit the HTML inside `.build/`; it is regenerated on every run and ignored by Git.
- **Output path**: `OUT=/tmp/check.pdf node submission/build.mjs` writes a preview without touching the deliverable.

`.build/` and `node_modules/` are ignored; `package-lock.json` is committed so the Markdown renderer resolves to the same version for everyone.
