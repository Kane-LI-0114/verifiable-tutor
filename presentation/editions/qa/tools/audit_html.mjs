import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { withDeckPage } from '../../custom-html/scripts/cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const [deckPath, selector, coverDisplay, contentDisplay, outName] = process.argv.slice(2);
const config = { selector, coverDisplay: Number(coverDisplay), contentDisplay: Number(contentDisplay) };

function pageAudit(cfg) {
  const EXCLUDE = '.notes, [aria-hidden="true"], #nav, #hint, #overview, #ppt-presenter';
  const CHROME = '.st-chrome, .chrome, .kick, .pg, .foot, .footer';
  const CJK = /[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af\uff00-\uffef]/;
  const slides = Array.from(document.querySelectorAll(cfg.selector));
  const isVisible = (el) => {
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    }
    return el.getClientRects().length > 0;
  };
  const firstFamily = (cs) => (cs.fontFamily.split(',')[0] || '').replace(/["']/g, '').trim();
  const wordCount = (t) => t.split(/\s+/).filter((w) => /[A-Za-z0-9]/.test(w)).length;
  const reports = slides.map((slide, index) => {
    const slideRect = slide.getBoundingClientRect();
    const textNodes = [];
    const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT, null);
    let node;
    while ((node = walker.nextNode())) {
      const raw = node.textContent.replace(/\s+/g, ' ').trim();
      if (!raw) continue;
      const el = node.parentElement;
      if (!el) continue;
      if (el.closest(EXCLUDE)) continue;
      if (!isVisible(el)) continue;
      const cs = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      textNodes.push({
        text: raw,
        size: Math.round(parseFloat(cs.fontSize) * 100) / 100,
        family: firstFamily(cs),
        tag: el.tagName,
        cls: String(el.className || '').slice(0, 80),
        inChrome: !!el.closest(CHROME),
        rect: [Math.round(rect.left - slideRect.left), Math.round(rect.top - slideRect.top), Math.round(rect.right - slideRect.left), Math.round(rect.bottom - slideRect.top)],
      });
    }
    const sizes = {};
    const families = {};
    const badSizes = [];
    const badFamilies = [];
    for (const t of textNodes) {
      sizes[t.size] = (sizes[t.size] || 0) + 1;
      families[t.family] = (families[t.family] || 0) + 1;
      if (![32, 80, 96, 112, 120].includes(t.size)) badSizes.push(t);
      if (!/^(Georgia|Arial|Courier New)$/i.test(t.family)) badFamilies.push(t);
    }
    const sizeKeys = Object.keys(sizes).map(Number).sort((a, b) => a - b);
    const isCover = index === 0;
    const expected = isCover ? [32, cfg.coverDisplay] : [32, cfg.contentDisplay];
    const sizeSetOk = sizeKeys.length === 2 && expected.every((s) => sizeKeys.includes(s));
    const displayTexts = textNodes.filter((t) => t.size >= 80).map((t) => t.text);
    const notesEl = slide.querySelector('.notes');
    const notesText = notesEl ? notesEl.textContent.replace(/\s+/g, ' ').trim() : '';
    const imgs = Array.from(slide.querySelectorAll('img')).map((img) => {
      const r = img.getBoundingClientRect();
      return {
        src: img.getAttribute('src'),
        complete: img.complete,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
      };
    });
    const brokenImages = imgs.filter((i) => !(i.complete && i.naturalWidth > 0));
    const bgUrls = [];
    for (const el of slide.querySelectorAll('*')) {
      const bg = getComputedStyle(el).backgroundImage;
      if (bg && bg.includes('url(')) {
        const m = bg.match(/url\("?([^")]+)"?\)/);
        if (m) bgUrls.push(m[1]);
      }
    }
    const visibleText = textNodes.map((t) => t.text).join(' ').replace(/\s+/g, ' ').trim();
    const allWords = wordCount(visibleText);
    const bodyNodes = textNodes.filter((t) => !t.inChrome && t.size < 80);
    const bodyWords = wordCount(bodyNodes.map((t) => t.text).join(' '));
    const cjkHits = (textNodes.map((t) => t.text).join(' ').match(CJK) || []).length;
    const outOfBounds = textNodes.filter((t) => t.rect[0] < -2 || t.rect[1] < -2 || t.rect[2] > slideRect.width + 2 || t.rect[3] > slideRect.height + 2).slice(0, 12);
    let contentBottom = 0;
    let contentBottomNode = '';
    const paintBottom = (bottom, label) => {
      if (bottom > contentBottom) { contentBottom = bottom; contentBottomNode = label; }
    };
    for (const t of textNodes) if (!t.inChrome) paintBottom(t.rect[3], 'text:' + t.text.slice(0, 30));
    for (const img of imgs) paintBottom(img.rect[1] + img.rect[3], 'img:' + (img.src || ''));
    const slideW = slideRect.width;
    const slideH = slideRect.height;
    for (const el of slide.querySelectorAll('*')) {
      if (el.closest(EXCLUDE) || el.closest(CHROME)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      if (r.width >= slideW * 0.98 && r.height >= slideH * 0.98) continue; // full-bleed background
      if (r.height <= 4 && r.width > slideW * 0.8) continue; // thin full-width rule (footer chrome)
      const cs = getComputedStyle(el);
      const bg = cs.backgroundColor;
      const hasBg = bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
      const hasImg = cs.backgroundImage && cs.backgroundImage !== 'none';
      let hasBorder = false;
      for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
        if (parseFloat(cs['border' + side + 'Width']) > 0) { hasBorder = true; break; }
      }
      const isMedia = el.tagName === 'IMG' || el.tagName === 'SVG' || el.tagName === 'FIGURE';
      if (hasBg || hasImg || hasBorder || isMedia) {
        paintBottom(Math.round(r.bottom - slideRect.top), el.tagName + '.' + String(el.className || '').split(' ')[0]);
      }
    }
    return {
      index: index + 1,
      id: slide.dataset.slideId || slide.dataset.title || '',
      titleAttr: slide.dataset.title || '',
      layout: slide.dataset.layout || '',
      sizeKeys, expected, sizeSetOk, sizes, families, badSizes, badFamilies,
      displayTexts, titleDisplay: displayTexts[0] || '',
      words: allWords, bodyWords, notesChars: notesText.length, notes: notesText,
      imgCount: imgs.length, svgCount: slide.querySelectorAll('svg').length, brokenImages, bgUrls,
      outOfBounds, cjkCount: cjkHits,
      contentBottom, contentBottomNode, blankBottomPct: Math.round((1 - contentBottom / slideRect.height) * 1000) / 10,
      visibleText, textNodeCount: textNodes.length,
    };
  });
  const externalResources = performance.getEntriesByType('resource').map((e) => e.name).filter((n) => /^https?:/i.test(n));
  const externalAttrs = Array.from(document.querySelectorAll('[src],[href]')).map((el) => el.getAttribute('src') || el.getAttribute('href')).filter((u) => u && /^https?:/i.test(u));
  const externalCss = [];
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      for (const rule of Array.from(sheet.cssRules || [])) {
        const s = rule.cssText || '';
        if (/url\(\s*["']?https?:/i.test(s) || /@import\s+["']?https?:/i.test(s)) externalCss.push(s.slice(0, 140));
      }
    } catch (e) { /* file:// sheet unreadable */ }
  }
  const allText = document.body.innerText;
  const cjkAll = (allText.match(CJK) || []).length;
  const stacks = new Set();
  for (const el of document.querySelectorAll('.slide *')) {
    const fam = getComputedStyle(el).fontFamily;
    if (fam) stacks.add(fam);
  }
  return {
    slideCount: slides.length,
    viewport: [innerWidth, innerHeight],
    externalResources, externalAttrs, externalCss, cjkAll,
    fontStacks: Array.from(stacks),
    slides: reports,
  };
}

