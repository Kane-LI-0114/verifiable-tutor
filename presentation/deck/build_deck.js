const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");
const { COLORS, FONTS, PAGE } = require("./theme");
const { slides } = require("./content");

const ROOT = path.resolve(__dirname, "..");
const ASSETS = path.join(ROOT, "assets");
const pptx = new pptxgen();

pptx.layout = "LAYOUT_WIDE";
pptx.author = "LI Jinchuan, TIAN Yujia, XIE Yifeng";
pptx.company = "CSIT6000V";
pptx.subject = "Verifiable Tutor final presentation";
pptx.title = "Verifiable Tutor";
pptx.theme = { headFontFace: FONTS.display, bodyFontFace: FONTS.body };
pptx.lang = "en-US";

function text(slide, value, x, y, w, h, opts = {}) {
  const options = {
    x, y, w, h,
    fontFace: opts.fontFace || FONTS.body,
    fontSize: opts.fontSize || 12,
    color: opts.color || COLORS.ink,
    bold: Boolean(opts.bold),
    margin: 0,
    isTextBox: true,
    valign: opts.valign || "top",
    align: opts.align || "left",
    fit: opts.fit || "shrink",
    lineSpacingMultiple: opts.lineSpacingMultiple || 0.95,
    charSpacing: opts.charSpacing,
    breakLine: false,
  };
  slide.addText(String(value), options);
}

function box(slide, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: opts.radius == null ? 0.08 : opts.radius,
    fill: { color: opts.fill || COLORS.white, transparency: opts.transparency == null ? 0 : opts.transparency },
    line: {
      color: opts.line || COLORS.line,
      width: opts.lineWidth == null ? 1 : opts.lineWidth,
      dashType: opts.dashType || "solid",
      transparency: opts.lineTransparency == null ? 0 : opts.lineTransparency,
    },
    shadow: opts.shadow ? { type: "outer", color: "000000", blur: 8, angle: 45, distance: 2, opacity: 0.12 } : undefined,
  });
}

function rule(slide, x, y, w, color = COLORS.line, h = 0.008) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color },
    line: { color, width: 0 },
  });
}

function arrow(slide, x1, y1, x2, y2, opts = {}) {
  slide.addShape(pptx.ShapeType.line, {
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    w: Math.max(Math.abs(x2 - x1), 0.01),
    h: Math.max(Math.abs(y2 - y1), 0.01),
    line: {
      color: opts.color || COLORS.cobalt,
      width: opts.width == null ? 1.1 : opts.width,
      dashType: opts.dashType || "solid",
      endArrowType: opts.endArrowType === false ? "none" : "triangle",
    },
  });
}

function section(slide, value, dark = false) {
  text(slide, value.toUpperCase(), PAGE.margin, PAGE.headerY, 8.5, 0.22, {
    fontSize: 8.5,
    color: dark ? COLORS.whiteMuted : COLORS.cobalt,
    charSpacing: 1.4,
    bold: true,
  });
}

function title(slide, value, dark = false, opts = {}) {
  text(slide, value, PAGE.margin, opts.y == null ? PAGE.titleY : opts.y, opts.w || 11.6, opts.h || 0.9, {
    fontFace: FONTS.display,
    fontSize: opts.fontSize || 31,
    color: dark ? COLORS.white : COLORS.ink,
    bold: false,
    lineSpacingMultiple: 0.92,
  });
}

function footer(slide, page, dark = false) {
  rule(slide, PAGE.margin, PAGE.footerY, PAGE.contentW, dark ? "2A2A2A" : COLORS.line, 0.006);
  text(slide, "Verifiable Tutor  /  CSIT6000V", PAGE.margin, PAGE.footerY + 0.04, 5.0, 0.18, {
    fontSize: 8,
    color: dark ? COLORS.whiteMuted : COLORS.muted,
    charSpacing: 0.5,
  });
  text(slide, page, 11.95, PAGE.footerY + 0.04, 0.55, 0.18, {
    fontSize: 8,
    color: dark ? COLORS.whiteMuted : COLORS.muted,
    align: "right",
  });
}

function bg(slide, name) {
  slide.addImage({ path: path.join(ASSETS, "backgrounds", name), x: 0, y: 0, w: PAGE.w, h: PAGE.h, altText: "" });
}

function image(slide, name, x, y, w, ratio, alt) {
  slide.addImage({
    path: path.join(ASSETS, "screenshots", name),
    x, y, w, h: w * ratio,
    altText: alt,
  });
}

function label(slide, value, x, y, w, opts = {}) {
  text(slide, value.toUpperCase(), x, y, w, 0.2, {
    fontSize: opts.fontSize || 8,
    color: opts.color || COLORS.cobalt,
    bold: true,
    charSpacing: 1.2,
  });
}

function num(slide, n, x, y, dark = false) {
  box(slide, x, y, 0.25, 0.25, {
    fill: dark ? COLORS.cobalt : COLORS.cobalt,
    line: dark ? COLORS.cobalt : COLORS.cobalt,
    radius: 0.03,
  });
  text(slide, String(n), x, y + 0.005, 0.25, 0.23, {
    fontSize: 8,
    color: COLORS.white,
    bold: true,
    align: "center",
    valign: "mid",
  });
}

function matrix(slide, x, y, w, cols, rows, widths, opts = {}) {
  const headerH = opts.headerH || 0.4;
  const rowH = opts.rowH || 0.38;
  let cx = x;
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = w / total;
  cols.forEach((name, index) => {
    const cw = widths[index] * scale;
    box(slide, cx, y, cw, headerH, {
      fill: COLORS.ink,
      line: COLORS.ink,
      radius: 0.02,
    });
    text(slide, name, cx + 0.08, y + 0.05, cw - 0.12, headerH - 0.08, {
      fontSize: 8.5,
      color: COLORS.white,
      bold: true,
      valign: "mid",
      align: index === 0 ? "left" : "center",
    });
    cx += cw;
  });
  rows.forEach((row, r) => {
    let rx = x;
    const ry = y + headerH + r * rowH;
    row.forEach((value, c) => {
      const cw = widths[c] * scale;
      const fill = c === 1 && opts.highlight ? COLORS.cobaltSoft : (r % 2 === 0 ? COLORS.white : "F7F7F8");
      box(slide, rx, ry, cw, rowH, { fill, line: COLORS.line, radius: 0.01, lineWidth: 0.6 });
      text(slide, value, rx + 0.08, ry + 0.05, cw - 0.14, rowH - 0.08, {
        fontSize: opts.fontSize || 9,
        color: c === 1 && opts.highlight ? COLORS.cobalt : COLORS.ink,
        bold: c === 1 && opts.highlight,
        align: c === 0 ? "left" : "center",
        valign: "mid",
      });
      rx += cw;
    });
  });
}

function chip(slide, x, y, w, value, opts = {}) {
  box(slide, x, y, w, opts.h || 0.32, {
    fill: opts.fill || COLORS.white,
    line: opts.line || COLORS.line,
    radius: 0.05,
    dashType: opts.dashType || "solid",
  });
  text(slide, value, x + 0.08, y + 0.035, w - 0.16, (opts.h || 0.32) - 0.06, {
    fontSize: opts.fontSize || 8.5,
    color: opts.color || COLORS.ink,
    bold: Boolean(opts.bold),
    align: opts.align || "left",
    valign: "mid",
    fontFace: opts.mono ? FONTS.mono : FONTS.body,
  });
}

