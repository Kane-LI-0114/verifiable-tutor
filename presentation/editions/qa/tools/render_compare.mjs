import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = fileURLToPath(new URL('.', import.meta.url));
const QA = resolve(HERE, '..');

const MIME = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.png': 'image/png', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.woff2': 'font/woff2', '.json': 'application/json' };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

async function launch(url, flags) {
  const port = 9400 + Math.floor(Math.random() * 500);
  const userDir = '/tmp/vt-qa-chrome-' + process.pid + '-' + port;
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio', '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--force-device-scale-factor=1', ...flags, '--window-size=1920,1080', '--remote-debugging-port=' + port, '--user-data-dir=' + userDir, url], { stdio: 'ignore' });
  let target = null;
  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    try {
      const list = await (await fetch('http://127.0.0.1:' + port + '/json/list')).json();
      target = list.find((t) => t.type === 'page');
      if (target) break;
    } catch { /* not up */ }
    await sleep(120);
  }
  if (!target) { chrome.kill('SIGKILL'); throw new Error('chrome did not start'); }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener('open', res, { once: true }); ws.addEventListener('error', rej, { once: true }); });
  let nextId = 0;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(typeof event.data === 'string' ? event.data : String(event.data));
    if (msg.id && pending.has(msg.id)) {
      const { resolve: r, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error))); else r(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((r, j) => { const id = ++nextId; pending.set(id, { resolve: r, reject: j }); ws.send(JSON.stringify({ id, method, params })); });
  const evaluate = async (expression) => {
    const out = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (out.exceptionDetails) throw new Error('eval failed: ' + JSON.stringify(out.exceptionDetails).slice(0, 300));
    return out.result ? out.result.value : undefined;
  };
  const screenshot = async (file) => {
    const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    await writeFile(file, Buffer.from(shot.data, 'base64'));
  };
  const close = async () => {
    try { ws.close(); } catch { /* noop */ }
    try { chrome.kill('SIGKILL'); } catch { /* noop */ }
    await sleep(150);
    try { await rm(userDir, { recursive: true, force: true }); } catch { /* noop */ }
  };
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false, screenWidth: 1920, screenHeight: 1080 });
  return { send, evaluate, screenshot, close };
}

const mode = process.argv[2];

if (mode === 'stage') {
  const root = resolve(QA, '..', 'stage-html');
  const outDir = resolve(QA, 'audits', 'render-stage');
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });
  const server = createServer(async (req, res) => {
    let pathname;
    try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); } catch { res.statusCode = 400; res.end(); return; }
    if (pathname === '/') pathname = '/index.html';
    const file = join(root, pathname);
    if (!file.startsWith(root)) { res.statusCode = 403; res.end(); return; }
    try {
      const data = await readFile(file);
      res.setHeader('content-type', MIME[extname(file).toLowerCase()] || 'application/octet-stream');
      res.setHeader('cache-control', 'no-store');
      res.end(data);
    } catch { res.statusCode = 404; res.end('not found'); }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const page = await launch('http://127.0.0.1:' + port + '/index.html?export=1', ['--force-color-profile=srgb', '--disable-background-networking']);
  try {
    await page.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] });
    const deadline = Date.now() + 40000;
    let ready = false;
    while (Date.now() < deadline) { try { if (await page.evaluate('window.__deckReady === true')) { ready = true; break; } } catch { /* wait */ } await sleep(150); }
    if (!ready) throw new Error('deck not ready');
    const count = await page.evaluate('document.querySelectorAll(".slide").length');
    for (let i = 0; i < count; i += 1) {
      await page.evaluate('window.__exportGo(' + i + ')');
      await page.evaluate('new Promise(function(r){requestAnimationFrame(function(){requestAnimationFrame(function(){setTimeout(r,40)})})})');
      const name = 'slide-' + String(i + 1).padStart(2, '0') + '.png';
      await page.screenshot(join(outDir, name));
      console.log('rendered', name);
    }
    console.log('stage render count:', count);
  } finally {
    await page.close();
    server.close();
  }
} else if (mode === 'custom') {
  const deck = resolve(QA, '..', 'custom-html', 'index.html');
  const outDir = resolve(QA, 'audits', 'render-custom');
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });
  const page = await launch('file://' + deck, []);
  try {
    const count = await page.evaluate("document.querySelectorAll('.deck > .slide').length");
    await page.evaluate('document.fonts.ready.then(() => true)');
    for (let index = 1; index <= count; index += 1) {
      await page.evaluate("location.hash = '#/" + index + "'; true");
      await sleep(760);
      const active = await page.evaluate("(document.querySelector('.deck .slide.is-active') || {}).getAttribute ? document.querySelector('.deck .slide.is-active').getAttribute('data-title') : ''");
      if (!active) throw new Error('slide ' + index + ' not active');
      const name = 'slide-' + String(index).padStart(2, '0') + '.png';
      await page.screenshot(join(outDir, name));
      console.log('rendered', name, ':', active);
    }
    console.log('custom render count:', count);
  } finally {
    await page.close();
  }
} else {
  console.error('usage: node render_compare.mjs stage|custom');
  process.exit(2);
}
