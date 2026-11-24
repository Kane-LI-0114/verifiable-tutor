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
import { spawn } from "node:child_process";
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

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForPageTarget(port) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try {
      const response = await fetch("http://127.0.0.1:" + port + "/json/list");
      const targets = await response.json();
      const page = targets.find(
        (target) => target.type === "page" && target.url.startsWith("file://"),
      );
      if (page && page.webSocketDebuggerUrl) return page;
    } catch {
      // Chrome is still starting.
    }
    await sleep(150);
  }
  throw new Error("Chrome did not expose a page target on port " + port);
}

async function printPdf(chrome, htmlPath, pdfPath) {
  const port = 9400 + Math.floor(Math.random() * 200);
  const profile = fs.mkdtempSync(path.join(BUILD_DIR, "chrome-"));
  const child = spawn(
    chrome,
    [
      "--headless",
      "--disable-gpu",
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      "--remote-debugging-port=" + port,
      "--user-data-dir=" + profile,
      "file://" + htmlPath,
    ],
    { stdio: "ignore" },
  );
  try {
    const target = await waitForPageTarget(port);
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.onopen = resolve;
      socket.onerror = reject;
    });

    const pending = new Map();
    let nextId = 1;
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      const waiter = message.id ? pending.get(message.id) : undefined;
      if (!waiter) return;
      pending.delete(message.id);
      if (message.error) waiter.reject(new Error(message.error.message));
      else waiter.resolve(message.result);
    };
    const send = (method, params = {}) =>
      new Promise((resolve, reject) => {
        const id = nextId++;
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
      });

    await send("Page.enable");
    await sleep(1200); // let fonts and the print styles settle
    const { data } = await send("Page.printToPDF", {
      displayHeaderFooter: true,
      headerTemplate: "<div></div>",
      footerTemplate:
        '<div style="width:100%; font-size:8pt; color:#5a6472; font-family:Helvetica,Arial,sans-serif; text-align:center;">' +
        'Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
      printBackground: true,
      paperWidth: 8.27,
      paperHeight: 11.69,
      marginTop: 0.67,
      marginBottom: 0.71,
      marginLeft: 0.63,
      marginRight: 0.63,
    });
    fs.writeFileSync(pdfPath, Buffer.from(data, "base64"));
    socket.close();
  } finally {
    child.kill("SIGKILL");
  }
}

const chrome = findChrome();
await printPdf(chrome, OUT_HTML, OUT_PDF);
console.log("wrote", path.relative(REPO, OUT_PDF), (fs.statSync(OUT_PDF).size / 1024).toFixed(0) + " KB");
