// Render the course repository submission PDF.
//
// The body is README.md, rendered with the same GFM rules GitHub applies, so
// the PDF cannot drift from the README. The cover lives in cover.html. Both are
// plain text: edit them, rerun this script, commit the new PDF.
//
// Usage, from the repository root:
//   npm --prefix submission install        # once, installs marked
//   node submission/build.mjs              # writes the PDF next to this file
//
// Environment:
//   CHROME=/path/to/chrome   override the browser used for printing
//   OUT=/path/to/file.pdf    override the output path

import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { marked } from "marked";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");
const GH_BASE = "https://github.com/Kane-LI-0114/verifiable-tutor/blob/main/";
const PDF_NAME = "CSIT6000V_Project_Repository_Submission_LI_TIAN_XIE.pdf";
const OUT_PDF = process.env.OUT ?? path.join(REPO, PDF_NAME);
const BUILD_DIR = path.join(HERE, ".build");
const OUT_HTML = path.join(BUILD_DIR, "submission.html");

const MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

function findChrome() {
  const candidates = [
    process.env.CHROME,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error(
    "No Chrome found. Install Chrome, or set CHROME=/path/to/chrome, or open " +
      OUT_HTML +
      " in a browser and print it to PDF by hand.",
  );
}

function renderReadme() {
  const source = fs.readFileSync(path.join(REPO, "README.md"), "utf8");
  let body = marked.parse(source, { gfm: true, mangle: false, headerIds: false });

  // A relative link must still open the right place when the reader is holding
  // the PDF, so point it at the public repository.
  body = body.replace(/href="([^"]+)"/g, (match, href) => {
    if (/^(https?:|mailto:|#)/.test(href)) return match;
    return 'href="' + GH_BASE + href.replace(/^\.\//, "") + '"';
  });

  // Inline the figures so the PDF carries what the README shows.
  body = body.replace(
    /<img([^>]*?)src="([^"]+)"([^>]*?)>/g,
    (match, pre, src, post) => {
      const file = path.join(REPO, src);
      const mime = MIME[path.extname(file).toLowerCase()];
      if (!mime || !fs.existsSync(file)) return match;
      const data = fs.readFileSync(file).toString("base64");
      return '<img' + pre + 'src="data:' + mime + ";base64," + data + '"' + post + ">";
    },
  );

  return body;
}

fs.mkdirSync(BUILD_DIR, { recursive: true });
const cover = fs.readFileSync(path.join(HERE, "cover.html"), "utf8");
const html = cover.replace("{{README}}", renderReadme());
fs.writeFileSync(OUT_HTML, html);
console.log("wrote", path.relative(REPO, OUT_HTML), (html.length / 1024).toFixed(0) + " KB");

const chrome = findChrome();
const profile = fs.mkdtempSync(path.join(BUILD_DIR, "chrome-"));
execFileSync(
  chrome,
  [
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--virtual-time-budget=8000",
    "--user-data-dir=" + profile,
    "--print-to-pdf=" + OUT_PDF,
    "file://" + OUT_HTML,
  ],
  { stdio: ["ignore", "ignore", "pipe"] },
);
console.log("wrote", path.relative(REPO, OUT_PDF), (fs.statSync(OUT_PDF).size / 1024).toFixed(0) + " KB");