function slideTitle() {
  const s = pptx.addSlide();
  bg(s, "title.jpg");
  box(s, 0.8, 0.72, 0.38, 0.38, { fill: COLORS.cobalt, line: COLORS.cobalt, radius: 0.05 });
  text(s, "VT", 0.8, 0.755, 0.38, 0.3, { fontSize: 10, color: COLORS.white, bold: true, align: "center", valign: "mid" });
  section(s, "CSIT6000V / FINAL PRESENTATION / FALL 2026", true);
  text(s, slides[0].title, 0.8, 1.45, 7.2, 1.7, {
    fontFace: FONTS.display, fontSize: 54, color: COLORS.white, lineSpacingMultiple: 0.9,
  });
  text(s, "A course-grounded agent with evidence you can check.", 0.82, 3.35, 6.2, 1.2, {
    fontSize: 20, color: COLORS.whiteDim, lineSpacingMultiple: 1.0,
  });
  rule(s, 0.82, 4.62, 3.0, COLORS.cobalt, 0.02);
  text(s, "LI Jinchuan  ·  TIAN Yujia  ·  XIE Yifeng", 0.82, 5.45, 6.6, 0.3, {
    fontSize: 12, color: COLORS.white,
  });
  text(s, "21188271  ·  21201619  ·  21322152", 0.82, 5.78, 6.6, 0.25, {
    fontSize: 9, color: COLORS.whiteMuted,
  });
  text(s, "Advanced AI Computing and Systems  ·  Fall 2026", 0.82, 6.45, 6.6, 0.25, {
    fontSize: 9, color: COLORS.whiteMuted,
  });

  const cardX = 8.42, cardY = 1.18, cardW = 4.15, cardH = 5.15;
  box(s, cardX, cardY, cardW, cardH, {
    fill: COLORS.white, transparency: 90, line: COLORS.white, lineTransparency: 72, radius: 0.12, shadow: true,
  });
  label(s, "EVIDENCE LAYER", cardX + 0.28, cardY + 0.28, 3.4, { color: COLORS.whiteMuted });
  text(s, "Every answer names the page it came from.", cardX + 0.28, cardY + 0.65, 3.55, 1.55, {
    fontFace: FONTS.display, fontSize: 24, color: COLORS.white, lineSpacingMultiple: 0.95,
  });
  text(s, "A source marker is a pointer. A quoted span that passes the verifier is a citation.", cardX + 0.28, cardY + 2.35, 3.45, 1.0, {
    fontSize: 10.5, color: COLORS.whiteDim, lineSpacingMultiple: 1.0,
  });
  ["p.9", "p.10", "p.11"].forEach((p, i) => {
    chip(s, cardX + 0.28 + i * 0.67, cardY + 3.55, 0.58, p, {
      fill: COLORS.cobalt, line: COLORS.cobalt, color: COLORS.white, fontSize: 8.5, align: "center",
    });
  });
  text(s, "14 retrieved sources  ·  2 span checks", cardX + 0.28, cardY + 4.12, 3.45, 0.25, {
    fontSize: 8.5, color: COLORS.whiteMuted,
  });
  text(s, "01", 11.95, 7.08, 0.55, 0.18, { fontSize: 8, color: COLORS.whiteMuted, align: "right" });
}

function slideProblem() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "01 / PROBLEM & GOAL");
  title(s, "A study loop students can trust.");
  text(s, "One concrete user, one measurable job. Not a generic assistant.", PAGE.margin, 1.42, 10.5, 0.3, {
    fontSize: 12, color: COLORS.muted,
  });

  label(s, "PRIMARY USER", 0.65, 1.95, 5.0);
  text(s, "CSIT6000V student", 0.65, 2.18, 5.4, 0.45, { fontFace: FONTS.display, fontSize: 24, color: COLORS.ink });
  const rows = [
    ["Ask", "Understand dense lectures and tutorials without hunting for the page."],
    ["Practice", "Work at assignment scale with questions that stay inside the course."],
    ["Deadline", "Know whether a complete solution is allowed before the due date."],
  ];
  rows.forEach(([head, body], i) => {
    const y = 2.88 + i * 0.78;
    num(s, i + 1, 0.65, y + 0.02);
    text(s, head, 1.02, y, 1.1, 0.24, { fontSize: 10, bold: true, color: COLORS.ink });
    text(s, body, 1.02, y + 0.25, 5.25, 0.38, { fontSize: 10.5, color: COLORS.muted });
  });
  text(s, "Before: answer, then trust me.   After: answer, page, practice, policy.", 0.65, 5.55, 5.9, 0.3, {
    fontSize: 9.5, color: COLORS.cobalt,
  });

  label(s, "TASK-ORIENTED GOAL", 6.95, 1.95, 5.6);
  text(s, "The course brief asks for one concrete task and a measurable user benefit. We chose the student study loop, not system efficiency.", 6.95, 2.2, 5.65, 0.9, {
    fontSize: 11, color: COLORS.muted, lineSpacingMultiple: 1.0,
  });
  const contracts = [
    ["TEXT", "A claim cites a page and a quoted span. The span must occur on that page."],
    ["CODE", "A reference answer appears only after it compiles and passes its tests."],
    ["DISCLOSURE", "What may be revealed follows a dated policy, evaluated in code."],
  ];
  contracts.forEach(([head, body], i) => {
    const y = 3.28 + i * 0.95;
    box(s, 6.95, y, 5.6, 0.82, { fill: COLORS.white, line: COLORS.line, radius: 0.08, shadow: false });
    num(s, i + 1, 7.12, y + 0.18);
    text(s, head, 7.52, y + 0.12, 1.6, 0.22, { fontSize: 8, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
    text(s, body, 7.52, y + 0.34, 4.85, 0.4, { fontSize: 9.5, color: COLORS.ink });
  });
  text(s, "Baselines: Doubao  ·  Gemini  ·  Qwen", 6.95, 6.25, 5.5, 0.22, { fontSize: 8.5, color: COLORS.muted });
  text(s, "WHAT SUCCESS LOOKS LIKE", 0.65, 6.22, 3.4, 0.18, { fontSize: 7.5, bold: true, color: COLORS.cobalt, charSpacing: 1.0 });
  text(s, "Grounded answers  ·  course coverage  ·  page-exact sources  ·  grading agreement", 0.65, 6.46, 5.9, 0.22, { fontSize: 7.6, color: COLORS.muted });
  footer(s, "02");
}

function slideArchitecture() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "02 / SYSTEM");
  title(s, "One local product. One batch backend on TACC.");

  box(s, 0.65, 2.5, 1.15, 0.5, { fill: COLORS.ink, line: COLORS.ink, radius: 0.06 });
  text(s, "Student", 0.65, 2.61, 1.15, 0.22, { fontSize: 10, color: COLORS.white, align: "center" });
  arrow(s, 1.8, 2.75, 2.12, 2.75);

  box(s, 2.12, 1.7, 2.4, 2.55, { fill: COLORS.white, line: COLORS.line, radius: 0.1 });
  text(s, "React SPA", 2.3, 1.86, 2.0, 0.28, { fontSize: 11, bold: true });
  ["Chat", "Practice", "Knowledge"].forEach((v, i) => chip(s, 2.3, 2.28 + i * 0.42, 1.95, v, { fontSize: 9 }));
  text(s, "one origin", 2.3, 3.85, 1.95, 0.2, { fontSize: 8, color: COLORS.muted });

  box(s, 4.9, 1.52, 4.25, 3.35, { fill: COLORS.white, line: COLORS.line, radius: 0.1 });
  text(s, "FastAPI backend / one process", 5.08, 1.68, 3.8, 0.26, { fontSize: 10.5, bold: true });
  const be = ["API + SSE", "Accounts", "LangGraph + tools", "Disclosure gate", "Retrieval + verifier", "Practice + grading", "Model adapter", "Trace logger"];
  be.forEach((v, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    chip(s, 5.08 + col * 1.95, 2.08 + row * 0.55, 1.82, v, { fontSize: 8.2 });
  });

  box(s, 9.55, 1.52, 3.15, 1.55, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "External APIs", 9.72, 1.65, 2.8, 0.22, { fontSize: 9, bold: true });
  ["DeepSeek API", "MiMo API", "QQ Mail SMTP"].forEach((v, i) => text(s, v, 9.72, 1.95 + i * 0.27, 2.75, 0.2, { fontSize: 8.2 }));

  box(s, 9.55, 3.3, 3.15, 1.75, { fill: COLORS.graphiteCard, line: COLORS.graphiteLine, radius: 0.08, dashType: "dash" });
  text(s, "TACC batch / required", 9.72, 3.43, 2.8, 0.22, { fontSize: 9, bold: true, color: COLORS.white });
  ["OCR job", "Index job", "Exec / Eval (next)", "Qwen KB job"].forEach((v, i) => text(s, v, 9.72, 3.72 + i * 0.24, 2.7, 0.2, { fontSize: 8, color: COLORS.whiteDim }));
  text(s, "USERDIR", 9.72, 4.76, 2.7, 0.18, { fontSize: 7.5, color: COLORS.whiteMuted });

  box(s, 4.9, 5.02, 4.25, 0.72, { fill: COLORS.white, line: COLORS.line, radius: 0.07 });
  text(s, "SQLite + local files", 5.08, 5.14, 2.0, 0.2, { fontSize: 9, bold: true });
  text(s, "JSONL traces, corpus, index, KB  ·  Langfuse (dev only)", 5.08, 5.38, 3.9, 0.2, { fontSize: 7.5, color: COLORS.muted });

  arrow(s, 4.52, 2.55, 4.88, 2.55);
  arrow(s, 9.15, 2.25, 9.53, 2.25);
  arrow(s, 9.15, 3.75, 9.53, 3.75, { dashType: "dash" });
  arrow(s, 6.95, 4.87, 6.95, 5.0);
  arrow(s, 10.95, 5.05, 9.15, 5.35, { dashType: "dot", width: 0.9 });

  rule(s, 0.65, 5.95, 12.0, COLORS.line, 0.006);
  [["solid", "shipped"], ["dash", "planned / partial"], ["dot", "dev only"]].forEach(([dash, name], i) => {
    const x = 0.65 + i * 2.2;
    rule(s, x, 6.08, 0.35, dash === "solid" ? COLORS.cobalt : COLORS.muted, 0.02);
    text(s, name, x + 0.42, 6.02, 1.6, 0.18, { fontSize: 7.5, color: COLORS.muted });
  });
  text(s, "Aligned with PRD §1 Figure 1", 9.55, 6.02, 3.1, 0.2, { fontSize: 7.5, color: COLORS.muted, align: "right" });

  ["Ask", "Plan", "Act", "Reflect", "Answer + cite"].forEach((v, i) => {
    const x = 0.65 + i * 2.42;
    box(s, x, 6.42, 2.05, 0.36, { fill: i === 4 ? COLORS.cobalt : COLORS.white, line: i === 4 ? COLORS.cobalt : COLORS.line, radius: 0.05 });
    text(s, v, x, 6.49, 2.05, 0.2, { fontSize: 8, color: i === 4 ? COLORS.white : COLORS.ink, align: "center", bold: true });
    if (i < 4) arrow(s, x + 2.06, 6.6, x + 2.4, 6.6, { width: 0.8 });
  });
  footer(s, "03");
}

