#!/usr/bin/env node
/* Export and audit the stage deck with headless Chrome over the DevTools protocol.
 *
 *   node scripts/render.mjs                 # audit + 20 PNGs + PDF + presenter smoke
 *   node scripts/render.mjs --skip-png      # audit + PDF
 *   node scripts/render.mjs --skip-pdf      # audit + PNGs
 *   node scripts/render.mjs --audit-only    # audit + presenter smoke only
 *
 * The deck is served from a local ephemeral HTTP server, so module imports work
 * identically to a static file host and nothing touches the network.
 */
import { spawn, execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const skipPng = args.includes('--skip-png') || args.includes('--audit-only');
const skipPdf = args.includes('--skip-pdf') || args.includes('--audit-only');
const skipSmoke = args.includes('--skip-smoke');
const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.json': 'application/json'
};

await mkdir(join(root, 'exports', 'png'), { recursive: true });
await mkdir(join(root, 'exports', 'audit'), { recursive: true });

/* ---------- static server ---------- */
const server = createServer(async (req, res) => {
  let pathname;
  try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); }
  catch { res.statusCode = 400; res.end('bad url'); return; }
  if (pathname === '/') pathname = '/index.html';
  const file = join(root, pathname);
  if (!file.startsWith(root)) { res.statusCode = 403; res.end('forbidden'); return; }
  try {
    const data = await readFile(file);
    res.setHeader('content-type', MIME[extname(file).toLowerCase()] || 'application/octet-stream');
    res.setHeader('cache-control', 'no-store');
    res.end(data);
  } catch { res.statusCode = 404; res.end('not found'); }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
const pageUrl = 'http://127.0.0.1:' + port + '/index.html?export=1';

/* ---------- chrome ---------- */
const userDataDir = '/tmp/vt-stage-chrome-' + process.pid;
const chrome = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio',
  '--no-first-run', '--no-default-browser-check', '--disable-extensions',
  '--force-device-scale-factor=1', '--force-color-profile=srgb',
  '--window-size=1920,1080', '--remote-debugging-port=0',
  '--user-data-dir=' + userDataDir, '--disable-background-networking',
  pageUrl
], { stdio: 'ignore' });

function cleanup(code) {
  try { chrome.kill('SIGTERM'); } catch {}
  try { server.close(); } catch {}
  process.exit(code);
}

let devtoolsPort = null;
for (let i = 0; i < 150; i++) {
  const file = join(userDataDir, 'DevToolsActivePort');
  if (existsSync(file)) {
    const lines = readFileSync(file, 'utf8').split('\n');
    if (lines[0]) { devtoolsPort = Number(lines[0]); break; }
  }
  await sleep(100);
}
if (!devtoolsPort) { console.error('Chrome DevTools port not found'); cleanup(1); }

let target = null;
for (let i = 0; i < 100; i++) {
  try {
    const list = await (await fetch('http://127.0.0.1:' + devtoolsPort + '/json/list')).json();
    target = list.find((t) => t.type === 'page' && t.url.includes('127.0.0.1'));
    if (target) break;
  } catch {}
  await sleep(100);
}
if (!target) { console.error('page target not found'); cleanup(1); }

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true });
  ws.addEventListener('error', reject, { once: true });
});
let nextId = 1;
const pending = new Map();
ws.addEventListener('message', (event) => {
  let message;
  try { message = JSON.parse(event.data); } catch { return; }
  if (message.id && pending.has(message.id)) {
    const entry = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) entry.reject(new Error(JSON.stringify(message.error)));
    else entry.resolve(message.result);
  }
});
function send(method, params) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
  });
}
async function evaluate(expression, awaitPromise) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: !!awaitPromise, userGesture: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'evaluate failed');
  return result.result ? result.result.value : undefined;
}
async function waitFor(expression, timeoutMs) {
  const limit = Date.now() + (timeoutMs || 30000);
  while (Date.now() < limit) {
    try { if (await evaluate(expression)) return true; } catch {}
    await sleep(120);
  }
  return false;
}

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false, screenWidth: 1920, screenHeight: 1080 });
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] });

if (!(await waitFor('window.__deckReady === true', 40000))) { console.error('deck did not become ready'); cleanup(1); }
const slideCount = await evaluate('document.querySelectorAll(".slide").length');
console.log('deck ready, slides =', slideCount);

