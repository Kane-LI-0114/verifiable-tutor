import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { withDeckPage } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DECK = resolve(HERE, '..', 'index.html');

const result = await withDeckPage(DECK, async ({ evaluate, sleep }) => {
  const slideCount = await evaluate("document.querySelectorAll('.deck > .slide').length");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true})); true");
  await sleep(650);
  const afterArrow = await evaluate("({active: [...document.querySelectorAll('.deck > .slide')].findIndex((s) => s.classList.contains('is-active')) + 1, hash: location.hash})");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'o',bubbles:true})); true");
  await sleep(450);
  const overview = await evaluate("({open: document.querySelector('.overview').classList.contains('open'), thumbs: document.querySelectorAll('.overview .thumb').length})");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); true");
  await sleep(250);
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'n',bubbles:true})); true");
  await sleep(300);
  const notes = await evaluate("({open: document.querySelector('.notes-overlay').classList.contains('open'), text: document.querySelector('.notes-overlay').textContent.trim().slice(0, 48)})");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); true");
  return { slideCount, afterArrow, overview, notes };
});

const failures = [];
if (result.slideCount !== 20) failures.push('slide count ' + result.slideCount);
if (result.afterArrow.active !== 2) failures.push('arrow navigation did not reach slide 2');
if (result.afterArrow.hash !== '#/2') failures.push('hash deep-link not updated: ' + result.afterArrow.hash);
if (!result.overview.open) failures.push('overview did not open');
if (result.overview.thumbs !== 20) failures.push('overview thumb count ' + result.overview.thumbs);
if (!result.notes.open) failures.push('notes drawer did not open');
if (!result.notes.text.startsWith('0:45.')) failures.push('notes text does not match slide 2: ' + result.notes.text);

console.log(JSON.stringify(result, null, 2));
if (failures.length) {
  for (const failure of failures) console.error('FAIL:', failure);
  process.exitCode = 1;
} else {
  console.log('RUNTIME CHECK PASS: arrow navigation, hash deep link, overview and speaker notes work from the vendored html-ppt runtime');
}