function slideDatabase() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "03 / DATA");
  title(s, "The data model makes the evidence chain durable.");

  box(s, 0.65, 1.55, 3.25, 2.2, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "Access", 0.85, 1.7, 2.8, 0.22, { fontSize: 10, bold: true });
  ["users", "verification_codes", "login_sessions"].forEach((v, i) => chip(s, 0.85, 2.1 + i * 0.38, 2.82, v, { fontSize: 8.5, mono: true }));

  box(s, 4.2, 1.5, 4.9, 4.55, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "Conversation & evidence", 4.4, 1.65, 4.4, 0.22, { fontSize: 10, bold: true });
  const conv = [
    ["conversations", "messages"],
    ["message_steps", "message_events"],
    ["message_sources", "tool_calls"],
    ["citations", ""],
  ];
  conv.forEach((pair, r) => {
    pair.forEach((v, c) => {
      if (!v) return;
      const highlight = v === "message_sources";
      const dashed = v === "citations";
      chip(s, 4.4 + c * 2.2, 2.1 + r * 0.55, 2.03, v, {
        fontSize: 8, mono: true,
        fill: highlight ? COLORS.cobaltSoft : COLORS.white,
        line: highlight ? COLORS.cobalt : COLORS.line,
        color: highlight ? COLORS.cobalt : COLORS.ink,
        bold: highlight,
        dashType: dashed ? "dash" : "solid",
      });
    });
  });
  text(s, "message_sources  =  answer → doc / page", 4.4, 4.62, 4.3, 0.2, { fontSize: 8, color: COLORS.cobalt });
  text(s, "citations  =  verified layer, next", 4.4, 4.86, 4.3, 0.2, { fontSize: 8, color: COLORS.muted });

  box(s, 9.45, 1.5, 3.25, 3.15, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "Knowledge / RAG", 9.65, 1.65, 2.8, 0.22, { fontSize: 10, bold: true });
  ["kb_folders", "kb_documents", "kb_chunks", "kb_chunks_fts", "kb_index_state", "knowledge_builds"].forEach((v, i) => {
    const highlight = v === "kb_chunks_fts";
    chip(s, 9.65, 2.08 + i * 0.38, 2.82, v, {
      fontSize: 8, mono: true,
      fill: highlight ? COLORS.cobaltSoft : COLORS.white,
      line: highlight ? COLORS.cobalt : COLORS.line,
      color: highlight ? COLORS.cobalt : COLORS.ink,
      bold: highlight,
    });
  });

  box(s, 9.45, 4.88, 3.25, 0.9, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "Learning", 9.65, 5.0, 2.8, 0.2, { fontSize: 9, bold: true });
  chip(s, 9.65, 5.28, 2.82, "topic_progress", { fontSize: 8, mono: true });

  arrow(s, 3.9, 2.55, 4.17, 2.55);
  arrow(s, 9.12, 2.55, 9.42, 2.55);
  rule(s, 0.65, 6.1, 12.0, COLORS.line, 0.006);
  text(s, "17 application tables + FTS5. Physical schema; PRD logical tables not yet physical are dashed.", 0.65, 6.2, 8.8, 0.2, { fontSize: 8, color: COLORS.muted });
  text(s, "SQLite / local-first", 10.4, 6.2, 2.2, 0.2, { fontSize: 8, color: COLORS.cobalt, align: "right" });
  footer(s, "04");
}

function slideStack() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "04 / STACK");
  title(s, "A small stack with one job per layer.");

  const rows = [
    ["INTERFACE", ["React 19", "Vite 8", "TypeScript 7", "Tailwind 4", "shadcn + AI Elements", "AI SDK 5", "PDF.js"], []],
    ["BACKEND", ["Python 3.12", "FastAPI 0.162", "Pydantic 2.14", "SSE", "SQLite FTS5"], []],
    ["AGENT", ["LangGraph 1.2.18", "5 typed tools", "budgets", "work chain"], [0]],
    ["RETRIEVAL", ["BGE-M3", "BM25", "RRF k=60", "NumPy"], [0, 1]],
    ["MODELS / PLATFORM", ["DeepSeek Flash", "MiMo 2.6", "TACC PaddleOCR-VL", "Qwen vLLM", "Langfuse", "pytest / Vitest"], [2]],
  ];
  rows.forEach(([labelText, chips, highlights], r) => {
    const y = 1.6 + r * 0.92;
    text(s, labelText, 0.65, y + 0.08, 1.35, 0.22, { fontSize: 7.8, bold: true, color: COLORS.muted, charSpacing: 1.1 });
    let x = 2.05;
    const total = chips.length;
    const gap = 0.08;
    const width = (10.6 - gap * (total - 1)) / total;
    chips.forEach((value, i) => {
      const hl = highlights.includes(i);
      chip(s, x, y, width, value, {
        fontSize: 8, h: 0.4,
        fill: hl ? COLORS.cobaltSoft : COLORS.white,
        line: hl ? COLORS.cobalt : COLORS.line,
        color: hl ? COLORS.cobalt : COLORS.ink,
        bold: hl,
        align: "center",
      });
      x += width + gap;
    });
  });
  text(s, "One origin.  Typed loop.  Local-first stores.  Batch TACC.", 0.65, 6.28, 10.4, 0.24, {
    fontSize: 10, color: COLORS.cobalt,
  });
  text(s, "Versions pinned in package.json / pyproject.toml / tech-selection.md", 0.65, 6.55, 11.0, 0.2, {
    fontSize: 7.5, color: COLORS.muted,
  });
  footer(s, "05");
}

