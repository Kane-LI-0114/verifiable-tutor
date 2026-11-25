// Build CSIT6000V Verifiable Tutor final deck, v2 edition.
// pptxgenjs CommonJS, 16:9, editable native shapes and text.
// Typography: Georgia display, Arial body, Courier New mono.
// Exactly two sizes per slide: Display 40pt (cover 64pt) and Body 16pt.

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");
const { slides: sourceSlides } = require("../../deck/content");

const ROOT = path.resolve(__dirname, "..", "..");
const SCREENS = path.join(ROOT, "assets", "screenshots");
const BGS = path.join(ROOT, "assets", "backgrounds");
const SHARED = path.join(ROOT, "editions", "shared", "assets");
const ICONS = path.join(SHARED, "icons");
const COURSE = path.join(SHARED, "course");
const QR = path.join(SHARED, "qr", "repo.png");
const OUT_NAME = "CSIT6000V_VerifiableTutor_v2.pptx";
const OUT_PATH = path.join(__dirname, OUT_NAME);

const C = {
  paper: "FAFAFA",
  white: "FFFFFF",
  ink: "09090B",
  graphite: "0A0A0A",
  card: "171717",
  cobalt: "1447E6",
  line: "E5E5E5",
  failure: "C10007",
};

const F = { display: "Georgia", body: "Arial", mono: "Courier New" };
const SZ = { display: 40, cover: 64, body: 16 };
const P = { w: 13.333, h: 7.5, m: 0.6, contentW: 12.133, footerRuleY: 6.95, footerY: 7.0 };

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "LI Jinchuan, TIAN Yujia, XIE Yifeng";
pptx.company = "CSIT6000V";
pptx.subject = "Verifiable Tutor final presentation, v2 edition";
pptx.title = "Verifiable Tutor";
pptx.lang = "en-US";
pptx.theme = { headFontFace: F.display, bodyFontFace: F.body };

// ---------------------------------------------------------------- primitives

function txt(s, value, x, y, w, h, o = {}) {
  s.addText(String(value), {
    x, y, w, h,
    fontFace: o.face || F.body,
    fontSize: o.size || SZ.body,
    color: o.color || C.ink,
    bold: Boolean(o.bold),
    align: o.align || "left",
    valign: o.valign || "top",
    margin: 0,
    isTextBox: true,
    lineSpacingMultiple: o.ls == null ? 1.02 : o.ls,
    charSpacing: o.spacing == null ? 0 : o.spacing,
    wrap: true,
  });
}

function disp(s, value, x, y, w, h, o = {}) {
  txt(s, value, x, y, w, h, Object.assign({}, o, { face: F.display, size: o.size || SZ.display }));
}

function mono(s, value, x, y, w, h, o = {}) {
  txt(s, value, x, y, w, h, Object.assign({}, o, { face: F.mono }));
}

function box(s, x, y, w, h, o = {}) {
  s.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: o.radius == null ? 0.06 : o.radius,
    fill: { color: o.fill || C.white, transparency: o.transparency == null ? 0 : o.transparency },
    line: {
      color: o.line || C.line,
      width: o.lineWidth == null ? 1 : o.lineWidth,
      dashType: o.dash || "solid",
      transparency: o.lineTransparency == null ? 0 : o.lineTransparency,
    },
    shadow: o.shadow ? { type: "outer", color: C.graphite, blur: 10, angle: 45, distance: 2, opacity: 0.16 } : undefined,
  });
}

function rule(s, x, y, w, color = C.line, h = 0.012) {
  s.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color },
    line: { color, width: 0 },
  });
}

function line(s, x1, y1, x2, y2, color = C.ink, width = 1.6, o = {}) {
  s.addShape(pptx.ShapeType.line, {
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    w: Math.max(Math.abs(x2 - x1), 0.01),
    h: Math.max(Math.abs(y2 - y1), 0.01),
    flipH: x1 > x2,
    flipV: y1 > y2,
    line: {
      color,
      width,
      dashType: o.dash || "solid",
      transparency: o.transparency == null ? 0 : o.transparency,
    },
    shadow: undefined,
  });
}

function arrow(s, x1, y1, x2, y2, o = {}) {
  s.addShape(pptx.ShapeType.line, {
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    w: Math.max(Math.abs(x2 - x1), 0.01),
    h: Math.max(Math.abs(y2 - y1), 0.01),
    flipH: x1 > x2,
    flipV: y1 > y2,
    line: {
      color: o.color || C.ink,
      width: o.width == null ? 1.4 : o.width,
      dashType: o.dash || "solid",
      endArrowType: "triangle",
      transparency: o.transparency == null ? 0 : o.transparency,
    },
  });
}

function ellipse(s, cx, cy, rx, ry, o = {}) {
  s.addShape(pptx.ShapeType.ellipse, {
    x: cx - rx, y: cy - ry, w: rx * 2, h: ry * 2,
    fill: { color: o.fill || C.white, transparency: o.fill == null ? 100 : 0 },
    line: { color: o.color || C.ink, width: o.width == null ? 1.6 : o.width, transparency: o.transparency == null ? 0 : o.transparency },
  });
}

function boxOutline(s, x, y, w, h, o = {}) {
  s.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color: o.fill || C.white, transparency: o.fill == null ? 100 : 0 },
    line: { color: o.color || C.ink, width: o.width == null ? 1.6 : o.width, transparency: o.transparency == null ? 0 : o.transparency },
  });
}

function dot(s, cx, cy, r, color = C.ink) {
  s.addShape(pptx.ShapeType.ellipse, {
    x: cx - r, y: cy - r, w: r * 2, h: r * 2,
    fill: { color },
    line: { color, width: 0 },
  });
}

// ---------------------------------------------------------------- icon set
// Shared Lucide icons (read-only): ink PNGs on paper, white PNGs on graphite.

const ICON_FILES = {
  target: "gauge",
  book: "book-open",
  lock: "shield-check",
  monitor: "boxes",
  cloud: "cpu",
  server: "database",
  branch: "git-branch",
  code: "terminal",
  chat: "quote",
  file: "file-text",
  check: "check",
  search: "search",
  layers: "layers",
  cpu: "cpu",
  alert: "x",
  clock: "gauge",
  spark: "quote",
  chart: "gauge",
  globe: "cpu",
};

function icon(s, name, x, y, size, color) {
  const file = ICON_FILES[name] || name;
  const folder = color === C.white ? "white" : "";
  s.addImage({ path: path.join(ICONS, folder, file + ".png"), x, y, w: size, h: size, altText: file });
}

// ---------------------------------------------------------------- page chrome

function bg(s, name) {
  s.addImage({ path: path.join(BGS, name), x: 0, y: 0, w: P.w, h: P.h, altText: "" });
}

function kicker(s, value, dark) {
  txt(s, value.toUpperCase(), P.m, 0.34, 11.2, 0.28, {
    size: SZ.body, bold: true, color: dark ? C.line : C.cobalt, spacing: 1.3,
  });
}

function title(s, value, dark, o = {}) {
  txt(s, value, P.m, o.y == null ? 0.64 : o.y, o.w || 12.1, o.h || 1.15, {
    face: F.display, size: SZ.display, color: dark ? C.white : C.ink, ls: 0.9,
  });
}

function lead(s, value, dark, y) {
  txt(s, value, P.m, y == null ? 1.82 : y, 11.6, 0.3, { color: dark ? C.line : C.card });
}

