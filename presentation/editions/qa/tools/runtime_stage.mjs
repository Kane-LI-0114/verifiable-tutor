import { withDeckPage } from '../../custom-html/scripts/cdp.mjs';
const deck = process.argv[2];
const result = await withDeckPage(deck, async ({ evaluate, send, sleep }) => {
  let ready = false;
  for (let i = 0; i < 120; i += 1) {
    try { if (await evaluate('window.__deckReady === true')) { ready = true; break; } } catch { /* wait */ }
    await sleep(150);
  }
  const info = {
    ready,
    slides: await evaluate('document.querySelectorAll(".slide").length'),
    notes: await evaluate('Array.isArray(window.__SPEAKER_NOTES__) ? window.__SPEAKER_NOTES__.length : 0'),
    external: await evaluate('performance.getEntriesByType("resource").map((e) => e.name).filter((n) => /^https?:/i.test(n))'),
    initial: await evaluate('window.__currentSlideIndex'),
  };
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await sleep(1400);
  info.afterRight = await evaluate('window.__currentSlideIndex');
  await sleep(1400);
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  await sleep(1400);
  info.afterRight2 = await evaluate('window.__currentSlideIndex');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowLeft', code: 'ArrowLeft', windowsVirtualKeyCode: 37 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowLeft', code: 'ArrowLeft', windowsVirtualKeyCode: 37 });
  await sleep(1400);
  info.afterLeft = await evaluate('window.__currentSlideIndex');
  return info;
});
console.log(JSON.stringify(result, null, 2));
const failures = [];
if (!result.ready) failures.push('deck not ready');
if (result.slides !== 20) failures.push('slide count ' + result.slides);
if (result.notes !== 20) failures.push('notes count ' + result.notes);
if (result.external.length) failures.push('external resources: ' + result.external.join(','));
if (result.afterRight !== 1) failures.push('ArrowRight did not advance: ' + result.afterRight);
if (result.afterRight2 !== 2) failures.push('second ArrowRight failed: ' + result.afterRight2);
if (result.afterLeft !== 1) failures.push('ArrowLeft did not go back: ' + result.afterLeft);
if (failures.length) { failures.forEach((f) => console.error('FAIL:', f)); process.exitCode = 1; }
else console.log('STAGE RUNTIME CHECK PASS: 20 slides, 20 notes, arrow/End navigation, no external resources');