function build() {
  slideTitle();
  slideProblem();
  slideArchitecture();
  slideDatabase();
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
    pptx._slides.forEach((slide, index) => {
      if (slides[index] && slides[index].notes) slide.addNotes(slides[index].notes);
    });
  } else {
    console.warn("pptxgenjs slides array unavailable; speaker notes not attached");
  }

  const out = path.join(ROOT, "CSIT6000V_VerifiableTutor_Final_2026F.pptx");
  return pptx.writeFile({ fileName: out }).then((file) => {
    try {
      execFileSync("zip", ["-dq", file, "*/"], { stdio: "ignore" });
    } catch (error) {
      console.warn("zip folder-entry cleanup skipped", error.message);
    }
    console.log("wrote", file);
  });
}

function slideAgent() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "05 / FUNCTIONS / AGENT");
  title(s, "A typed loop, not a prompt.");
  text(s, "The model cannot run a shell. It can call five audited tools, and the UI shows the chain.", PAGE.margin, 1.42, 11.0, 0.3, { fontSize: 12, color: COLORS.muted });

  const roles = [
    ["PERCEIVE", "Message, history, optional document context, and the tool results already in the turn."],
    ["PLAN", "The model picks the next tool or the answer. No separate planner node; the schema and budget constrain it."],
    ["ACT", "Arguments are validated by Pydantic. The tool returns bounded JSON and a numbered source."],
    ["REFLECT", "verify_span checks a quote. Same-model retries only; if evidence is missing, say what is missing."],
  ];
  roles.forEach(([head, body], i) => {
    const x = 0.65 + (i % 2) * 3.15;
    const y = 1.65 + Math.floor(i / 2) * 1.95;
    box(s, x, y, 3.0, 1.72, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
    num(s, i + 1, x + 0.18, y + 0.18);
    text(s, head, x + 0.55, y + 0.16, 2.2, 0.22, { fontSize: 8.5, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
    text(s, body, x + 0.18, y + 0.57, 2.62, 1.0, { fontSize: 9.5, color: COLORS.muted, lineSpacingMultiple: 1.0 });
  });

  box(s, 7.25, 1.62, 5.4, 2.45, { fill: COLORS.white, line: COLORS.line, radius: 0.1 });
  text(s, "THE LOOP", 7.45, 1.76, 2.0, 0.18, { fontSize: 7.8, bold: true, color: COLORS.cobalt, charSpacing: 1.2 });
  box(s, 7.5, 2.18, 1.35, 0.55, { fill: COLORS.ink, line: COLORS.ink, radius: 0.06 });
  text(s, "agent", 7.5, 2.31, 1.35, 0.22, { fontSize: 10, color: COLORS.white, align: "center" });
  box(s, 10.35, 2.18, 1.35, 0.55, { fill: COLORS.cobaltSoft, line: COLORS.cobalt, radius: 0.06 });
  text(s, "tools", 10.35, 2.31, 1.35, 0.22, { fontSize: 10, color: COLORS.cobalt, align: "center", bold: true });
  arrow(s, 8.88, 2.45, 10.3, 2.45);
  arrow(s, 10.3, 2.72, 8.88, 2.72, { dashType: "dash" });
  text(s, "max model calls / tool calls", 7.45, 3.0, 2.3, 0.2, { fontSize: 8, color: COLORS.muted });
  text(s, "last call without tools → answer or abstain", 7.45, 3.25, 4.6, 0.2, { fontSize: 8, color: COLORS.muted });
  text(s, "work-chain events persisted; JSONL replay", 7.45, 3.55, 4.6, 0.2, { fontSize: 8, color: COLORS.muted });

  text(s, "TOOL SURFACE", 7.25, 4.35, 2.0, 0.18, { fontSize: 7.8, bold: true, color: COLORS.cobalt, charSpacing: 1.2 });
  const tools = ["search_course", "read_course_page", "verify_span", "web_search", "web_fetch"];
  tools.forEach((tool, i) => {
    const col = i < 3 ? i : i - 3;
    const y = i < 3 ? 4.65 : 5.08;
    chip(s, 7.25 + col * 1.75, y, 1.62, tool, { fontSize: 7.4, mono: true, h: 0.3, align: "center" });
  });
  text(s, "No shell. Every call is typed, bounded, and visible.", 7.25, 5.62, 5.4, 0.25, { fontSize: 10, color: COLORS.ink });
  text(s, "Memory: conversation history + SQLite turn metadata. No long-term learner model.", 0.65, 5.72, 6.0, 0.3, { fontSize: 8.5, color: COLORS.muted });
  footer(s, "06");
}

function slideAgentDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  section(s, "06 / DEMO / AGENT", true);
  title(s, "Watch the loop work.", true);
  image(s, "agent-workchain.png", 0.55, 1.5, 6.55, 0.791, "Expanded work chain showing search, read, and verify_span tool calls");

  box(s, 7.4, 1.55, 5.25, 4.95, { fill: COLORS.graphiteCard, line: COLORS.white, lineTransparency: 82, radius: 0.1, transparency: 10 });
  label(s, "REAL TURN / ENGLISH", 7.65, 1.78, 4.6, { color: COLORS.cobalt });
  const items = [
    ["01", "Five retrieval calls", "Three search_course and two read_course_page calls, all visible with durations."],
    ["02", "Quote checked before answer", "verify_span carries doc_id, page_no, and the exact span."],
    ["03", "Output: span verified", "The quote occurs on page 9. The call is persisted in the work chain."],
  ];
  items.forEach(([n, head, body], i) => {
    const y = 2.25 + i * 1.3;
    num(s, n, 7.65, y, true);
    text(s, head, 8.02, y - 0.02, 4.2, 0.25, { fontSize: 11, color: COLORS.white, bold: true });
    text(s, body, 8.02, y + 0.28, 4.2, 0.65, { fontSize: 9.5, color: COLORS.whiteDim, lineSpacingMultiple: 1.0 });
  });
  text(s, "Replayable from JSONL. No network needed.", 7.65, 6.15, 4.6, 0.25, { fontSize: 8.5, color: COLORS.whiteMuted });
  footer(s, "07", true);
}

function slideRagOffline() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "07 / FUNCTIONS / RAG OFFLINE");
  title(s, "Build the evidence base on TACC.");
  text(s, "One offline pipeline. No index job runs at request time.", PAGE.margin, 1.42, 10.5, 0.3, { fontSize: 12, color: COLORS.muted });

  const stages = [
    ["PDFs", "16 documents / 593 pages", "LOCAL"],
    ["TACC OCR", "PaddleOCR-VL + layout", "TACC"],
    ["Chunk + FTS5", "page_first_450", "LOCAL"],
    ["BGE-M3 index", "612 vectors + row map", "TACC"],
    ["Local store", "SQLite + vectors", "LOCAL"],
  ];
  stages.forEach(([head, body, tag], i) => {
    const x = 0.65 + i * 2.48;
    const isTacc = tag === "TACC";
    box(s, x, 1.95, 2.15, 1.05, {
      fill: isTacc ? COLORS.graphiteCard : COLORS.white,
      line: isTacc ? COLORS.graphiteLine : COLORS.line,
      radius: 0.08,
      dashType: isTacc ? "dash" : "solid",
    });
    text(s, head, x + 0.14, 2.08, 1.9, 0.24, { fontSize: 10, bold: true, color: isTacc ? COLORS.white : COLORS.ink });
    text(s, body, x + 0.14, 2.38, 1.9, 0.3, { fontSize: 7.6, color: isTacc ? COLORS.whiteDim : COLORS.muted });
    text(s, tag, x + 0.14, 2.74, 1.9, 0.16, { fontSize: 6.5, color: isTacc ? COLORS.cobalt : COLORS.muted, charSpacing: 1.0 });
    if (i < stages.length - 1) arrow(s, x + 2.17, 2.48, x + 2.45, 2.48);
  });

  const stats = [["16", "documents"], ["593", "pages"], ["612", "chunks / vectors"], ["16", "summaries"]];
  stats.forEach(([n, l], i) => {
    const x = 0.65 + i * 3.0;
    text(s, n, x, 3.35, 1.2, 0.55, { fontFace: FONTS.display, fontSize: 30, color: COLORS.ink });
    text(s, l, x + 0.02, 3.93, 2.4, 0.2, { fontSize: 8.5, color: COLORS.muted });
  });

  const cards = [
    ["Page is the unit", "354 of 365 pages are one chunk at 450 tokens. Citations land on a page, not a fragment."],
    ["No vector database", "612 chunks: an exact NumPy matrix multiply is enough. SQLite owns FTS5 and metadata."],
    ["Import restores offline", "ingest_corpus.py import rebuilds chunks and vectors from tracked artifacts, without TACC."],
  ];
  cards.forEach(([head, body], i) => {
    const x = 0.65 + i * 4.05;
    box(s, x, 4.55, 3.85, 1.35, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
    text(s, head, x + 0.18, 4.7, 3.4, 0.24, { fontSize: 10, bold: true });
    text(s, body, x + 0.18, 4.98, 3.45, 0.8, { fontSize: 8.6, color: COLORS.muted, lineSpacingMultiple: 1.0 });
  });
  text(s, "TACC batch only. Artifacts downloaded to the laptop; no inbound service.", 0.65, 6.15, 8.2, 0.22, { fontSize: 8.5, color: COLORS.cobalt });
  footer(s, "08");
}