function footer(s, page, dark) {
  rule(s, P.m, P.footerRuleY, P.contentW, C.line, 0.008);
  txt(s, "Verifiable Tutor  /  CSIT6000V", P.m, P.footerY, 6.0, 0.3, {
    color: dark ? C.line : C.card,
  });
  txt(s, page + " / 20", 11.0, P.footerY, 1.73, 0.3, { color: dark ? C.line : C.card, align: "right" });
}

// image in an optional white frame
function shot(s, file, x, y, w, ratio, o = {}) {
  const h = w * ratio;
  if (o.frame !== false) {
    box(s, x - 0.06, y - 0.06, w + 0.12, h + 0.12, {
      fill: C.white, line: C.line, radius: 0.04, shadow: Boolean(o.shadow),
    });
  }
  s.addImage({ path: path.join(SCREENS, file), x, y, w, h, altText: o.alt || "" });
  return h;
}

function courseImage(s, file, x, y, w, o = {}) {
  const h = w * 0.75;
  if (o.frame !== false) {
    box(s, x - 0.06, y - 0.06, w + 0.12, h + 0.12, {
      fill: C.white, line: C.line, radius: 0.04, shadow: Boolean(o.shadow),
    });
  }
  s.addImage({ path: path.join(COURSE, file), x, y, w, h, altText: o.alt || "Course page" });
  return h;
}

function chip(s, x, y, w, value, o = {}) {
  box(s, x, y, w, o.h || 0.36, {
    fill: o.fill || C.white,
    line: o.line || C.line,
    radius: 0.05,
    lineWidth: 1,
    dash: o.dash || "solid",
  });
  txt(s, value, x, y + 0.02, w, (o.h || 0.36) - 0.04, {
    face: o.mono ? F.mono : F.body,
    color: o.color || C.ink,
    bold: Boolean(o.bold),
    align: o.align || "center",
    valign: "mid",
    size: SZ.body,
  });
}

function iconTile(s, name, x, y, size, o = {}) {
  box(s, x, y, size, size, {
    fill: o.fill || C.white,
    line: o.line || C.line,
    radius: 0.05,
    lineWidth: 1,
    transparency: o.transparency,
    lineTransparency: o.lineTransparency,
  });
  icon(s, name, x + size * 0.22, y + size * 0.22, size * 0.56, o.color || C.ink, o.width);
}

function stat(s, value, label, x, y, w, o = {}) {
  disp(s, value, x, y, w, 0.66, { color: o.color || C.ink, size: o.size || SZ.display });
  txt(s, label, x, y + 0.78, w, 0.3, { color: o.labelColor || C.card });
}

// ---------------------------------------------------------------- slides

function slideCover() {
  const s = pptx.addSlide();
  bg(s, "title.jpg");
  kicker(s, "CSIT6000V / FINAL PRESENTATION / FALL 2026", true);

  txt(s, "Verifiable Tutor", P.m, 1.1, 8.0, 1.5, {
    face: F.display, size: SZ.cover, color: C.white, ls: 0.88,
  });
  txt(s, "A course-grounded agent with evidence you can check.", P.m, 2.85, 6.6, 0.75, {
    color: C.line, ls: 1.05,
  });
  rule(s, P.m, 3.95, 3.2, C.cobalt, 0.03);

  ["p.9", "p.10", "p.11"].forEach((v, i) => {
    chip(s, P.m + i * 0.92, 4.22, 0.8, v, { fill: C.cobalt, line: C.cobalt, color: C.white, bold: true });
  });
  txt(s, "Every answer names its page.", P.m + 2.95, 4.27, 4.6, 0.3, { color: C.line });

  txt(s, "LI Jinchuan  ·  TIAN Yujia  ·  XIE Yifeng", P.m, 5.45, 7.0, 0.3, { color: C.white });
  txt(s, "21188271  ·  21201619  ·  21322152", P.m, 5.85, 7.0, 0.3, { color: C.line });
  txt(s, "Advanced AI Computing and Systems  ·  Fall 2026", P.m, 6.55, 7.6, 0.3, { color: C.line });

  // evidence card
  const cx = 8.55, cy = 1.1, cw = 4.18, ch = 5.55;
  box(s, cx, cy, cw, ch, { fill: C.white, line: C.line, radius: 0.08, shadow: true });
  txt(s, "A REAL COURSE PAGE", cx + 0.26, cy + 0.24, 3.6, 0.3, { color: C.cobalt, bold: true, spacing: 1.2 });
  const imgW = 3.62;
  const imgH = imgW * 0.884;
  s.addImage({ path: path.join(SCREENS, "kb-page9-detail.png"), x: cx + 0.28, y: cy + 0.66, w: imgW, h: imgH, altText: "Lecture 2 page 9, Memory Wall" });
  txt(s, "Lecture 2  ·  Memory Wall  ·  p.9", cx + 0.26, cy + 4.05, 3.65, 0.3, { color: C.ink, bold: true });
  txt(s, "16 documents  ·  593 pages indexed", cx + 0.26, cy + 4.45, 3.65, 0.3, { color: C.card });

  txt(s, "01 / 20", 11.0, P.footerY, 1.73, 0.3, { color: C.line, align: "right" });
}

function slideProblem() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "01 / PROBLEM & GOAL");
  title(s, "A study loop students can trust.");
  lead(s, "A fluent answer is not a checkable answer.", false);

  const rows = [
    ["search", "Dense lectures", "Find the exact page."],
    ["book", "Assignment practice", "Stay inside the course."],
    ["lock", "Deadline help", "Policy decides what is allowed."],
  ];
  rows.forEach(([ic, head, body], i) => {
    const y = 2.35 + i * 1.25;
    iconTile(s, ic, P.m, y, 0.62, { color: C.cobalt });
    txt(s, head, P.m + 0.88, y + 0.02, 4.7, 0.32, { bold: true });
    txt(s, body, P.m + 0.88, y + 0.38, 4.9, 0.32, { color: C.card });
  });
  txt(s, "Before: trust the answer. After: check the page.", P.m, 6.25, 5.5, 0.3, { color: C.cobalt, bold: true });

  // course page visual
  const x = 6.55, w = 5.15;
  const h = courseImage(s, "acs2-p09.png", x, 1.95, w, { shadow: true, alt: "Lecture 2 page 9, Memory Wall" });
  txt(s, "Lecture 2  ·  Memory Wall  ·  p.9", x, 1.95 + h + 0.22, w, 0.3, { bold: true });
  txt(s, "16 documents, 593 pages indexed", x, 1.95 + h + 0.6, w, 0.3, { color: C.card });
  footer(s, "02");
}