/* ---------- audit ---------- */
const audit = JSON.parse(await evaluate('JSON.stringify(window.__auditFontSizes())'));
const layout = JSON.parse(await evaluate('JSON.stringify(window.__auditLayout())'));
const external = JSON.parse(await evaluate('JSON.stringify(window.__auditExternal())')) || [];
const noteCount = await evaluate('Array.isArray(window.__SPEAKER_NOTES__) ? window.__SPEAKER_NOTES__.length : 0');
const failures = [];
const EXPECTED = 20;
if (slideCount !== EXPECTED) failures.push('slide count ' + slideCount + ' != ' + EXPECTED);
if (noteCount !== EXPECTED) failures.push('speaker notes ' + noteCount + ' != ' + EXPECTED);
if (external.length) failures.push('external runtime resources: ' + external.join(', '));
console.log('\nper-slide audit');
console.log('  #  id                  layout                sizes        copy  words  img/svg  families');
for (const slide of audit) {
  const isCover = slide.layout === 'SWISS-COVER-ASCII';
  const allowed = isCover ? [32, 120] : [32, 96];
  const sizesOk = slide.sizes.length === 2 && allowed.every((s) => slide.sizes.includes(s));
  const families = Object.keys(slide.families);
  const line = [
    '  ' + String(slide.index).padStart(2, '0'),
    slide.id.padEnd(19),
    slide.layout.padEnd(20),
    JSON.stringify(slide.sizes).padEnd(12),
    String(slide.copyWords).padStart(4),
    String(slide.words).padStart(6),
    String(slide.images + '/' + slide.icons).padStart(8),
    ' ' + families.join('+')
  ].join(' ');
  console.log(line);
  if (!sizesOk) failures.push('slide ' + slide.index + ' sizes ' + JSON.stringify(slide.sizes) + ' != ' + JSON.stringify(allowed));
  if (slide.badSizes.length) failures.push('slide ' + slide.index + ' off-scale text: ' + JSON.stringify(slide.badSizes.slice(0, 3)));
  if (slide.badFamilies.length) failures.push('slide ' + slide.index + ' unexpected font: ' + JSON.stringify(slide.badFamilies.slice(0, 3)));
  if (slide.copyWords > 45) failures.push('slide ' + slide.index + ' copy words ' + slide.copyWords + ' > 45');
  if (slide.images + slide.icons === 0) failures.push('slide ' + slide.index + ' has no image or icon cluster');
  if (slide.brokenImages.length) failures.push('slide ' + slide.index + ' broken images: ' + slide.brokenImages.join(', '));
}
await writeFile(join(root, 'exports', 'audit', 'font-audit.json'), JSON.stringify({ generatedAt: new Date().toISOString(), slideCount, noteCount, external, audit, layout }, null, 2));
console.log('\ncopy-word total:', audit.reduce((sum, s) => sum + s.copyWords, 0));

console.log('\nlayout overflow audit (stage-local px)');
for (const slide of layout) {
  const state = slide.overflowCount ? 'OVERFLOW' : 'ok';
  const blankPx = 1080 - slide.safeBottom;
  const blankPct = Math.round((blankPx / 1080) * 1000) / 10;
  const safeState = slide.safeBottom > 1040 ? '  CONTENT>1040 (' + slide.safeBottom + ' ' + slide.safeNode + ')' : '';
  const blankState = blankPx > 162 ? '  BLANK>' + blankPct + '%' : '';
  console.log('  ' + String(slide.index).padStart(2, '0') + ' ' + slide.id.padEnd(19) + ' maxBottom=' + String(slide.maxBottom).padStart(4) + ' safeBottom=' + String(slide.safeBottom).padStart(4) + ' blank=' + String(blankPct).padStart(4) + '%  ' + state + (slide.overflowCount ? ' x' + slide.overflowCount : '') + safeState + blankState);
  for (const item of slide.overflow) {
    console.log('       ' + item.tag + (item.cls ? '.' + item.cls : '') + ' [' + item.left + ',' + item.top + ' → ' + item.right + ',' + item.bottom + '] "' + item.text + '"');
  }
  if (slide.overflowCount) failures.push('slide ' + slide.index + ' overflows the 1920x1080 stage (' + slide.overflowCount + ' elements)');
  if (slide.safeBottom > 1040) failures.push('slide ' + slide.index + ' content reaches ' + slide.safeBottom + 'px (must stay above 1040px): ' + slide.safeNode);
  if (1080 - slide.safeBottom > 162) failures.push('slide ' + slide.index + ' bottom blank band ' + blankPct + '% exceeds 15% (content ends ' + slide.safeBottom + 'px)');
}
console.log('audit failures:', failures.length);

/* ---------- PNG export ---------- */
const pngFiles = [];
if (!skipPng) {
  for (let i = 0; i < slideCount; i++) {
    await evaluate('window.__exportGo(' + i + ')');
    await evaluate('new Promise(function(r){requestAnimationFrame(function(){requestAnimationFrame(function(){setTimeout(r,40)})})})', true);
    const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    const buffer = Buffer.from(shot.data, 'base64');
    const width = buffer.readUInt32BE(16);
    const height = buffer.readUInt32BE(20);
    if (width !== 1920 || height !== 1080) failures.push('slide ' + (i + 1) + ' PNG ' + width + 'x' + height);
    const name = 'slide-' + String(i + 1).padStart(2, '0') + '.png';
    await writeFile(join(root, 'exports', 'png', name), buffer);
    pngFiles.push({ name, width, height, bytes: buffer.length });
  }
  console.log('PNG export:', pngFiles.length, 'files at 1920x1080');
}