function slideRagOnline() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "08 / FUNCTIONS / RAG ONLINE");
  title(s, "Retrieve pages, then let the model read.");

  box(s, 0.65, 2.15, 1.85, 0.9, { fill: COLORS.ink, line: COLORS.ink, radius: 0.08 });
  text(s, "question", 0.8, 2.42, 1.55, 0.25, { fontSize: 10, color: COLORS.white, align: "center" });
  box(s, 2.9, 1.55, 2.25, 0.78, { fill: COLORS.white, line: COLORS.line, radius: 0.07 });
  text(s, "FTS5 BM25", 3.05, 1.7, 1.95, 0.22, { fontSize: 9, bold: true });
  text(s, "top 30 chunks", 3.05, 1.95, 1.95, 0.2, { fontSize: 7.8, color: COLORS.muted });
  box(s, 2.9, 2.65, 2.25, 0.78, { fill: COLORS.white, line: COLORS.line, radius: 0.07 });
  text(s, "BGE-M3 dense", 3.05, 2.8, 1.95, 0.22, { fontSize: 9, bold: true });
  text(s, "local query embedding", 3.05, 3.05, 1.95, 0.2, { fontSize: 7.8, color: COLORS.muted });
  arrow(s, 2.5, 2.55, 2.87, 2.0);
  arrow(s, 2.5, 2.65, 2.87, 3.0);

  box(s, 5.55, 1.95, 2.0, 1.1, { fill: COLORS.cobaltSoft, line: COLORS.cobalt, radius: 0.08 });
  text(s, "RRF", 5.7, 2.12, 1.7, 0.25, { fontSize: 12, bold: true, color: COLORS.cobalt, align: "center" });
  text(s, "k=60 · 1:1 · page dedupe", 5.7, 2.45, 1.7, 0.2, { fontSize: 7.2, color: COLORS.cobalt, align: "center" });
  arrow(s, 5.15, 1.9, 5.52, 2.3);
  arrow(s, 5.15, 3.0, 5.52, 2.7);

  box(s, 7.85, 1.95, 2.2, 1.1, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "agent tools", 8.0, 2.1, 1.9, 0.22, { fontSize: 9, bold: true });
  text(s, "search · read · verify", 8.0, 2.4, 1.9, 0.2, { fontSize: 7.8, color: COLORS.muted });
  arrow(s, 7.57, 2.5, 7.82, 2.5);

  box(s, 10.35, 1.95, 2.0, 1.1, { fill: COLORS.ink, line: COLORS.ink, radius: 0.08 });
  text(s, "answer + [ref_n]", 10.5, 2.1, 1.7, 0.22, { fontSize: 9, color: COLORS.white, bold: true });
  text(s, "source pane", 10.5, 2.4, 1.7, 0.2, { fontSize: 7.8, color: COLORS.whiteDim });
  arrow(s, 10.07, 2.5, 10.32, 2.5);

  const stats = [["0.849", "nDCG@5"], ["0.882", "hit@5"], ["937", "tokens@5"]];
  stats.forEach(([n, l], i) => {
    const x = 0.65 + i * 2.9;
    text(s, n, x, 3.55, 1.4, 0.5, { fontFace: FONTS.display, fontSize: 28 });
    text(s, l, x, 4.05, 1.8, 0.2, { fontSize: 8.5, color: COLORS.muted });
  });
  text(s, "chunking study, 51 test questions", 9.6, 4.05, 2.8, 0.2, { fontSize: 7.5, color: COLORS.muted, align: "right" });

  box(s, 0.65, 4.65, 11.95, 0.95, { fill: COLORS.cobaltSoft, line: COLORS.cobalt, radius: 0.08 });
  text(s, "source ≠ citation", 0.85, 4.8, 2.5, 0.25, { fontSize: 12, bold: true, color: COLORS.cobalt });
  text(s, "A marker names a retrieved page. Only a quoted span that passes the verifier becomes a citation.", 3.2, 4.82, 9.1, 0.25, { fontSize: 9.5, color: COLORS.ink });
  text(s, "Chat: the model writes the tool query. Knowledge search: plan_query rewrites Chinese → English for BM25.", 0.85, 5.18, 10.9, 0.2, { fontSize: 8, color: COLORS.muted });
  text(s, "Two arms, 30 candidates each; the fused top-k pages go back to the model, not into a hidden prompt.", 0.65, 5.9, 10.9, 0.22, { fontSize: 8.5, color: COLORS.muted });
  footer(s, "09");
}

function slideRagDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  section(s, "09 / DEMO / RAG", true);
  title(s, "Every paragraph names its source.", true);
  label(s, "ANSWER / INLINE MARKERS", 0.6, 1.3, 4.2, { color: COLORS.cobalt });
  label(s, "SOURCE PANE", 7.5, 1.3, 2.4, { color: COLORS.cobalt });
  image(s, "rag-answer-detail.png", 0.55, 1.5, 6.7, 0.665, "Answer detail with inline source markers");
  image(s, "rag-source-detail.png", 7.45, 1.5, 2.5, 1.971, "Per-answer source pane in marker order");

  box(s, 10.05, 1.5, 2.65, 5.05, { fill: COLORS.graphiteCard, line: COLORS.white, lineTransparency: 82, radius: 0.1, transparency: 10 });
  const items = [
    ["14", "retrieved pages", "One row per marker, in marker order."],
    ["p.9 / p.10 / p.11", "page-exact", "The row opens the exact course page."],
    ["0", "verified citations", "A marker is a source, not yet a citation."],
  ];
  items.forEach(([n, h, b], i) => {
    const y = 1.85 + i * 1.45;
    text(s, n, 10.2, y, 2.3, 0.35, { fontFace: FONTS.display, fontSize: i === 1 ? 14 : 21, color: COLORS.white });
    text(s, h, 10.2, y + 0.36, 2.3, 0.2, { fontSize: 7.2, color: COLORS.cobalt, bold: true, charSpacing: 0.7 });
    text(s, b, 10.2, y + 0.6, 2.3, 0.55, { fontSize: 7.4, color: COLORS.whiteDim, lineSpacingMultiple: 1.0 });
  });
  text(s, "The verifier decides whether a source becomes a citation. Yoga takes it from here.", 0.6, 6.55, 7.4, 0.25, { fontSize: 8, color: COLORS.whiteMuted });
  footer(s, "10", true);
}