function slideSystem() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "02 / SYSTEM");
  title(s, "One local product. One batch backend on TACC.", false, { h: 1.2 });
  lead(s, "The student loop is local. Heavy builds are TACC jobs.", false, 1.86);

  const zones = [
    ["monitor", "Local product", "React SPA  ·  FastAPI\nLangGraph  ·  SQLite", false],
    ["cloud", "External APIs", "DeepSeek  ·  MiMo", false],
    ["server", "TACC batch jobs", "OCR  ·  index  ·  Qwen KB\nNo inbound service", true],
  ];
  zones.forEach(([ic, head, body, dark], i) => {
    const x = P.m + i * 4.14, w = 3.9, y = 2.28, h = 2.3;
    box(s, x, y, w, h, {
      fill: dark ? C.card : C.white,
      line: dark ? C.card : C.line,
      radius: 0.07,
      lineTransparency: dark ? 100 : 0,
    });
    icon(s, ic, x + 0.26, y + 0.26, 0.54, dark ? C.white : C.cobalt);
    txt(s, head, x + 1.0, y + 0.3, w - 1.2, 0.34, { color: dark ? C.white : C.ink, bold: true });
    let ty = y + 0.92;
    body.split("\n").forEach((lineText) => {
      txt(s, lineText, x + 0.26, ty, w - 0.45, 0.3, { color: dark ? C.line : C.card });
      ty += 0.4;
    });
  });
  arrow(s, 4.55, 3.4, 4.7, 3.4, { color: C.ink, width: 1.2 });
  arrow(s, 8.7, 3.4, 8.85, 3.4, { color: C.ink, width: 1.2 });

  // one turn flow
  txt(s, "ONE TURN", P.m, 5.05, 3.0, 0.3, { color: C.cobalt, bold: true, spacing: 1.2 });
  const flow = [
    ["chat", "Ask"],
    ["branch", "Plan"],
    ["code", "Act"],
    ["check", "Verify"],
    ["file", "Cite"],
  ];
  flow.forEach(([ic, name], i) => {
    const w = 2.1;
    const x = P.m + i * 2.5;
    const last = name === "Cite";
    box(s, x, 5.45, w, 1.0, {
      fill: last ? C.cobalt : C.white,
      line: last ? C.cobalt : C.line,
      radius: 0.06,
    });
    icon(s, ic, x + 0.18, 5.6, 0.42, last ? C.white : C.ink);
    txt(s, name, x + 0.74, 5.62, w - 0.8, 0.34, { color: last ? C.white : C.ink, bold: true, valign: "mid" });
    if (i < 4) arrow(s, x + w + 0.04, 5.95, x + 2.44, 5.95, { color: C.ink, width: 1.2 });
  });
  txt(s, "Streamed to the SPA as frames.", P.m, 6.55, 7.0, 0.3, { color: C.card });
  footer(s, "03");
}

function slideData() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "03 / DATA");
  title(s, "The data model makes the evidence chain durable.", false, { h: 1.2 });

  disp(s, "17", P.m, 1.98, 1.1, 0.7, {});
  txt(s, "application tables + FTS5", P.m + 1.15, 2.12, 3.4, 0.34, { bold: true });

  const clusters = [
    ["database", "3", "access tables", "users · sessions"],
    ["chat", "5", "conversation", "messages · steps"],
    ["book", "6", "knowledge", "chunks · docs"],
    ["clock", "1", "learning", "topic_progress"],
  ];
  clusters.forEach(([ic, n, label, tables], i) => {
    const x = P.m + (i % 2) * 3.3;
    const y = 2.98 + Math.floor(i / 2) * 1.42;
    const w = 3.1, h = 1.27;
    box(s, x, y, w, h, { fill: C.white, line: C.line, radius: 0.06 });
    icon(s, ic, x + 0.18, y + 0.18, 0.36, C.cobalt, 1.3);
    disp(s, n, x + 0.66, y + 0.1, 0.8, 0.6, {});
    txt(s, label, x + 1.4, y + 0.2, w - 1.5, 0.3, { bold: true });
    mono(s, tables, x + 0.18, y + 0.82, w - 0.3, 0.3, { color: C.card });
  });

  box(s, P.m, 5.95, 6.3, 0.72, { fill: C.white, line: C.cobalt, radius: 0.05 });
  mono(s, "message_sources = answer → doc / page", P.m + 0.16, 6.09, 6.0, 0.3, { color: C.cobalt });
  mono(s, "citations = verified layer, next", P.m + 0.16, 6.43, 6.0, 0.3, { color: C.card });

  const sx = 7.25, sw = 5.55, sh = sw * 0.590;
  shot(s, "rag-source-pane.png", sx, 1.9, sw, 0.590, { shadow: true, alt: "Source pane with fourteen retrieved course pages" });
  txt(s, "14 retrieved pages in marker order", sx, 1.9 + sh + 0.24, sw, 0.3, { color: C.ink, bold: true });
  txt(s, "message_sources is the bridge from an answer to a page.", sx, 1.9 + sh + 0.62, sw, 0.6, { color: C.card });
  footer(s, "04");
}

function slideStack() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "04 / STACK");
  title(s, "A small stack with one job per layer.");
  lead(s, "Pinned versions; one origin; local-first stores.", false);

  const layers = [
    ["monitor", "Interface", "React 19  ·  Vite  ·  TypeScript  ·  Tailwind", "LOCAL"],
    ["server", "Backend", "FastAPI  ·  Pydantic  ·  SQLite FTS5", "LOCAL"],
    ["branch", "Agent", "LangGraph  ·  5 typed tools  ·  budgets", "LOCAL"],
    ["layers", "Retrieval", "BGE-M3  ·  BM25  ·  RRF k=60", "LOCAL"],
    ["cloud", "Platform", "DeepSeek  ·  MiMo  ·  Qwen vLLM", "TACC"],
  ];
  layers.forEach(([ic, name, parts, place], i) => {
    const y = 2.15 + i * 0.86;
    box(s, P.m, y, P.contentW, 0.74, { fill: C.white, line: C.line, radius: 0.05 });
    icon(s, ic, P.m + 0.18, y + 0.16, 0.42, i === 4 ? C.cobalt : C.ink, 1.4);
    txt(s, name, P.m + 0.8, y + 0.2, 1.9, 0.34, { bold: true });
    txt(s, parts, P.m + 2.55, y + 0.2, 7.3, 0.34, { color: C.card });
    txt(s, place, 11.15, y + 0.2, 1.35, 0.34, { color: i === 4 ? C.cobalt : C.card, align: "right", bold: i === 4 });
    if (i < 4) line(s, P.m + 1.19, y + 0.6, P.m + 1.19, y + 0.86, C.line, 1.2);
  });
  txt(s, "Versions in package.json, pyproject.toml, tech-selection.md.", P.m, 6.55, 9.0, 0.3, { color: C.card });
  footer(s, "05");
}

function slideAgent() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "05 / FUNCTIONS / AGENT");
  title(s, "A typed loop, not a prompt.");
  lead(s, "Perceive, plan, act, reflect.", false);

  const roles = [
    ["layers", "Perceive", "message and history"],
    ["branch", "Plan", "the model picks the tool"],
    ["code", "Act", "typed arguments"],
    ["check", "Reflect", "verify and repair"],
  ];
  roles.forEach(([ic, head, body], i) => {
    const x = P.m + (i % 2) * 3.0;
    const y = 2.2 + Math.floor(i / 2) * 1.8;
    const w = 2.8;
    box(s, x, y, w, 1.62, { fill: C.white, line: C.line, radius: 0.06 });
    icon(s, ic, x + 0.2, y + 0.2, 0.4, C.ink);
    txt(s, head, x + 0.7, y + 0.22, w - 0.8, 0.32, { bold: true });
    txt(s, body, x + 0.2, y + 0.86, w - 0.4, 0.4, { color: C.card });
  });

  const lx = 6.9, ly = 2.2, lw = 5.85, lh = 2.9;
  box(s, lx, ly, lw, lh, { fill: C.white, line: C.line, radius: 0.07 });
  box(s, lx + 0.3, ly + 0.5, 2.1, 0.7, { fill: C.ink, line: C.ink, radius: 0.06 });
  txt(s, "agent", lx + 0.3, ly + 0.67, 2.1, 0.34, { color: C.white, align: "center", bold: true });
  box(s, lx + 3.45, ly + 0.5, 2.1, 0.7, { fill: C.white, line: C.cobalt, radius: 0.06 });
  txt(s, "tools", lx + 3.45, ly + 0.67, 2.1, 0.34, { color: C.cobalt, align: "center", bold: true });
  arrow(s, lx + 2.45, ly + 0.7, lx + 3.4, ly + 0.7, { color: C.ink, width: 1.4 });
  arrow(s, lx + 3.4, ly + 1.0, lx + 2.45, ly + 1.0, { color: C.ink, width: 1.4, dash: "dash" });
  txt(s, "Bounded calls; last call answers.", lx + 0.3, ly + 1.7, lw - 0.6, 0.34, { color: C.card });
  txt(s, "Events are persisted.", lx + 0.3, ly + 2.15, lw - 0.6, 0.34, { color: C.card });

  txt(s, "TOOL SURFACE", lx, 5.55, 3.0, 0.3, { color: C.cobalt, bold: true, spacing: 1.2 });
  const toolsRow1 = ["search_course", "read_course_page", "verify_span"];
  const toolWidths = [1.8, 2.3, 1.55];
  let tx = lx;
  toolsRow1.forEach((t, i) => {
    chip(s, tx, 5.92, toolWidths[i], t, { mono: true, h: 0.36 });
    tx += toolWidths[i] + 0.08;
  });
  chip(s, lx, 6.38, 1.45, "web_search", { mono: true, h: 0.36 });
  chip(s, lx + 1.55, 6.38, 1.35, "web_fetch", { mono: true, h: 0.36 });
  txt(s, "No shell. Typed calls only.", lx + 3.1, 6.38, 2.75, 0.4, { color: C.ink, bold: true });
  footer(s, "06");
}

function slideAgentDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  kicker(s, "06 / DEMO / AGENT", true);
  title(s, "Watch the loop work.", true);
  shot(s, "agent-workchain.png", 0.55, 1.62, 6.0, 0.791, { shadow: true, alt: "Expanded work chain: searches, page reads, verify_span" });
  txt(s, "Real turn, replayed from JSONL.", 0.55, 6.55, 6.3, 0.3, { color: C.line });

  const stats = [
    ["5", "retrieval calls", "three searches, two page reads"],
    ["2", "pages read", "page 9 and page 10"],
    ["4", "span checks", "doc_id, page_no, exact quote"],
  ];
  stats.forEach(([n, head, body], i) => {
    const y = 1.78 + i * 1.5;
    disp(s, n, 7.15, y, 0.9, 0.7, { color: C.white });
    txt(s, head, 8.0, y + 0.06, 4.6, 0.32, { color: C.white, bold: true });
    txt(s, body, 8.0, y + 0.44, 4.7, 0.3, { color: C.line });
    if (i < 2) rule(s, 7.15, y + 1.22, 5.55, C.line, 0.006);
  });
  txt(s, "verify_span returns span verified.", 7.15, 6.3, 5.5, 0.3, { color: C.cobalt, bold: true });
  txt(s, "No network needed.", 7.15, 6.68, 5.5, 0.3, { color: C.line });
  footer(s, "07", true);
}

function slideRagOffline() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "07 / FUNCTIONS / RAG OFFLINE");
  title(s, "Build the evidence base on TACC.");
  lead(s, "One offline pipeline; no request-time index.", false);

  const stages = [
    ["file", "PDFs", "16 documents"],
    ["cloud", "TACC OCR", "PaddleOCR-VL"],
    ["layers", "Page chunks", "450-token pages"],
    ["database", "BGE-M3", "612 vectors"],
    ["server", "SQLite", "local store"],
  ];
  stages.forEach(([ic, head, body], i) => {
    const w = 2.18, x = P.m + i * 2.44, y = 2.18, h = 1.18;
    const dark = i === 1 || i === 3;
    box(s, x, y, w, h, { fill: dark ? C.card : C.white, line: dark ? C.card : C.line, radius: 0.06 });
    icon(s, ic, x + 0.16, y + 0.16, 0.36, dark ? C.white : C.cobalt, 1.3);
    txt(s, head, x + 0.6, y + 0.18, w - 0.7, 0.32, { color: dark ? C.white : C.ink, bold: true });
    txt(s, body, x + 0.16, y + 0.7, w - 0.3, 0.3, { color: dark ? C.line : C.card });
    if (i < 4) arrow(s, x + w + 0.02, y + 0.58, x + 2.4, y + 0.58, { color: C.ink, width: 1.2 });
  });

  const stats = [["16", "documents"], ["593", "pages"], ["612", "chunks / vectors"], ["16", "summaries"]];
  stats.forEach(([n, label], i) => {
    stat(s, n, label, P.m + i * 3.05, 3.68, 2.4);
  });

  const imgW = 2.4;
  courseImage(s, "acs2-p09.png", P.m, 5.02, imgW, { alt: "Lecture 2 page 9" });
  courseImage(s, "acs2-p10.png", P.m + 2.62, 5.02, imgW, { alt: "Lecture 2 page 10" });
  txt(s, "Page is the retrieval unit.", P.m + 5.4, 5.2, 6.8, 0.34, { bold: true });
  txt(s, "354 of 365 pages are one chunk at 450 tokens.", P.m + 5.4, 5.64, 6.8, 0.34, { color: C.card });
  txt(s, "Import rebuilds the corpus offline.", P.m + 5.4, 6.08, 6.8, 0.34, { color: C.card });
  footer(s, "08");
}

function slideRagOnline() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "08 / FUNCTIONS / RAG ONLINE");
  title(s, "Retrieve pages, then let the model read.");
  lead(s, "The model queries; retrieval returns page text.", false);

  const nodes = [
    ["chat", "Question", "student turn"],
    ["search", "Two arms", "top 30 each"],
    ["layers", "RRF", "k=60"],
    ["code", "Tools", "typed tools"],
    ["file", "Answer", "markers"],
  ];
  nodes.forEach(([ic, head, body], i) => {
    const w = 2.1, x = P.m + i * 2.48, y = 2.15, h = 1.15;
    const last = i === 4;
    box(s, x, y, w, h, { fill: last ? C.cobalt : C.white, line: last ? C.cobalt : C.line, radius: 0.06 });
    icon(s, ic, x + 0.16, y + 0.16, 0.36, last ? C.white : C.ink);
    txt(s, head, x + 0.6, y + 0.17, w - 0.7, 0.32, { color: last ? C.white : C.ink, bold: true });
    txt(s, body, x + 0.16, y + 0.7, w - 0.3, 0.3, { color: last ? C.line : C.card });
    if (i < 4) arrow(s, x + w + 0.02, y + 0.57, x + 2.44, y + 0.57, { color: C.ink, width: 1.2 });
  });

  const stats = [["0.849", "nDCG@5"], ["0.882", "hit@5"], ["937", "tokens@5"]];
  stats.forEach(([n, label], i) => {
    stat(s, n, label, P.m + i * 3.05, 3.62, 2.6);
  });
  txt(s, "Chunking study: 51 questions.", P.m, 5.0, 7.6, 0.34, { color: C.card });

  box(s, P.m, 5.45, P.contentW, 1.1, { fill: C.white, line: C.cobalt, radius: 0.07 });
  icon(s, "alert", P.m + 0.22, 5.66, 0.38, C.ink);
  txt(s, "Marker: retrieved page, not citation.", P.m + 0.82, 5.64, 9.9, 0.34, { bold: true });
  txt(s, "30 candidates per arm; RRF fuses to pages.", P.m + 0.82, 6.04, 9.9, 0.34, { color: C.card });
  footer(s, "09");
}

function slideRagDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  kicker(s, "09 / DEMO / RAG", true);
  title(s, "Every paragraph names its source.", true);

  const aw = 6.6, ah = aw * 0.674;
  shot(s, "rag-answer-detail.png", 0.55, 1.72, aw, 0.674, { shadow: true, alt: "Answer with inline source markers" });
  txt(s, "The marker opens the exact course page.", 0.55, 6.28, aw, 0.34, { color: C.white, bold: true });
  txt(s, "A source is not yet a citation.", 0.55, 6.66, aw, 0.34, { color: C.line });

  const sx = 7.55, sw = 4.75, sh = sw * 0.590;
  shot(s, "rag-source-pane.png", sx, 1.72, sw, 0.590, { shadow: true, alt: "Source pane in marker order" });

  const rows = [
    ["14", "retrieved pages"],
    ["exact", "page numbers"],
    ["0", "verified citations"],
  ];
  rows.forEach(([n, label], i) => {
    const y = 4.62 + i * 0.7;
    disp(s, n, sx, y, 1.9, 0.62, { color: C.white });
    txt(s, label, sx + 1.95, y + 0.12, 2.8, 0.34, { color: C.line });
    if (i < 2) rule(s, sx, y + 0.64, sw, C.line, 0.006);
  });
  footer(s, "10", true);
}

function slideKnowledge() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "10 / FUNCTIONS / KNOWLEDGE");
  title(s, "A conversation that lives beside the file.");
  lead(s, "The open page is context, not injected text.", false);

  const iw = 3.05;
  const ih = iw * 1.411;
  shot(s, "kb-chat-before.png", P.m, 2.15, iw, 1.411, { shadow: true, alt: "Page chat with inline page markers" });
  txt(s, "PAGE CHAT  /  LECTURE 2", P.m, 6.55, 3.4, 0.3, { color: C.cobalt, bold: true });

  const steps = [
    ["file", "doc_id and page_no", "The open document travels with each request."],
    ["code", "read_course_page", "Page text is not pre-loaded."],
    ["chat", "thread per file", "History resumes for that document."],
  ];
  steps.forEach(([ic, head, body], i) => {
    const y = 2.2 + i * 1.45;
    iconTile(s, ic, 4.05, y, 0.56, { color: C.cobalt });
    txt(s, head, 4.85, y + 0.0, 7.8, 0.34, { bold: true });
    txt(s, body, 4.85, y + 0.4, 7.8, 0.34, { color: C.card });
    if (i < 2) rule(s, 4.05, y + 1.1, 8.4, C.line, 0.006);
  });
  mono(s, "marker → /knowledge/docs/<doc>?page=N", 4.05, 6.55, 8.5, 0.3, { color: C.card });
  footer(s, "11");
}

function slideKnowledgeDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  kicker(s, "11 / DEMO / KNOWLEDGE", true);
  title(s, "From a marker to the exact page.", true);

  const chatW = 2.45;
  shot(s, "kb-chat-before.png", 0.55, 2.15, chatW, 1.411, { shadow: true, alt: "Page chat answer" });
  const pageW = 4.0;
  courseImage(s, "acs2-p09.png", 3.4, 2.39, pageW, { shadow: true, alt: "Lecture 2 page 9" });
  courseImage(s, "acs2-p10.png", 7.85, 2.39, pageW, { shadow: true, alt: "Lecture 2 page 10" });

  txt(s, "ANSWER  p.9 → p.10", 0.55, 1.82, 2.6, 0.3, { color: C.line, bold: true });
  txt(s, "BEFORE  /  p.9", 3.4, 1.82, 3.0, 0.3, { color: C.line, bold: true });
  txt(s, "AFTER  /  p.10", 7.85, 1.82, 3.0, 0.3, { color: C.line, bold: true });
  arrow(s, 7.5, 3.9, 7.82, 3.9, { color: C.white, width: 2 });
  txt(s, "Click [3]: the PDF moves to page 10; the chat stays.", 0.55, 6.02, 8.0, 0.34, { color: C.white, bold: true });
  txt(s, "[2] can cross documents: Lecture 3, p.74.", 0.55, 6.42, 8.0, 0.34, { color: C.line });
  footer(s, "12", true);
}

function slideVerifier() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "12 / VERIFIER");
  title(s, "A source is not a citation until the span passes.", false, { h: 1.2 });
  lead(s, "Implementation: Yoga.", false);

  const steps = [
    ["spark", "Normalize", "case and whitespace"],
    ["search", "Locate", "span on the cited page"],
    ["clock", "Repair", "one round"],
    ["alert", "Abstain", "name the gap"],
  ];
  steps.forEach(([ic, head, body], i) => {
    const y = 2.4 + i * 1.1;
    icon(s, ic, P.m, y, 0.4, C.ink, 1.3);
    txt(s, head, P.m + 0.68, y - 0.03, 2.0, 0.34, { bold: true });
    txt(s, body, P.m + 2.55, y - 0.03, 3.9, 0.34, { color: C.card });
  });

  // pass card
  const px = 6.95, pw = 5.8;
  box(s, px, 2.05, pw, 1.95, { fill: C.white, line: C.cobalt, radius: 0.06 });
  txt(s, "PASS", px + 0.22, 2.2, 1.0, 0.3, { color: C.cobalt, bold: true, spacing: 1.2 });
  mono(s, '"PU core number doubling every ~2 years."', px + 0.22, 2.55, 3.6, 0.62, { color: C.ink, ls: 1.05 });
  txt(s, "p.9 → citation", px + 0.22, 3.35, 3.6, 0.34, { color: C.cobalt, bold: true });
  const tw = 1.55;
  courseImage(s, "acs2-p09.png", px + pw - tw - 0.22, 2.22, tw, { frame: false, alt: "Lecture 2 page 9" });

  // fail card
  box(s, px, 4.2, pw, 1.95, { fill: C.white, line: C.failure, radius: 0.06 });
  txt(s, "FAIL", px + 0.22, 4.35, 1.0, 0.3, { color: C.failure, bold: true, spacing: 1.2 });
  mono(s, '"IO-aware tiling saves HBM traffic."', px + 0.22, 4.7, 4.9, 0.62, { color: C.ink, ls: 1.05 });
  txt(s, "not on p.40 → repair → abstain", px + 0.22, 5.5, 5.2, 0.34, { color: C.failure, bold: true });

  box(s, P.m, 6.25, P.contentW, 0.55, { fill: C.white, line: C.line, radius: 0.05, dash: "dash" });
  mono(s, "citations table: verified layer, next.", P.m + 0.18, 6.35, 8.0, 0.3, { color: C.cobalt });
  footer(s, "13");
}

function slidePractice() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "13 / FUNCTIONS / PRACTICE & POLICY");
  title(s, "Practice and integrity.");
  lead(s, "One record; one clock.", false);

  const lx = P.m, lw = 5.9, ly = 2.1, lh = 4.4;
  box(s, lx, ly, lw, lh, { fill: C.white, line: C.line, radius: 0.08 });
  icon(s, "book", lx + 0.24, ly + 0.24, 0.46, C.ink);
  txt(s, "Practice", lx + 0.9, ly + 0.28, 4.4, 0.34, { bold: true });
  const types = ["Single", "Multiple", "True / false", "Short answer", "Code"];
  types.forEach((t, i) => {
    chip(s, lx + 0.24 + (i % 3) * 1.85, ly + 1.05 + Math.floor(i / 3) * 0.5, 1.7, t, { h: 0.4 });
  });
  txt(s, "Choice deterministic; open model-graded.", lx + 0.24, ly + 2.25, lw - 0.5, 0.4, { color: C.card });
  box(s, lx + 0.24, ly + 3.2, lw - 0.48, 0.8, { fill: C.paper, line: C.line, radius: 0.05 });
  mono(s, "FlashAttention · 2 points · [3]", lx + 0.4, ly + 3.4, lw - 0.8, 0.3, { color: C.ink });

  const rx = 6.75, rw = 5.95;
  box(s, rx, ly, rw, lh, { fill: C.white, line: C.line, radius: 0.08 });
  icon(s, "lock", rx + 0.24, ly + 0.24, 0.46, C.ink);
  txt(s, "Disclosure gate", rx + 0.9, ly + 0.28, 4.4, 0.34, { bold: true });
  const states = [
    ["pre-release", "refuse + hint"],
    ["active", "refuse + hint"],
    ["extension", "refuse + hint"],
    ["post-deadline", "full teaching"],
    ["unknown", "abstain"],
  ];
  states.forEach(([state, outcome], i) => {
    const y = ly + 1.1 + i * 0.48;
    dot(s, rx + 0.34, y + 0.18, 0.055, i === 3 ? C.cobalt : C.ink);
    txt(s, state, rx + 0.55, y, 2.3, 0.32, { bold: i === 3 });
    txt(s, outcome, rx + 2.95, y, 2.7, 0.32, { color: i === 3 ? C.cobalt : C.card, bold: i === 3 });
  });
  txt(s, "The gate runs before the model.", rx + 0.24, ly + 3.95, rw - 0.5, 0.34, { bold: true });
  footer(s, "14");
}

function slidePracticeDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  kicker(s, "14 / DEMO / PRACTICE & POLICY", true);
  title(s, "Practice, then check.", true);

  const pw = 6.0;
  const ph = pw * 0.740;
  shot(s, "practice-question.png", 0.55, 1.92, pw, 0.740, { shadow: true, alt: "Generated single-choice practice question" });
  txt(s, "GENERATED QUESTION", 0.55, 1.62, 4.0, 0.3, { color: C.line, bold: true });
  txt(s, "Source [3] · 2 points · single choice", 0.55, 6.5, pw, 0.34, { color: C.white, bold: true });

  const rw = 5.75;
  const rh = rw * 0.379;
  shot(s, "policy-refusal.png", 7.0, 1.92, rw, 0.379, { shadow: true, alt: "Assignment 3 refusal before the deadline" });
  txt(s, "POLICY  /  ASSIGNMENT 3", 7.0, 1.62, 4.0, 0.3, { color: C.line, bold: true });
  txt(s, "Complete solution refused before the deadline.", 7.0, 4.36, rw, 0.34, { color: C.white, bold: true });
  txt(s, "The refusal offers concepts, a similar example, or a hint.", 7.0, 4.76, rw, 0.62, { color: C.line });
  ["concepts", "example", "hint"].forEach((t, i) => {
    chip(s, 7.0 + i * 1.35, 5.55, 1.25, t, { h: 0.38 });
  });
  txt(s, "Policy is code, not a prompt.", 7.0, 6.5, rw, 0.34, { color: C.white, bold: true });
  footer(s, "15", true);
}

function slideEvaluation() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "15 / EVALUATION");
  title(s, "We win on coverage. We tie on grading.");
  lead(s, "10 practice questions, 15 citation questions, three hosted assistants.", false);

  // table
  const tx = P.m, ty = 2.2, tw = 7.3;
  const cols = ["Practice", "Tutor", "Doubao", "Gemini", "Qwen"];
  const widths = [2.35, 1.2, 1.25, 1.25, 1.25];
  const rows = [
    ["Grounded", "10/10", "10/10", "6/10", "6/10"],
    ["Off-topic", "0/10", "0/10", "4/10", "4/10"],
    ["Coverage", "5/5", "3/5", "3/5", "3/5"],
    ["Grading", "10/10", "10/10", "10/10", "10/10"],
    ["Citations", "10/10", "8/10", "10/10", "9/10"],
  ];
  const rowH = 0.46;
  let cx = tx;
  cols.forEach((name, i) => {
    const w = widths[i];
    box(s, cx, ty, w, rowH, { fill: i === 1 ? C.cobalt : C.ink, line: i === 1 ? C.cobalt : C.ink, radius: 0.02 });
    txt(s, name, cx + (i === 0 ? 0.12 : 0), ty + 0.04, w - (i === 0 ? 0.12 : 0), rowH - 0.08, { color: C.white, bold: true, align: i === 0 ? "left" : "center", valign: "mid" });
    cx += w;
  });
  rows.forEach((row, r) => {
    let cx2 = tx;
    const ry = ty + rowH + r * rowH;
    row.forEach((val, c) => {
      const w = widths[c];
      box(s, cx2, ry, w, rowH, { fill: c === 1 ? C.white : C.paper, line: C.line, radius: 0.01, lineWidth: 0.75 });
      txt(s, val, cx2 + (c === 0 ? 0.12 : 0), ry + 0.04, w - (c === 0 ? 0.12 : 0), rowH - 0.08, {
        color: c === 1 ? C.cobalt : C.ink,
        bold: c === 1,
        align: c === 0 ? "left" : "center",
        valign: "mid",
      });
      cx2 += w;
    });
  });

  // scorecards
  const cards = [
    ["5/5 vs 3/5", "coverage"],
    ["0", "invented quotes"],
    ["TIE", "grading"],
  ];
  const cardIcons = ["gauge", "x", "check"];
  cards.forEach(([n, label], i) => {
    const y = 2.2 + i * 1.45;
    box(s, 8.35, y, 4.35, 1.25, { fill: C.white, line: C.line, radius: 0.06 });
    icon(s, cardIcons[i], 8.55, y + 0.42, 0.42, C.ink);
    disp(s, n, 9.15, y + 0.16, 3.3, 0.66, {});
    txt(s, label, 9.15, y + 0.84, 3.3, 0.32, { color: C.card });
  });

  txt(s, "Ties are reported as ties.", P.m, 5.9, 7.4, 0.34, { bold: true });
  txt(s, "Controls: Doubao, Gemini, Qwen, each with the PDFs uploaded.", P.m, 6.3, 7.4, 0.34, { color: C.card });
  footer(s, "16");
}

function slideFailure() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "16 / FAILURE & LIMITS");
  title(s, "Tutorials are the hard slice.");
  lead(s, "Page-level nDCG@5 on 51 test questions.", false);

  const bars = [
    ["concept", 0.912, false],
    ["assignment", 0.909, false],
    ["mechanism", 0.875, false],
    ["tutorial", 0.617, true],
  ];
  bars.forEach(([name, value, bad], i) => {
    const y = 2.28 + i * 0.68;
    txt(s, name, P.m, y + 0.02, 1.7, 0.34, { color: C.ink });
    box(s, P.m + 1.75, y + 0.03, 3.35, 0.34, { fill: C.line, line: C.line, radius: 0.02 });
    box(s, P.m + 1.75, y + 0.03, Math.max(0.1, 3.35 * value), 0.34, { fill: bad ? C.failure : C.cobalt, line: bad ? C.failure : C.cobalt, radius: 0.02 });
    txt(s, value.toFixed(3), P.m + 5.25, y + 0.02, 0.9, 0.34, { color: bad ? C.failure : C.ink, bold: true });
  });
  courseImage(s, "tutorial4-p40.png", P.m, 4.98, 2.1, { shadow: true, alt: "Tutorial 4 page 40" });
  disp(s, "0.617", P.m + 2.35, 5.02, 2.4, 0.7, { color: C.failure });
  txt(s, "tutorial nDCG@5", P.m + 2.4, 5.72, 3.4, 0.34, { color: C.failure, bold: true });
  txt(s, "Tutorial 4  ·  page 40", P.m + 2.4, 6.12, 3.4, 0.34, { color: C.card });

  // right cards
  const rx = 7.2, rw = 5.5;
  box(s, rx, 2.1, rw, 1.4, { fill: C.white, line: C.line, radius: 0.07 });
  icon(s, "alert", rx + 0.22, 2.28, 0.36, C.failure, 1.4);
  txt(s, "Root cause", rx + 0.72, 2.28, 4.0, 0.34, { bold: true });
  txt(s, "Tutorial pages bundle several sub-tasks.", rx + 0.22, 2.8, rw - 0.45, 0.34, { color: C.card });

  box(s, rx, 3.62, rw, 1.75, { fill: C.white, line: C.line, radius: 0.07 });
  icon(s, "chart", rx + 0.22, 3.8, 0.36, C.ink, 1.4);
  txt(s, "Lesson", rx + 0.72, 3.8, 4.0, 0.34, { bold: true });
  txt(s, "Dual granularity: hit@5 0.882 to 0.941,", rx + 0.22, 4.32, rw - 0.45, 0.34, { color: C.card });
  txt(s, "no nDCG gain, 2.7 times index cost.", rx + 0.22, 4.66, rw - 0.45, 0.34, { color: C.card });
  txt(s, "We kept page_first_450.", rx + 0.22, 4.98, rw - 0.45, 0.34, { bold: true });

  const limits = [
    ["file-text", "citations next"],
    ["terminal", "exec next"],
    ["book-open", "one course"],
    ["gauge", "434 s start"],
  ];
  limits.forEach(([ic, label], i) => {
    const x = rx + (i % 2) * 2.78;
    const y = 5.42 + Math.floor(i / 2) * 0.72;
    box(s, x, y, 2.66, 0.58, { fill: C.white, line: C.line, radius: 0.05 });
    icon(s, ic, x + 0.12, y + 0.14, 0.28, C.ink);
    txt(s, label, x + 0.5, y + 0.12, 2.1, 0.34, { color: C.card });
  });
  footer(s, "17");
}

