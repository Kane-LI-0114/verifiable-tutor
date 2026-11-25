import { mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { withDeckPage } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const DECK = resolve(ROOT, 'index.html');
const OUT_DIR = resolve(ROOT, 'exports/slides');

rmSync(OUT_DIR, { recursive: true, force: true });
mkdirSync(OUT_DIR, { recursive: true });

const total = await withDeckPage(DECK, async ({ evaluate, screenshot, sleep }) => {
  const count = await evaluate("document.querySelectorAll('.deck > .slide').length");
  for (let index = 1; index <= count; index += 1) {
    await evaluate("location.hash = '#/" + index + "'; true");
    await sleep(720);
    const active = await evaluate("(document.querySelector('.deck .slide.is-active') || {}).getAttribute ? document.querySelector('.deck .slide.is-active').getAttribute('data-title') : ''");
    if (!active) throw new Error('slide ' + index + ' did not become active');
    const name = 'slide-' + String(index).padStart(2, '0') + '.png';
    await screenshot(resolve(OUT_DIR, name));
    console.log('rendered', name, '·', active);
  }
  return count;
});

console.log('done:', total, 'PNG slides at', OUT_DIR);