const expression = '(' + pageAudit.toString() + ')(' + JSON.stringify(config) + ')';
const data = await withDeckPage(deckPath, async (page) => {
  await page.evaluate("new Promise((resolve) => { const imgs = Array.from(document.images); const pending = imgs.filter((i) => !i.complete).length; if (!pending) return resolve(true); let left = pending; const done = () => { if (--left === 0) resolve(true); }; imgs.forEach((i) => { if (!i.complete) { i.addEventListener('load', done, { once: true }); i.addEventListener('error', done, { once: true }); } }); setTimeout(() => resolve(true), 10000); })");
  await page.sleep(300);
  return page.evaluate(expression);
});
mkdirSync(resolve(ROOT, 'audits'), { recursive: true });
writeFileSync(resolve(ROOT, 'audits', outName), JSON.stringify(data, null, 2));
console.log(JSON.stringify({
  deck: deckPath,
  slideCount: data.slideCount,
  externalResources: data.externalResources,
  externalAttrs: data.externalAttrs,
  externalCss: data.externalCss,
  cjkAll: data.cjkAll,
  fontStacks: data.fontStacks,
  perSlide: data.slides.map((s) => ({ i: s.index, id: s.id, sizes: s.sizeKeys, ok: s.sizeSetOk, badSizes: s.badSizes.length, badFamilies: s.badFamilies.length, bodyWords: s.bodyWords, words: s.words, img: s.imgCount, svg: s.svgCount, broken: s.brokenImages.length, oob: s.outOfBounds.length, blankPct: s.blankBottomPct, cjk: s.cjkCount, notes: s.notesChars })),
}, null, 2));