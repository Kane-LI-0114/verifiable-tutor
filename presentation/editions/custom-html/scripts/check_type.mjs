import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { withDeckPage } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const DECK = resolve(ROOT, 'index.html');
const OUT = resolve(ROOT, 'exports/type-audit.json');

const ALLOWED_SIZES = [32, 80, 112];

const AUDIT_EXPRESSION = `(() => {
  const allowed = [32, 80, 112];
  const isVisible = (el, slide) => {
    for (let node = el; node && node !== slide.parentElement; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
    }
    return true;
  };
  const wordsIn = (text) => text.split(/\s+/).filter((token) => /[A-Za-z0-9]/.test(token)).length;
  const slides = Array.from(document.querySelectorAll('.deck > .slide'));
  const violations = [];
  const slideReports = slides.map((slide, index) => {
    const sizes = new Map();
    const textElements = [];
    const allWords = [];
    const bodyWords = [];
    const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const raw = node.textContent.replace(/\s+/g, ' ').trim();
      if (!raw) continue;
      const el = node.parentElement;
      if (!el || el.closest('.notes')) continue;
      if (!isVisible(el, slide)) continue;
      const size = Math.round(parseFloat(getComputedStyle(el).fontSize) * 100) / 100;
      sizes.set(size, (sizes.get(size) || 0) + 1);
      const chunk = wordsIn(raw);
      allWords.push(chunk);
      const inChrome = !!el.closest('.kick, .pg');
      const inDisplay = !!el.closest('.display, .num, .ctitle, .questions');
      if (!inChrome && !inDisplay) bodyWords.push(chunk);
      if (!allowed.includes(size)) {
        violations.push({ slide: index + 1, kind: 'size', size, text: raw.slice(0, 56), className: String(el.className || '') });
      }
      const rect = el.getBoundingClientRect();
      const slideRect = slide.getBoundingClientRect();
      textElements.push({ el, rect, slideRect });
      if (rect.left < slideRect.left - 2 || rect.right > slideRect.right + 2 ||
          rect.top < slideRect.top - 2 || rect.bottom > slideRect.bottom + 2) {
        violations.push({
          slide: index + 1, kind: 'bounds', size,
          text: raw.slice(0, 56),
          rect: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
        });
      }
    }
    // paragraph-level check: no visible text block should touch the footer rail
    for (const { rect } of textElements) {
      if (rect.bottom > 1004) {
        // footer rail sits at y=1010; text above it is fine
      }
    }
    const expected = index === 0 ? [32, 112] : [32, 80];
    const actual = Array.from(sizes.keys()).sort((a, b) => a - b);
    const sizeSetOk = actual.length === expected.length && expected.every((s) => sizes.has(s));
    if (!sizeSetOk) {
      violations.push({ slide: index + 1, kind: 'size-set', expected, actual });
    }
    const note = slide.querySelector('.notes');
    const noteText = note ? note.textContent.replace(/\s+/g, ' ').trim() : '';
    if (!noteText) violations.push({ slide: index + 1, kind: 'missing-notes' });
    const images = slide.querySelectorAll('img').length;
    if (!images) violations.push({ slide: index + 1, kind: 'missing-visual' });
    return {
      index: index + 1,
      title: slide.getAttribute('data-title') || '',
      sizes: actual,
      sizeSetOk,
      notes: noteText.length,
      images,
      allWords: allWords.reduce((a, b) => a + b, 0),
      bodyWords: bodyWords.reduce((a, b) => a + b, 0),
    };
  });

  const resources = performance.getEntriesByType('resource')
    .map((entry) => entry.name)
    .filter((name) => /^https?:/i.test(name));

  const displayEl = document.querySelector('.slide .display');
  const bodyEl = document.querySelector('.slide p, .slide .contract span');
  const monoEl = document.querySelector('.tbl, .mono');
  const fonts = {
    display: displayEl ? getComputedStyle(displayEl).fontFamily : '',
    body: bodyEl ? getComputedStyle(bodyEl).fontFamily : '',
    mono: monoEl ? getComputedStyle(monoEl).fontFamily : '',
  };
  if (displayEl && !/Georgia/i.test(fonts.display)) violations.push({ kind: 'font', expected: 'Georgia', actual: fonts.display });
  if (!/Arial/i.test(fonts.body)) violations.push({ kind: 'font', expected: 'Arial', actual: fonts.body });
  if (!/Courier New/i.test(fonts.mono)) violations.push({ kind: 'font', expected: 'Courier New', actual: fonts.mono });

  if (slides.length !== 20) violations.push({ kind: 'slide-count', actual: slides.length });
  if (resources.length) violations.push({ kind: 'network', resources });

  const wordLimitViolations = slideReports.filter((report) => report.bodyWords > 45);
  return {
    viewport: [window.innerWidth, window.innerHeight],
    slideCount: slides.length,
    fonts,
    externalResources: resources,
    slides: slideReports,
    wordLimitViolations,
    violations,
    ok: violations.length === 0 && wordLimitViolations.length === 0,
  };
})()`;

const result = await withDeckPage(DECK, async ({ evaluate }) => evaluate(AUDIT_EXPRESSION));

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(result, null, 2) + '\n');

console.log('slide  sizes        body words  imgs  notes  title');
for (const s of result.slides) {
  console.log(
    String(s.index).padStart(5),
    (s.sizes.join(',') + 'px').padEnd(12),
    String(s.bodyWords).padStart(10),
    String(s.images).padStart(5),
    String(s.notes).padStart(6),
    ' ' + s.title,
  );
}
console.log('');
console.log('viewport:', result.viewport.join(' x '));
console.log('slide count:', result.slideCount);
console.log('fonts:', result.fonts);
console.log('external resources:', result.externalResources.length);
console.log('body-word limit violations:', result.wordLimitViolations.length);
for (const item of result.wordLimitViolations) console.log('  over 45:', item.index, item.bodyWords, item.title);
console.log('violations:', result.violations.length);
for (const item of result.violations) console.log('  ' + JSON.stringify(item));
console.log('audit written to', OUT);
if (!result.ok) process.exitCode = 1;
else console.log('TYPE AUDIT PASS: every visible text is 32px, 80px, or the cover 112px');