/* ---------- PDF export ----------
   Chrome Page.printToPDF stalls on this 20-page image-heavy deck in headless mode,
   so the PDF is assembled from the verified 1920x1080 PNGs with Pillow (96 dpi =>
   20 x 11.25 in pages), which the task brief explicitly allows. */
if (!skipPdf && !skipPng) {
  const pdfPath = join(root, 'exports', 'VerifiableTutor_stage.pdf');
  try {
    execFileSync('python3', [join(root, 'scripts', 'png_to_pdf.py'), root], { encoding: 'utf8', stdio: 'inherit' });
  } catch (error) {
    failures.push('PNG to PDF export failed: ' + error.message);
  }
  let pages = null;
  try {
    const info = execFileSync('/opt/homebrew/bin/pdfinfo', [pdfPath], { encoding: 'utf8' });
    const match = info.match(/Pages:\s+(\d+)/);
    if (match) pages = Number(match[1]);
  } catch (error) {
    console.log('pdfinfo unavailable:', error.message);
  }
  console.log('PDF export:', pdfPath, 'pages =', pages);
  if (pages !== 20) failures.push('PDF page count ' + pages + ' != 20');
}

/* ---------- presenter / navigation smoke test ---------- */
let smoke = null;
if (!skipSmoke) {
  smoke = {};
  await evaluate('window.__exportGo(0)');
  await sleep(900);
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await sleep(250);
  smoke.arrowRightIndex = await evaluate('window.__currentSlideIndex');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await sleep(250);
  smoke.overviewOpen = await evaluate('document.getElementById("overview") && getComputedStyle(document.getElementById("overview")).display !== "none"');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await sleep(200);
  smoke.overviewClosed = await evaluate('getComputedStyle(document.getElementById("overview")).display === "none"');
  await evaluate('window.__pptPresenter.enterPresenter(false)');
  await sleep(1200);
  smoke.presenterShell = await evaluate('!!document.getElementById("ppt-presenter")');
  smoke.presenterTitle = await evaluate('document.getElementById("ppt-notes-title") ? document.getElementById("ppt-notes-title").textContent : null');
  smoke.presenterNotes = await evaluate('document.getElementById("ppt-note-editor") ? document.getElementById("ppt-note-editor").value.slice(0, 80) : null');
  smoke.currentFrameSlide = await evaluate('document.getElementById("ppt-current-frame") ? document.getElementById("ppt-current-frame").dataset.slide : null');
  smoke.presenterPageBeforeNext = await evaluate('document.getElementById("ppt-page-count") ? document.getElementById("ppt-page-count").textContent : null');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await sleep(400);
  smoke.presenterPageAfterNext = await evaluate('document.getElementById("ppt-page-count") ? document.getElementById("ppt-page-count").textContent : null');
  smoke.presenterNotesAfterNext = await evaluate('document.getElementById("ppt-notes-title") ? document.getElementById("ppt-notes-title").textContent : null');
  smoke.cjkInPresenter = await evaluate('(function(){var t=document.getElementById("ppt-presenter").innerText; return /[\\u4e00-\\u9fff]/.test(t)})()');
  await evaluate('window.__pptPresenter ? window.__pptPresenter.enterPresenter && document.getElementById("ppt-exit").click() : null');
  await sleep(300);
  smoke.presenterExited = await evaluate('!document.body.classList.contains("ppt-presenter")');
  await writeFile(join(root, 'exports', 'audit', 'runtime-check.json'), JSON.stringify(smoke, null, 2));
  console.log('presenter/navigation smoke:', JSON.stringify(smoke));
  if (smoke.arrowRightIndex !== 1) failures.push('keyboard navigation ArrowRight did not advance (index ' + smoke.arrowRightIndex + ')');
  if (!smoke.overviewOpen || !smoke.overviewClosed) failures.push('overview toggle failed');
  if (!smoke.presenterShell) failures.push('presenter shell did not mount');
  if (!smoke.presenterNotes || smoke.presenterNotes.length < 20) failures.push('speaker notes not shown in presenter');
  if (smoke.cjkInPresenter) failures.push('presenter chrome still contains CJK');
  if (!smoke.presenterPageAfterNext || smoke.presenterPageAfterNext === smoke.presenterPageBeforeNext) failures.push('presenter next page did not advance');
}

if (pngFiles.length) await writeFile(join(root, 'exports', 'audit', 'png-manifest.json'), JSON.stringify(pngFiles, null, 2));

if (failures.length) {
  console.error('\nFAILURES (' + failures.length + '):');
  for (const failure of failures) console.error(' - ' + failure);
  ws.close();
  cleanup(1);
}
console.log('\nAUDIT PASS: 20 slides, two sizes per slide (32/96 content, 32/120 cover), no off-scale text, no CDN resources.');
ws.close();
cleanup(0);