function slideKnowledge() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "10 / FUNCTIONS / KNOWLEDGE");
  title(s, "A conversation that lives beside the file.");

  box(s, 0.65, 1.6, 6.15, 4.65, { fill: COLORS.white, line: COLORS.line, radius: 0.1 });
  text(s, "PDF + Page chat", 0.85, 1.75, 4.0, 0.25, { fontSize: 11, bold: true });
  box(s, 0.85, 2.2, 3.0, 3.65, { fill: COLORS.paper, line: COLORS.line, radius: 0.06 });
  text(s, "MEMORY WALL", 1.0, 2.38, 2.6, 0.2, { fontSize: 7.5, bold: true, color: COLORS.muted, charSpacing: 1.0 });
  text(s, "ACS_lecture_2_2026F", 1.0, 2.65, 2.5, 0.2, { fontSize: 8, color: COLORS.muted });
  text(s, "9 / 69", 1.0, 5.55, 2.5, 0.2, { fontSize: 8, color: COLORS.muted });
  box(s, 4.1, 2.2, 2.5, 3.65, { fill: COLORS.paper, line: COLORS.line, radius: 0.06 });
  text(s, "Page chat", 4.25, 2.35, 2.1, 0.2, { fontSize: 8.5, bold: true });
  box(s, 4.25, 2.72, 2.1, 0.55, { fill: COLORS.cobalt, line: COLORS.cobalt, radius: 0.05 });
  text(s, "What is the memory wall?", 4.33, 2.84, 1.95, 0.25, { fontSize: 7.5, color: COLORS.white });
  text(s, "p.9  [1]   p.10  [3]", 4.25, 3.45, 2.1, 0.2, { fontSize: 7.5, color: COLORS.cobalt });
  arrow(s, 3.9, 4.0, 4.08, 4.0);

  const steps = [
    ["Every turn carries doc_id + page_no", "document_context is sent with the request."],
    ["The page text is not given for free", "The system note names the file; the model must call read_course_page."],
    ["Markers become URLs", "sourceTarget resolves to /knowledge/docs/<doc>?page=N."],
    ["The thread belongs to the file", "History resumes the same conversation for that document."],
  ];
  steps.forEach(([head, body], i) => {
    const y = 1.65 + i * 1.05;
    num(s, i + 1, 7.15, y);
    text(s, head, 7.52, y - 0.02, 5.0, 0.24, { fontSize: 10, bold: true });
    text(s, body, 7.52, y + 0.27, 5.0, 0.4, { fontSize: 8.8, color: COLORS.muted });
  });
  text(s, "The open page is context, not a pre-filled prompt.", 0.65, 6.5, 8.0, 0.25, { fontSize: 10, color: COLORS.cobalt });
  footer(s, "11");
}

function slideKnowledgeDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  section(s, "11 / DEMO / KNOWLEDGE", true);
  title(s, "From a marker to the exact page.", true);

  image(s, "kb-chat-before.png", 0.5, 1.5, 3.3, 1.441, "Page chat answer with inline page markers");
  image(s, "kb-page9-detail.png", 4.65, 1.5, 3.85, 0.880, "PDF reader on page 9 before the citation click");
  image(s, "kb-page10-detail.png", 8.75, 1.5, 3.85, 0.880, "PDF reader on page 10 after the citation click");

  label(s, "ANSWER / p.9 + p.10", 0.72, 6.38, 3.0, { color: COLORS.cobalt });
  label(s, "BEFORE / p.9", 4.87, 4.98, 2.0, { color: COLORS.cobalt });
  label(s, "AFTER / p.10", 8.97, 4.98, 2.0, { color: COLORS.cobalt });
  arrow(s, 8.55, 3.0, 8.72, 3.0, { color: COLORS.cobalt, width: 1.4 });
  text(s, "Click [3] in the answer: the PDF moves to page 10, the chat stays.", 0.65, 6.68, 8.4, 0.22, { fontSize: 9, color: COLORS.white });
  text(s, "[2] can cross documents: Lecture 3, p.74.", 9.9, 6.68, 2.9, 0.22, { fontSize: 8, color: COLORS.whiteMuted, align: "right" });
  footer(s, "12", true);
}

function slideVerifier() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "12 / VERIFIER");
  title(s, "A source is not a citation until the span passes.");
  text(s, "The verifier is the hinge between retrieval and the answer. Implementation: Yoga.", PAGE.margin, 1.42, 10.5, 0.3, { fontSize: 12, color: COLORS.muted });

  const steps = [
    ["Normalize", "Whitespace and case are normalized before comparison."],
    ["Locate", "The quoted span must occur on the cited page's text."],
    ["Repair once", "A failed span gets one repair round, not a silent rewrite."],
    ["Abstain", "If it still fails, the answer names the missing evidence."],
  ];
  steps.forEach(([head, body], i) => {
    const y = 1.9 + i * 0.95;
    num(s, i + 1, 0.8, y);
    text(s, head, 1.18, y - 0.02, 5.3, 0.25, { fontSize: 11, bold: true });
    text(s, body, 1.18, y + 0.28, 5.3, 0.35, { fontSize: 9.5, color: COLORS.muted });
  });

  box(s, 7.35, 1.85, 5.2, 1.55, { fill: COLORS.cobaltSoft, line: COLORS.cobalt, radius: 0.1 });
  text(s, "PASS", 7.55, 2.0, 1.2, 0.2, { fontSize: 8, bold: true, color: COLORS.cobalt, charSpacing: 1.2 });
  text(s, "\"PU core number doubling every ~2 years.\"", 7.55, 2.28, 4.6, 0.25, { fontSize: 8.5, color: COLORS.ink, fontFace: FONTS.mono });
  text(s, "p.9  →  span verified  →  citation", 7.55, 2.75, 4.6, 0.25, { fontSize: 9, color: COLORS.cobalt, bold: true });
  text(s, "Pass keeps the claim and the page together.", 7.55, 3.05, 4.6, 0.2, { fontSize: 8, color: COLORS.muted });

  box(s, 7.35, 3.6, 5.2, 1.55, { fill: COLORS.failureSoft, line: COLORS.failure, radius: 0.1 });
  text(s, "FAIL", 7.55, 3.75, 1.2, 0.2, { fontSize: 8, bold: true, color: COLORS.failure, charSpacing: 1.2 });
  text(s, "\"IO-aware tiling saves HBM traffic.\"", 7.55, 4.03, 4.6, 0.25, { fontSize: 8.5, color: COLORS.ink, fontFace: FONTS.mono });
  text(s, "not on p.40  →  repair  →  abstain", 7.55, 4.5, 4.6, 0.25, { fontSize: 9, color: COLORS.failure, bold: true });
  text(s, "A fabricated quote never becomes a citation.", 7.55, 4.8, 4.6, 0.2, { fontSize: 8, color: COLORS.muted });

  box(s, 0.8, 5.65, 11.75, 0.7, { fill: COLORS.white, line: COLORS.line, radius: 0.07, dashType: "dash" });
  text(s, "citations table: verified layer, next", 1.0, 5.82, 4.0, 0.22, { fontSize: 9, bold: true, color: COLORS.cobalt });
  text(s, "Sources are shown today. Persisting the passing span is the gap between retrieval and a citation.", 4.6, 5.82, 7.6, 0.22, { fontSize: 8.5, color: COLORS.muted });
  footer(s, "13");
}