function slideConclusion() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  kicker(s, "17 / CONCLUSION", true);
  title(s, "Verifiability is a system property.", true);

  const take = [
    ["layers", "Page-first retrieval", "beats BM25 and dense."],
    ["lock", "Policy as code", "the deadline changes the answer."],
    ["target", "Coverage and quote integrity", "coverage beats three assistants; grading ties."],
  ];
  take.forEach(([ic, head, body], i) => {
    const y = 1.95 + i * 1.18;
    iconTile(s, ic, P.m, y, 0.56, { color: C.white, fill: C.card, line: C.card });
    txt(s, head, P.m + 0.82, y + 0.0, 5.6, 0.34, { color: C.white, bold: true });
    txt(s, body, P.m + 0.82, y + 0.4, 5.6, 0.34, { color: C.line });
  });

  const fx = 7.3, fw = 5.3;
  box(s, fx, 1.95, fw, 3.55, { fill: C.card, line: C.card, radius: 0.07 });
  txt(s, "NEXT SURFACE", fx + 0.28, 2.1, 3.5, 0.34, { color: C.line, bold: true, spacing: 1.2 });
  txt(s, "Instructor/TA console", fx + 0.28, 2.5, fw - 0.5, 0.34, { color: C.white, bold: true });
  txt(s, "verified citations, TACC exec,", fx + 0.28, 2.92, fw - 0.5, 0.34, { color: C.line });
  txt(s, "multi-course support.", fx + 0.28, 3.28, fw - 0.5, 0.34, { color: C.line });
  s.addImage({ path: QR, x: fx + 0.28, y: 3.85, w: 1.2, h: 1.2, altText: "Repository QR code" });
  mono(s, "github.com/Kane-LI-0114", fx + 1.68, 4.05, 3.3, 0.3, { color: C.white });
  mono(s, "verifiable-tutor", fx + 1.68, 4.45, 3.3, 0.3, { color: C.white });

  rule(s, P.m, 5.92, P.contentW, C.line, 0.01);
  txt(s, "Questions?", P.m, 6.15, 3.5, 0.4, { color: C.white, bold: true });
  txt(s, "LI Jinchuan · TIAN Yujia · XIE Yifeng", 7.6, 6.55, 5.1, 0.34, { color: C.line, align: "right" });
  footer(s, "18", true);
}

function slideAppendixA1() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "APPENDIX / A1");
  title(s, "One question, end to end.");
  lead(s, "Solid is shipped; dashed is planned.", false);

  const row1 = [
    ["chat", "Student"],
    ["monitor", "React SPA"],
    ["server", "FastAPI"],
    ["lock", "Gate"],
    ["branch", "LangGraph"],
  ];
  const w = 2.18, step = 2.43, y1 = 2.15, y2 = 3.55, h = 0.95;
  row1.forEach(([ic, name], i) => {
    const x = P.m + i * step;
    box(s, x, y1, w, h, { fill: C.white, line: C.line, radius: 0.05 });
    icon(s, ic, x + 0.16, y1 + 0.28, 0.36, C.ink);
    txt(s, name, x + 0.66, y1 + 0.3, w - 0.75, 0.34, { bold: true, valign: "mid" });
    if (i < 4) arrow(s, x + w + 0.02, y1 + h / 2, x + step + 0.02, y1 + h / 2, { color: C.ink, width: 1.2 });
  });
  const row2 = [
    ["terminal", "Typed tools", false],
    ["check", "Verifier", true],
    ["cpu", "Model", false],
    ["database", "SQLite", false],
    ["file", "SSE frames", false],
  ];
  row2.forEach(([ic, name, dashed], j) => {
    const x = P.m + (4 - j) * step;
    box(s, x, y2, w, h, { fill: C.white, line: dashed ? C.cobalt : C.line, radius: 0.05, dash: dashed ? "dash" : "solid" });
    icon(s, ic, x + 0.16, y2 + 0.28, 0.36, dashed ? C.cobalt : C.ink);
    txt(s, name, x + 0.66, y2 + 0.3, w - 0.75, 0.34, { color: dashed ? C.cobalt : C.ink, bold: true, valign: "mid" });
    if (j < 4) {
      const xLeft = P.m + (3 - j) * step;
      arrow(s, x - 0.02, y2 + h / 2, xLeft + w + 0.02, y2 + h / 2, { color: C.ink, width: 1.2, dash: dashed ? "dash" : "solid" });
    }
  });
  arrow(s, P.m + 4 * step + w / 2, y1 + h + 0.02, P.m + 4 * step + w / 2, y2 - 0.02, { color: C.ink, width: 1.2 });

  rule(s, P.m, 5.3, 6.0, C.cobalt, 0.03);
  txt(s, "solid = shipped", P.m, 5.45, 2.6, 0.34, { color: C.ink, bold: true });
  line(s, P.m + 2.4, 5.62, P.m + 3.3, 5.62, C.ink, 1.5, { dash: "dash" });
  txt(s, "dashed = planned", P.m + 3.45, 5.45, 2.8, 0.34, { color: C.cobalt, bold: true });
  txt(s, "No inbound service; every TACC step is a submitted batch job.", P.m, 6.1, 11.0, 0.34, { color: C.card });
  txt(s, "One turn, nine steps.", P.m, 6.45, 11.0, 0.34, { color: C.card });
  footer(s, "A1");
}

