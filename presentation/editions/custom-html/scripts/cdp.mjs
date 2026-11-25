import { spawn } from 'node:child_process';
import { rmSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Open one headless Chrome page at exactly 1920x1080, load the deck file, and
 * hand a small CDP client to the callback. The Chrome process is always torn
 * down. No external packages: Node's built-in fetch and WebSocket are enough.
 */
export async function withDeckPage(deckPath, fn) {
  const port = 9400 + Math.floor(Math.random() * 300);
  const userDir = '/tmp/vt-custom-chrome-' + process.pid;
  rmSync(userDir, { recursive: true, force: true });
  const chrome = spawn(CHROME, [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-sandbox',
    '--window-size=1920,1080',
    '--force-device-scale-factor=1',
    '--remote-debugging-port=' + port,
    '--user-data-dir=' + userDir,
    'about:blank',
  ], { stdio: 'ignore' });

  let ws;
  try {
    let target = null;
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      try {
        const res = await fetch('http://127.0.0.1:' + port + '/json/list');
        const list = await res.json();
        target = list.find((t) => t.type === 'page');
        if (target) break;
      } catch {
        // devtools endpoint not up yet
      }
      await sleep(120);
    }
    if (!target) throw new Error('Chrome DevTools endpoint did not come up');

    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });

    let nextId = 0;
    const pending = new Map();
    ws.addEventListener('message', (event) => {
      const message = JSON.parse(typeof event.data === 'string' ? event.data : String(event.data));
      if (message.id && pending.has(message.id)) {
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) reject(new Error(JSON.stringify(message.error)));
        else resolve(message.result);
      }
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

    await send('Page.enable');
    await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', {
      width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false,
      screenWidth: 1920, screenHeight: 1080,
    });
    await send('Page.navigate', { url: pathToFileURL(deckPath).href });
    await sleep(1600);
    await send('Runtime.evaluate', {
      expression: 'document.fonts.ready.then(() => true)',
      awaitPromise: true,
      returnByValue: true,
    });
    await sleep(400);

    const evaluate = async (expression) => {
      const result = await send('Runtime.evaluate', {
        expression, returnByValue: true, awaitPromise: true,
      });
      if (result.exceptionDetails) {
        throw new Error('page evaluation failed: ' + JSON.stringify(result.exceptionDetails));
      }
      return result.result.value;
    };

    const screenshot = async (filePath) => {
      const result = await send('Page.captureScreenshot', {
        format: 'png', fromSurface: true, captureBeyondViewport: false,
      });
      const { writeFileSync } = await import('node:fs');
      writeFileSync(filePath, Buffer.from(result.data, 'base64'));
    };

    return await fn({ send, evaluate, screenshot, sleep });
  } finally {
    try { if (ws && ws.readyState === 1) ws.close(); } catch { /* ignore */ }
    chrome.kill('SIGKILL');
    await sleep(120);
    rmSync(userDir, { recursive: true, force: true });
  }
}