function slidePractice() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "13 / FUNCTIONS / PRACTICE & POLICY");
  title(s, "Practice and integrity.");
  text(s, "One question record for practice and self-test; one clock for disclosure.", PAGE.margin, 1.42, 10.5, 0.3, { fontSize: 12, color: COLORS.muted });

  box(s, 0.65, 1.7, 5.9, 4.55, { fill: COLORS.white, line: COLORS.line, radius: 0.1 });
  text(s, "PRACTICE & SELF-TEST", 0.88, 1.88, 4.8, 0.2, { fontSize: 8, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  ["single", "multiple", "true / false", "short answer", "code"].forEach((v, i) => chip(s, 0.88 + (i % 3) * 1.55, 2.18 + Math.floor(i / 3) * 0.42, 1.42, v, { fontSize: 8, h: 0.32, align: "center" }));
  text(s, "Reference answer + scoring points + page citations.", 0.88, 3.05, 5.2, 0.22, { fontSize: 9, color: COLORS.ink });
  text(s, "Choice questions grade deterministically. Open and code answers are model-graded against the scoring points.", 0.88, 3.38, 5.2, 0.55, { fontSize: 8.8, color: COLORS.muted, lineSpacingMultiple: 1.0 });
  box(s, 0.88, 4.2, 5.4, 1.0, { fill: COLORS.paper, line: COLORS.line, radius: 0.06 });
  text(s, "EXAMPLE RECORD", 1.05, 4.34, 2.6, 0.18, { fontSize: 7.2, bold: true, color: COLORS.cobalt, charSpacing: 1.0 });
  text(s, "FlashAttention · single choice · 2 points · source [3]", 1.05, 4.58, 4.95, 0.2, { fontSize: 8.5, color: COLORS.ink });
  text(s, "Reference answer + scoring points stay with the question.", 1.05, 4.85, 4.95, 0.2, { fontSize: 7.6, color: COLORS.muted });
  text(s, "A saved practice run is a conversation; the result keeps its sources.", 0.88, 5.55, 5.2, 0.22, { fontSize: 8, color: COLORS.cobalt });

  box(s, 6.85, 1.7, 5.8, 4.55, { fill: COLORS.white, line: COLORS.line, radius: 0.1 });
  text(s, "DISCLOSURE GATE", 7.08, 1.88, 4.8, 0.2, { fontSize: 8, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  const states = ["pre-release", "active", "extension", "post-deadline", "unknown"];
  states.forEach((v, i) => {
    const y = 2.2 + i * 0.56;
    box(s, 7.08, y, 0.22, 0.22, { fill: i === 1 ? COLORS.cobalt : COLORS.white, line: i === 1 ? COLORS.cobalt : COLORS.line, radius: 0.03 });
    text(s, v, 7.42, y - 0.01, 2.2, 0.22, { fontSize: 9, bold: i === 1, color: i === 1 ? COLORS.cobalt : COLORS.ink });
    text(s, i === 3 ? "full teaching" : i === 4 ? "abstain" : "refuse + hint", 9.7, y - 0.01, 2.6, 0.22, { fontSize: 8, color: COLORS.muted });
  });
  text(s, "The gate runs before the model. A complete solution is blocked while the named deadline is ahead.", 7.08, 5.3, 5.2, 0.35, { fontSize: 8.2, color: COLORS.muted });
  text(s, "Code, not a prompt instruction.", 7.08, 5.78, 5.2, 0.22, { fontSize: 9, color: COLORS.cobalt, bold: true });
  footer(s, "14");
}

function slidePracticeDemo() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  section(s, "14 / DEMO / PRACTICE & POLICY", true);
  title(s, "Practice, then check.", true);
  image(s, "practice-question.png", 0.5, 1.55, 6.0, 0.731, "Generated single-choice practice question with a source marker and two points");
  image(s, "policy-refusal.png", 7.0, 1.55, 5.7, 0.379, "Assignment 3 refusal before the deadline");
  text(s, "PRACTICE", 0.72, 6.05, 2.0, 0.2, { fontSize: 7.5, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  text(s, "topic and type → question + marker + points", 0.72, 6.28, 5.8, 0.2, { fontSize: 8, color: COLORS.whiteDim });
  text(s, "POLICY", 7.22, 3.95, 2.0, 0.2, { fontSize: 7.5, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  text(s, "Assignment 3, due 29 Nov: complete solution blocked before the deadline.", 7.22, 4.2, 5.4, 0.25, { fontSize: 9.5, color: COLORS.white });
  text(s, "The refusal offers concepts, a similar example, or a hint.", 7.22, 4.52, 5.4, 0.22, { fontSize: 8.5, color: COLORS.whiteMuted });
  footer(s, "15", true);
}

function slideEvaluation() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "15 / EVALUATION");
  title(s, "We win on coverage. We tie on grading.");
  text(s, "10 practice questions and 15 citation questions against three hosted assistants. Ties are reported as ties.", PAGE.margin, 1.42, 11.5, 0.3, { fontSize: 11, color: COLORS.muted });

  matrix(s, 0.65, 1.75, 6.0, ["Practice", "Tutor", "Doubao", "Gemini", "Qwen"], [
    ["Grounded questions", "10/10", "10/10", "6/10", "6/10"],
    ["Off-topic questions", "0/10", "0/10", "4/10", "4/10"],
    ["Knowledge coverage", "5/5", "3/5", "3/5", "3/5"],
    ["Grading accuracy", "10/10", "10/10", "10/10", "10/10"],
    ["Citation accuracy", "10/10", "8/10", "10/10", "9/10"],
  ], [1.9, 1, 1, 1, 1], { highlight: true, fontSize: 8.9, rowH: 0.38 });

  matrix(s, 6.85, 1.75, 5.8, ["Citation study", "Tutor", "Doubao", "Gemini", "Qwen"], [
    ["Invented quotes", "0", "0", "2", "1"],
    ["False \"not in PDF\"", "0", "3", "0", "0"],
    ["Page accuracy", "exact", "good", "best", "-1 page"],
  ], [2.0, 1, 1, 1, 1], { highlight: true, fontSize: 8.9, rowH: 0.38 });

  text(s, "Chunking study: hybrid nDCG@5 0.849, hit@5 0.882, 937 tokens@5.", 0.65, 4.25, 7.0, 0.2, { fontSize: 8, color: COLORS.muted });
  box(s, 0.65, 4.75, 11.95, 0.8, { fill: COLORS.cobaltSoft, line: COLORS.cobalt, radius: 0.08 });
  text(s, "Coverage 5/5 vs 3/5.  Zero invented quotes.  Grading is a tie.", 0.88, 4.96, 11.5, 0.3, { fontSize: 13, color: COLORS.cobalt, bold: true });
  text(s, "Controls: Doubao, Gemini, Qwen, each with the relevant PDFs uploaded.", 0.65, 5.8, 10.5, 0.2, { fontSize: 8, color: COLORS.muted });
  footer(s, "16");
}

function slideFailure() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "16 / FAILURE & LIMITS");
  title(s, "Tutorials are the hard slice.");
  text(s, "Page-level nDCG@5, 51 test questions. The tutorial slice is the weakest.", PAGE.margin, 1.42, 10.0, 0.3, { fontSize: 11, color: COLORS.muted });

  const bars = [["concept", 0.912, false], ["assignment", 0.909, false], ["mechanism", 0.875, false], ["tutorial", 0.617, true]];
  bars.forEach(([name, value, bad], i) => {
    const y = 2.0 + i * 0.78;
    text(s, name, 0.65, y, 1.55, 0.24, { fontSize: 9.5, color: COLORS.ink });
    box(s, 2.25, y + 0.02, 3.7, 0.28, { fill: "F1F1F3", line: "F1F1F3", radius: 0.02 });
    box(s, 2.25, y + 0.02, Math.max(0.08, 3.7 * value), 0.28, { fill: bad ? COLORS.failure : COLORS.cobalt, line: bad ? COLORS.failure : COLORS.cobalt, radius: 0.02 });
    text(s, value.toFixed(3), 6.08, y, 0.7, 0.24, { fontSize: 9.5, color: bad ? COLORS.failure : COLORS.ink, bold: true });
  });
  text(s, "0", 2.25, 5.22, 0.3, 0.18, { fontSize: 7, color: COLORS.muted });
  text(s, "1.0", 5.72, 5.22, 0.3, 0.18, { fontSize: 7, color: COLORS.muted });

  box(s, 7.0, 1.75, 5.6, 1.55, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "ROOT CAUSE", 7.2, 1.9, 2.0, 0.18, { fontSize: 7.8, bold: true, color: COLORS.failure, charSpacing: 1.1 });
  text(s, "Tutorial pages bundle several sub-tasks. Page-level chunks keep unrelated tasks together; figure-only pages weaken the text evidence.", 7.2, 2.15, 5.2, 0.95, { fontSize: 9, color: COLORS.muted, lineSpacingMultiple: 1.0 });

  box(s, 7.0, 3.48, 5.6, 1.55, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "LESSON", 7.2, 3.63, 2.0, 0.18, { fontSize: 7.8, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  text(s, "Genre-aware chunking is promising, not free: dual granularity raised hit@5 0.882 → 0.941, but the nDCG interval crossed zero and the index cost 2.7×. We kept page_first_450.", 7.2, 3.88, 5.2, 0.95, { fontSize: 8.8, color: COLORS.muted, lineSpacingMultiple: 1.0 });

  text(s, "WHAT WE DO NOT CLAIM", 0.65, 5.55, 3.5, 0.18, { fontSize: 7.8, bold: true, color: COLORS.muted, charSpacing: 1.1 });
  const limits = [
    ["Verified citations", "sources now; persistence next"],
    ["TACC execution", "model-graded; exec job next"],
    ["Scope", "one course, trusted users; instructor/TA UI partial"],
    ["TACC latency", "434s cold start; demo pre-built"],
  ];
  limits.forEach(([h, b], i) => {
    const x = 0.65 + i * 3.02;
    box(s, x, 5.8, 2.88, 0.82, { fill: COLORS.white, line: COLORS.line, radius: 0.06 });
    text(s, h, x + 0.12, 5.9, 2.6, 0.2, { fontSize: 8, bold: true });
    text(s, b, x + 0.12, 6.12, 2.6, 0.35, { fontSize: 7.2, color: COLORS.muted });
  });
  footer(s, "17");
}

function slideConclusion() {
  const s = pptx.addSlide();
  bg(s, "graphite.jpg");
  section(s, "17 / CONCLUSION", true);
  title(s, "Verifiability is a system property.", true);

  const take = [
    ["Page-first hybrid retrieval", "beats BM25 and dense on this corpus."],
    ["Policy is code", "the deadline changes what may be revealed."],
    ["Coverage and quote integrity", "beat three hosted assistants; grading ties."],
  ];
  take.forEach(([h, b], i) => {
    const y = 1.85 + i * 1.15;
    num(s, i + 1, 0.8, y, true);
    text(s, h, 1.18, y - 0.02, 4.9, 0.25, { fontSize: 11, color: COLORS.white, bold: true });
    text(s, b, 1.18, y + 0.28, 4.9, 0.4, { fontSize: 9.5, color: COLORS.whiteDim });
  });

  text(s, "FUTURE DEVELOPMENT", 7.1, 1.75, 4.8, 0.18, { fontSize: 7.8, bold: true, color: COLORS.cobalt, charSpacing: 1.2 });
  const future = [
    ["Instructor/TA console", "live KB build, deadline editor, TA grading and analytics."],
    ["Verifier + execution", "persist verified citations; add TACC code execution."],
    ["Multi-course", "course-scoped corpus, deadlines and memberships."],
  ];
  future.forEach(([h, b], i) => {
    const y = 2.18 + i * 1.0;
    text(s, h, 7.1, y, 4.8, 0.24, { fontSize: 10, color: COLORS.white, bold: true });
    text(s, b, 7.1, y + 0.27, 4.8, 0.4, { fontSize: 8.8, color: COLORS.whiteMuted });
  });

  box(s, 0.8, 5.55, 11.75, 0.9, { fill: COLORS.graphiteCard, line: COLORS.white, lineTransparency: 84, radius: 0.08, transparency: 8 });
  text(s, "The student loop is end-to-end; the operator loop is the next product surface.", 1.05, 5.78, 7.8, 0.3, { fontSize: 12, color: COLORS.white });
  text(s, "Questions?   github.com/Kane-LI-0114/verifiable-tutor", 8.9, 5.78, 3.4, 0.3, { fontSize: 8.5, color: COLORS.whiteMuted, align: "right" });
  footer(s, "18", true);
}

function slideAppendixA1() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "APPENDIX / A1");
  title(s, "One question, end to end.");
  text(s, "The delivered turn, with the planned verification layer marked.", PAGE.margin, 1.42, 9.0, 0.3, { fontSize: 11, color: COLORS.muted });

  const row1 = ["Student", "React SPA", "FastAPI", "Gate"];
  row1.forEach((v, i) => {
    const x = 0.65 + i * 3.05;
    box(s, x, 2.0, 2.55, 0.55, { fill: COLORS.white, line: COLORS.line, radius: 0.06 });
    text(s, v, x, 2.15, 2.55, 0.22, { fontSize: 9, align: "center" });
    if (i < 3) arrow(s, x + 2.57, 2.27, x + 3.02, 2.27);
  });
  const row2 = ["LangGraph", "Typed tools", "Verifier", "Model"];
  row2.forEach((v, i) => {
    const x = 0.65 + i * 3.05;
    const dashed = v === "Verifier";
    box(s, x, 3.05, 2.55, 0.55, { fill: dashed ? COLORS.cobaltSoft : COLORS.white, line: dashed ? COLORS.cobalt : COLORS.line, radius: 0.06, dashType: dashed ? "dash" : "solid" });
    text(s, v, x, 3.2, 2.55, 0.22, { fontSize: 9, align: "center", color: dashed ? COLORS.cobalt : COLORS.ink });
    if (i < 3) arrow(s, x + 2.57, 3.32, x + 3.02, 3.32, { dashType: dashed ? "dash" : "solid" });
  });
  ["SQLite + JSONL", "SSE frames"].forEach((v, i) => {
    const x = 2.2 + i * 5.0;
    box(s, x, 4.1, 3.0, 0.55, { fill: COLORS.white, line: COLORS.line, radius: 0.06 });
    text(s, v, x, 4.25, 3.0, 0.22, { fontSize: 9, align: "center" });
  });
  arrow(s, 1.92, 2.57, 1.92, 3.02);
  arrow(s, 8.0, 2.57, 8.0, 3.02);
  arrow(s, 10.3, 3.6, 10.3, 4.08);
  text(s, "solid = shipped   ·   dashed = planned / partial", 0.65, 5.25, 5.0, 0.2, { fontSize: 7.5, color: COLORS.muted });
  text(s, "No inbound service; every TACC step is a submitted batch job.", 0.65, 5.55, 9.0, 0.2, { fontSize: 8, color: COLORS.muted });
  footer(s, "A1");
}

function slideAppendixA2() {
  const s = pptx.addSlide();
  bg(s, "paper.jpg");
  section(s, "APPENDIX / A2");
  title(s, "Evaluation method and TACC evidence.");
  text(s, "How the numbers were produced, and what the batch backend measured.", PAGE.margin, 1.42, 10.0, 0.3, { fontSize: 11, color: COLORS.muted });

  box(s, 0.65, 1.8, 6.0, 4.4, { fill: COLORS.white, line: COLORS.line, radius: 0.08 });
  text(s, "EVALUATION METHOD", 0.88, 1.98, 4.0, 0.2, { fontSize: 8, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  const rows = [
    ["Practice", "10 single-choice questions on Tutorial 4, 3 controls."],
    ["Citation", "15 new questions, page and quote checked against tracked pages."],
    ["Grading", "10 questions, correct and wrong answers, model vs ground truth."],
    ["Chunking", "51 test questions, page-level nDCG@5, bootstrap CI."],
  ];
  rows.forEach(([h, b], i) => {
    const y = 2.35 + i * 0.85;
    text(s, h, 0.88, y, 1.4, 0.22, { fontSize: 9, bold: true });
    text(s, b, 2.2, y, 4.2, 0.45, { fontSize: 8.5, color: COLORS.muted });
  });

  box(s, 6.95, 1.8, 5.7, 4.4, { fill: COLORS.graphiteCard, line: COLORS.graphiteLine, radius: 0.08 });
  text(s, "TACC / QWEN JOB 28067", 7.18, 1.98, 4.5, 0.2, { fontSize: 8, bold: true, color: COLORS.cobalt, charSpacing: 1.1 });
  const stats = [["434 s", "vLLM cold start"], ["43.9 s", "8-chunk build"], ["8 / 8", "valid records"]];
  stats.forEach(([n, l], i) => {
    const y = 2.35 + i * 1.1;
    text(s, n, 7.18, y, 2.3, 0.42, { fontFace: FONTS.display, fontSize: 22, color: COLORS.white });
    text(s, l, 7.18, y + 0.44, 3.8, 0.2, { fontSize: 8, color: COLORS.whiteMuted });
  });
  text(s, "One shard, 8 chunks; 16 documents / 593 pages / 612 chunks in the full corpus.", 7.18, 5.55, 5.0, 0.35, { fontSize: 7.5, color: COLORS.whiteMuted });
  footer(s, "A2");
}

build().catch((error) => {
  console.error(error);
  process.exit(1);
});