function slideAppendixA2() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  kicker(s, "APPENDIX / A2");
  title(s, "Evaluation method and TACC evidence.");

  const lx = P.m, lw = 6.2;
  box(s, lx, 1.9, lw, 4.7, { fill: C.white, line: C.line, radius: 0.08 });
  icon(s, "chart", lx + 0.25, 2.12, 0.42, C.cobalt, 1.4);
  txt(s, "Evaluation method", lx + 0.85, 2.14, 4.6, 0.34, { bold: true });
  const methods = [
    ["Practice", "10 questions, 3 controls"],
    ["Citation", "15 questions, page + quote checked"],
    ["Grading", "10 questions, model vs ground truth"],
    ["Chunking", "51 questions, page-level nDCG@5"],
  ];
  methods.forEach(([head, body], i) => {
    const y = 2.9 + i * 0.92;
    txt(s, head, lx + 0.25, y, 1.7, 0.34, { bold: true });
    txt(s, body, lx + 2.0, y, lw - 2.3, 0.34, { color: C.card });
    if (i < 3) rule(s, lx + 0.25, y + 0.52, lw - 0.5, C.line, 0.006);
  });

  const rx = 7.1, rw = 5.6;
  box(s, rx, 1.9, rw, 4.7, { fill: C.card, line: C.card, radius: 0.08 });
  icon(s, "cpu", rx + 0.25, 2.12, 0.42, C.white, 1.4);
  txt(s, "TACC / Qwen job 28067", rx + 0.85, 2.14, 4.4, 0.34, { color: C.white, bold: true });
  const stats = [
    ["434 s", "vLLM cold start"],
    ["43.9 s", "8-chunk build"],
    ["8 / 8", "valid records"],
  ];
  stats.forEach(([n, label], i) => {
    const y = 2.85 + i * 1.1;
    disp(s, n, rx + 0.25, y, 2.4, 0.66, { color: C.white });
    txt(s, label, rx + 2.75, y + 0.12, 2.55, 0.34, { color: C.line });
  });
  txt(s, "One shard: 16 documents, 593 pages, 612 chunks.", rx + 0.25, 6.25, rw - 0.5, 0.3, { color: C.line });
  footer(s, "A2");
}

// ---------------------------------------------------------------- build

const notes = [
  "0:15. A tutor that can show its work. Every answer names the page it came from, and every practice question carries a reference answer.",
  "0:45. The user is a CSIT6000V student. The job is to keep up with dense material, practise at assignment scale, and know what help is allowed. The pain is that a fluent answer is not a checkable answer. We chose the task-oriented direction: measure the study loop against hosted assistants, not system efficiency.",
  "0:45. The product runs on the laptop: React SPA, FastAPI, LangGraph, SQLite and local files. TACC is a required model-serving backend, but only through submitted batch jobs: OCR, index, and the Qwen knowledge-base job. No inbound service. The bottom strip is the one-turn flow.",
  "0:30. All durable state is one local SQLite database: identity, conversations and the work chain, and the knowledge store. message_sources is the bridge from an answer to a document page; citations is the verified layer we are still wiring.",
  "0:25. The UI is a React SPA served by FastAPI; the agent is a typed LangGraph loop; retrieval is SQLite FTS5 plus BGE-M3; and batch model jobs run on TACC. Versions are pinned in package.json and pyproject.toml.",
  "0:40. Perception is the message, history, document context, and tool results. Planning is model-driven inside the agent node, constrained by a closed tool set. Execution validates arguments and streams results. Reflection is tool-mediated: verify_span, same-model retries, abstain when evidence is missing.",
  "0:30. This is a real turn: five retrieval calls, two page reads, and four span checks. verify_span carries the doc id, page number, and exact quote. The output is span verified. Every call is persisted in the work chain and can be replayed from JSONL.",
  "0:35. Offline, the course PDFs are parsed by a TACC OCR job, chunked page-first, embedded with BGE-M3 on TACC, and imported into the local SQLite store. The index never runs at request time. 16 documents, 593 pages, 612 chunks and vectors.",
  "0:35. Online, the model writes the tool query. FTS5 BM25 and a local BGE-M3 query embedding each return 30 candidates. RRF fuses them, and the tool returns page-anchored text with a marker. The model reads the page and checks the quote before answering.",
  "0:30. This is the source pane for one answer: 14 retrieved course pages in marker order. A marker opens the exact page. A source is retrieved evidence, not yet a verified citation; the verifier is the next layer.",
  "0:30. Every turn carries doc_id and page_no. The system note names the file and page but does not inject the page text; the model must call read_course_page. A citation target is a URL to that exact page, and the conversation belongs to the file.",
  "0:30. The open file is Lecture 2, page 9. The answer cites page 9, page 10, page 11 and a cross-document page. Clicking the page-10 marker moves the PDF to page 10 while the chat stays in place.",
  "0:30. The verifier normalizes whitespace and case, requires the quoted span to occur on the cited page, allows one repair round, and otherwise abstains. Pass becomes a citation; fail goes back to repair or abstention. Persisting the verified layer is the next step.",
  "0:30. Practice and self-test share one question record: five types, a reference answer, scoring points, and course citations. Choice questions are graded deterministically; open and code answers are model-graded. The disclosure gate is code, with five states from a dated registry.",
  "0:25. The student chooses a topic and type; the question comes from the course with a page marker. Before the deadline, a complete Assignment 3 solution is blocked and the refusal points to concepts, a similar example, or a hint.",
  "0:35. On ten practice questions we match the best control on groundedness, lead on knowledge-point coverage, and tie on grading. In the 15-question citation study we invent no quotes and no false negatives, and page numbers are programmatic. Ties are reported as ties.",
  "0:35. Tutorial questions retrieve worse than concept, mechanism or assignment questions. The likely cause is that tutorial pages bundle several sub-tasks into one page. Dual-granularity chunking raised hit@5 but not significantly, at 2.7 times the index cost, so we kept the page-first rule and logged it.",
  "0:30. The page is the retrieval unit, the policy is code, and the evaluation separates grounding from grading. The student loop is end-to-end. The operator console, verifier persistence, TACC execution, and multi-course support are the next surfaces.",
  "Appendix. The sequence from student to answer: SPA, API, gate, LangGraph, typed tools, verifier, model, store, and SSE. Solid is shipped; dashed is planned.",
  "Appendix. Ten practice questions and fifteen citation questions against three hosted assistants. The Qwen knowledge-base job 28067 measured a 434 second cold start, 43.9 second build, and 8 of 8 valid records.",
];

async function main() {
  slideCover();
  slideProblem();
  slideSystem();
  slideData();
  slideStack();
  slideAgent();
  slideAgentDemo();
  slideRagOffline();
  slideRagOnline();
  slideRagDemo();
  slideKnowledge();
  slideKnowledgeDemo();
  slideVerifier();
  slidePractice();
  slidePracticeDemo();
  slideEvaluation();
  slideFailure();
  slideConclusion();
  slideAppendixA1();
  slideAppendixA2();

  if (Array.isArray(pptx._slides)) {
    pptx._slides.forEach((slide, i) => {
      const note = notes[i] || (sourceSlides[i] && sourceSlides[i].notes);
      if (note) slide.addNotes(note);
    });
  }

  await pptx.writeFile({ fileName: OUT_PATH });

  // Sanitize the theme font scheme so the deck carries only Georgia / Arial.
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vt-deck-"));
  execFileSync("unzip", ["-q", OUT_PATH, "-d", tmp]);
  const themePath = path.join(tmp, "ppt", "theme", "theme1.xml");
  let theme = fs.readFileSync(themePath, "utf8");
  theme = theme.replace(
    /<a:fontScheme[\s\S]*?<\/a:fontScheme>/,
    '<a:fontScheme name="Verifiable Tutor"><a:majorFont><a:latin typeface="Georgia"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
  );
  fs.writeFileSync(themePath, theme);
  fs.rmSync(OUT_PATH);
  execFileSync("zip", ["-qrDX", OUT_PATH, "."], { cwd: tmp });
  fs.rmSync(tmp, { recursive: true, force: true });

  console.log("wrote", OUT_PATH);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
